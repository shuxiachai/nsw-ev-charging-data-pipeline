"""Build a relational database atomically, then validate independent invariants."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import logging
from pathlib import Path

import duckdb
import pandas as pd

from .acquire import ROOT, RAW
from .clean import load_clean, spatial_assign, identifier
from .augment import augment
from .osm import osm_augment
from .jolt import jolt_augment
from .ampol import ampol_augment
from .resolve import resolve_conflicts
from .reviewed import apply_reviewed_resolutions
from .identity import apply_reviewed_identities, identity_audit_matches_configuration
from .coverage import attribute_coverage, augmentation_composition
from .matching_review import database_address_exceptions_valid

OUT = ROOT / "data/processed"
QA = ROOT / "outputs"
DB = OUT / "ev_chargers.duckdb"
EXT = ROOT / ".runtime/duckdb_extensions"


def connect(path, offline=True):
    EXT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), config={"extension_directory": str(EXT)})
    # TIMESTAMPTZ represents an instant; exports must not depend on the host zone.
    con.execute("SET TimeZone='UTC'")
    try:
        con.execute("LOAD spatial")
    except duckdb.Error:
        if offline:
            con.close()
            raise RuntimeError("DuckDB spatial extension not installed for this platform/version. Run python -m ev_pipeline all online once.")
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
    return con


def insert(con, table, frame, columns=None):
    if frame.empty:
        return
    con.register("input_frame", frame if columns is None else frame[columns])
    try:
        # table/column identifiers are constants controlled by this source file.
        con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM input_frame")
    finally:
        con.unregister("input_frame")


def snapshots():
    rows = []
    for p in sorted(RAW.rglob("*.meta.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        name = p.with_name(p.name.removesuffix(".meta.json"))
        if (not name.exists() or sha256(name.read_bytes()).hexdigest() != m["sha256"]
                or name.stat().st_size != m["bytes"]):
            raise ValueError(f"Input snapshot hash mismatch: {name}")
        rows.append({"source_file": name.relative_to(ROOT).as_posix(), "url": m["url"],
                     "retrieved_at_utc": m["retrieved_at_utc"], "sha256": m["sha256"], "byte_count": m["bytes"]})
    return pd.DataFrame(rows)


def reviewed_identity_evidence_valid(con):
    from .identity import identity_evidence_audit
    expected = sorted(identity_evidence_audit().itertuples(index=False, name=None))
    actual = con.execute("SELECT review_id,source_file,role,element_id,sha256 FROM reviewed_identity_evidence ORDER BY ALL").fetchall()
    invalid = con.execute("""
        SELECT count(*) FROM reviewed_identity_evidence e
        LEFT JOIN source_snapshot s USING(source_file)
        WHERE e.sha256 IS DISTINCT FROM s.sha256
           OR NOT EXISTS (SELECT 1 FROM reviewed_identity i WHERE i.review_id=e.review_id)
    """).fetchone()[0]
    return actual == expected and invalid == 0


def reviewed_resolution_address_evidence_valid(con):
    config = json.loads((ROOT / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
    sources = {source["file"]: source["sha256"] for source in config["sources"]}
    expected = []
    for entry in config["resolutions"]:
        supporting = entry.get("supporting_address_source_file")
        role = "mapped_landmark" if entry["corroborating"]["kind"] == "osm_landmark" else "same_operator_charger"
        expected.append((entry["record_id"], entry["address_source_file"], sources[entry["address_source_file"]],
                         supporting, sources.get(supporting), entry.get("supporting_address_locator"), role))
    actual = con.execute("""
        SELECT r.record_id,r.address_source_file,s.sha256,
               r.supporting_address_source_file,extra.sha256,r.supporting_address_locator,r.corroborating_role
        FROM reviewed_resolution r
        LEFT JOIN source_snapshot s ON s.source_file=r.address_source_file
        LEFT JOIN source_snapshot extra ON extra.source_file=r.supporting_address_source_file
        ORDER BY r.record_id
    """).fetchall()
    return actual == sorted(expected)


def jolt_status_snapshots_match_source(con):
    """Check persisted states and carpark notes against the dated raw map."""
    from .jolt import parse_map, snapshot_status, carpark_hours_text
    path = RAW / "jolt_map.html"
    try:
        body = path.read_bytes()
        metadata = json.loads(path.with_name(path.name + ".meta.json").read_text(encoding="utf-8"))
        captured = datetime.fromisoformat(metadata["retrieved_at_utc"])
        if (metadata["url"] != "https://joltcharge.com/au/find-a-charger/"
                or captured.utcoffset() is None
                or sha256(body).hexdigest() != metadata["sha256"]
                or len(body) != metadata["bytes"]):
            return False
        stored = con.execute("""
            SELECT url,sha256,byte_count,retrieved_at_utc FROM source_snapshot
            WHERE source_file='data/raw/jolt_map.html'
        """).fetchall()
        if stored != [(metadata["url"], metadata["sha256"], metadata["bytes"], captured)]:
            return False
        points = parse_map(body.decode("utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        return False
    try:
        expected = sorted({(int(p["id"]), snapshot_status(p.get("networkStatus"), "networkStatus"),
                            snapshot_status(p.get("evseStatus"), "evseStatus"),
                            carpark_hours_text(p["address"]), "data/raw/jolt_map.html")
                           for p in points})
    except (ValueError, KeyError, TypeError):
        return False
    actual = con.execute("""
        SELECT jolt_id,network_status_snapshot,evse_status_snapshot,carpark_hours_text,source_file
        FROM jolt_site ORDER BY jolt_id
    """).fetchall()
    return actual == expected


def jolt_status_attributes_match_sites(con):
    """Require complete source-linked states/notes for every accepted JOLT match."""
    expected = con.execute("""
        SELECT m.location_id,j.jolt_id,state.attribute,state.value,'site',
               j.source_file,'coordinate_operator_address_match'
        FROM jolt_site_match m JOIN jolt_site j USING(jolt_id),
        LATERAL (VALUES
            ('operator_network_status_snapshot',j.network_status_snapshot),
            ('operator_evse_status_snapshot',j.evse_status_snapshot),
            ('operator_carpark_hours_text',j.carpark_hours_text)
        ) AS state(attribute,value)
        WHERE state.value IS NOT NULL ORDER BY ALL
    """).fetchall()
    actual = con.execute("""
        SELECT location_id,jolt_id,attribute,value,scope,source_file,method
        FROM augmentation
        WHERE attribute IN ('operator_network_status_snapshot','operator_evse_status_snapshot','operator_carpark_hours_text')
        ORDER BY ALL
    """).fetchall()
    return actual == expected


def ampol_evidence_checks(con):
    """Reconstruct publisher observations and accepted links from pinned originals.

    This verifies extraction and persistence, not real-world equipment truth.
    A deleted, relocated, reassigned or invented provider observation must fail.
    """
    from .ampol import SITE_COLUMNS, load_sources
    result = dict(ampol_snapshots_match_source=False, ampol_matches_match_evidence=False,
                  ampol_attributes_match_sites=False)
    try:
        locations = con.execute("SELECT l.*,o.operator_name FROM location l JOIN operator o USING(operator_id)").df()
        records = con.execute("SELECT location_id,charger_type FROM charger_record").df()
        sites, matches, _, attributes = ampol_augment(locations, records)
        columns = ','.join(SITE_COLUMNS)
        expected_sites = sorted(tuple(None if pd.isna(value) else value for value in row)
                                for row in sites[SITE_COLUMNS].itertuples(index=False, name=None))
        actual_sites = con.execute(f"SELECT {columns} FROM amp_charge_site ORDER BY ampol_id").fetchall()
        source_rows = []
        for source, _ in load_sources():
            source_rows.append((source['file'], source['url'], source['sha256'], source['bytes'],
                                datetime.fromisoformat(source['retrieved_at_utc'].replace('Z', '+00:00'))))
        actual_sources = con.execute("""SELECT source_file,url,sha256,byte_count,retrieved_at_utc
                                     FROM source_snapshot WHERE source_file LIKE 'data/raw/ampol/%'
                                     ORDER BY source_file""").fetchall()
        result['ampol_snapshots_match_source'] = actual_sites == expected_sites and actual_sources == sorted(source_rows)
        fields = ['location_id', 'ampol_id', 'distance_m', 'address_similarity', 'score']
        expected_matches = sorted(tuple(row) + ('coordinate_operator_address_match',)
                                  for row in matches[fields].itertuples(index=False, name=None))
        actual_matches = con.execute("""SELECT location_id,ampol_id,distance_m,address_similarity,score,method
                                     FROM amp_charge_site_match ORDER BY location_id""").fetchall()
        result['ampol_matches_match_evidence'] = actual_matches == expected_matches
        fields = ['location_id', 'ampol_id', 'attribute', 'value', 'scope', 'source_file', 'method',
                  'ocm_id', 'ocm_operator_id', 'osm_id', 'jolt_id']
        expected_attributes = sorted(attributes[fields].itertuples(index=False, name=None))
        actual_attributes = con.execute("SELECT " + ','.join(fields) +
                                        " FROM augmentation WHERE ampol_id IS NOT NULL"
                                        " OR source_file LIKE 'data/raw/ampol/%' ORDER BY ALL").fetchall()
        result['ampol_attributes_match_sites'] = actual_attributes == expected_attributes
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result


def reviewed_source_quality_valid(con):
    """Reconstruct the new source warnings, so removing an audit cannot hide them."""
    from .source_quality import source_quality_issues
    from .clean import operator as canonical_operator, text as clean_text
    try:
        records = con.execute("""
            SELECT c.record_id,c.source_row,c.raw_json,l.address,l.address_postcode,l.latitude,l.longitude
            FROM charger_record c JOIN location l USING(location_id)
        """).df()
        # The production validator is strict even for truncated/imported inputs.
        expected = source_quality_issues(records)
        for row in records.itertuples():
            label = clean_text(json.loads(row.raw_json)["Operator"])
            if canonical_operator(label) in {"Fast Cities A", "Energy Austra", "University of"}:
                expected.append(dict(record_id=row.record_id, source_row=int(row.source_row),
                                     code="operator_label_review_required", severity="warning",
                                     detail=f"Source operator label {label!r} is incomplete or ambiguous; retained without guessing a company/network expansion. Review the individual site before interpreting this label as a distinct operator."))
        columns = ["record_id", "source_row", "code", "severity", "detail"]
        actual = con.execute("""SELECT record_id,source_row,code,severity,detail FROM quality_issue
                            WHERE code IN ('address_postcode_locality_mismatch','operator_label_review_required')
                            ORDER BY ALL""").fetchall()
        return actual == sorted(tuple(row[key] for key in columns) for row in expected)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def validate(con):
    from .matching_review import database_match_exclusions_valid
    from .regional import database_regional_reviews_valid
    from .operator_review import database_operator_reviews_valid
    scalar = lambda sql: con.execute(sql).fetchone()[0]
    checks = {
        "reviewed_operator_assignments_withheld": database_operator_reviews_valid(con),
        **ampol_evidence_checks(con),
        "reviewed_source_quality_warnings_complete": reviewed_source_quality_valid(con),
        "reviewed_identity_audit_matches_configuration": identity_audit_matches_configuration(con),
        "reviewed_identity_evidence_complete": reviewed_identity_evidence_valid(con),
        "reviewed_resolution_address_evidence_complete": reviewed_resolution_address_evidence_valid(con),
        "jolt_status_snapshots_match_source": jolt_status_snapshots_match_source(con),
        "jolt_status_attributes_match_sites": jolt_status_attributes_match_sites(con),
        "locations_have_records": scalar("SELECT count(*) FROM location l WHERE NOT EXISTS (SELECT 1 FROM charger_record c WHERE c.location_id=l.location_id)") == 0,
        "reviewed_identities_applied_to_members": scalar("SELECT count(*) FROM reviewed_identity i JOIN charger_record c USING(record_id) JOIN charger_record representative ON representative.record_id=i.representative_record_id WHERE c.location_id IS DISTINCT FROM i.location_id OR c.source_row IS DISTINCT FROM i.source_row OR representative.location_id IS DISTINCT FROM i.location_id") == 0,
        "reviewed_identity_preserves_representative_point": scalar("SELECT count(*) FROM reviewed_identity i JOIN charger_record c ON c.record_id=i.representative_record_id JOIN location l ON l.location_id=i.location_id WHERE l.latitude IS DISTINCT FROM TRY_CAST(json_extract_string(c.raw_json,'$.Latitude') AS DOUBLE) OR l.longitude IS DISTINCT FROM TRY_CAST(json_extract_string(c.raw_json,'$.Longitude') AS DOUBLE)") == 0,
        "reviewed_match_exceptions_have_evidence": database_address_exceptions_valid(con),
        "reviewed_match_exclusions_applied": database_match_exclusions_valid(con),
        "reviewed_regions_match_sources_and_configuration": database_regional_reviews_valid(con),
        "regional_view_does_not_expose_point_geometry": scalar("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_catalog=current_database() AND table_schema='main'
              AND table_name='regional_analysis_locations' AND column_name IN ('latitude','longitude','geometry')
        """) == 0,
        "reviewed_locality_wholly_in_one_sa4": scalar("""
            SELECT count(*) FROM reviewed_region q
            WHERE (SELECT count(*) FROM region r WHERE ST_Covers(r.geometry,q.locality_geometry))<>1
               OR NOT EXISTS (SELECT 1 FROM region r WHERE r.sa4_code=q.reviewed_sa4_code
                              AND ST_Covers(r.geometry,q.locality_geometry))
               OR EXISTS (SELECT 1 FROM region r WHERE r.sa4_code<>q.reviewed_sa4_code
                          AND ST_Intersects(r.geometry,q.locality_geometry))
        """) == 0,
        "regional_view_contains_exact_eligible_locations": scalar("""
            WITH expected AS (
                SELECT l.location_id,coalesce(q.reviewed_sa4_code,l.sa4_code) AS sa4_code,
                       l.sa4_code AS source_point_sa4_code,coalesce(q.method,l.sa4_method) AS regional_assignment_method,
                       q.review_id AS regional_review_id,
                       CASE WHEN q.review_id IS NOT NULL THEN 'unresolved' ELSE 'analysis_ready' END AS coordinate_status
                FROM location l LEFT JOIN reviewed_region q USING(location_id)
                WHERE q.review_id IS NOT NULL OR (NOT l.address_conflict AND l.sa4_code IS NOT NULL)
            ), actual AS (
                SELECT location_id,sa4_code,source_point_sa4_code,regional_assignment_method,
                       regional_review_id,coordinate_status FROM regional_analysis_locations
            ), missing AS (SELECT * FROM expected EXCEPT SELECT * FROM actual),
               extra AS (SELECT * FROM actual EXCEPT SELECT * FROM expected)
            SELECT (SELECT count(*) FROM missing)+(SELECT count(*) FROM extra)
                  +abs((SELECT count(*) FROM actual)-(SELECT count(*) FROM expected))
        """) == 0,
        "external_counts_nonnegative": scalar("SELECT (SELECT count(*) FROM external_site WHERE number_of_points<0)+(SELECT count(*) FROM external_connector WHERE quantity<0)") == 0,
        "source_rows_unique": scalar("SELECT count(*)-count(DISTINCT source_row) FROM charger_record") == 0,
        "source_digests_are_sha256": scalar("SELECT count(*) FROM source_snapshot WHERE NOT regexp_full_match(sha256,'[0-9a-f]{64}')") == 0,
        "power_values_valid": scalar("""
            SELECT (SELECT count(*) FROM charger_record WHERE
                   (power_min_kw IS NULL)<>(power_max_kw IS NULL)
                OR power_min_kw<=0 OR power_max_kw<power_min_kw
                OR NOT isfinite(power_min_kw) OR NOT isfinite(power_max_kw))
                 + (SELECT count(*) FROM external_connector WHERE power_kw<0 OR NOT isfinite(power_kw))
        """) == 0,
        "power_view_preserves_source_observations": scalar("""
            WITH expected AS (
                SELECT c.location_id,c.record_id,c.source_row,c.charger_type,c.power_min_kw,
                       c.power_max_kw,c.power_kind,c.power_raw,s.source_file,s.url AS source_url,
                       s.retrieved_at_utc AS source_captured_at
                FROM charger_record c JOIN source_snapshot s ON s.source_file='data/raw/ev_20251216.csv'
                WHERE c.power_min_kw IS NOT NULL OR c.power_max_kw IS NOT NULL
            ), missing AS (SELECT * FROM expected EXCEPT SELECT * FROM location_power_observations),
               extra AS (SELECT * FROM location_power_observations EXCEPT SELECT * FROM expected)
            SELECT (SELECT count(*) FROM missing)+(SELECT count(*) FROM extra)
                +abs((SELECT count(*) FROM location_power_observations)-(SELECT count(*) FROM expected))
        """) == 0,
        "exact_spatial_assignments_agree": scalar("SELECT count(*) FROM location l JOIN region r USING(sa4_code) WHERE l.sa4_method='point_in_polygon' AND NOT ST_Intersects(l.geometry,r.geometry)") == 0,
        "all_locations_have_sa4": scalar("SELECT count(*) FROM location WHERE sa4_code IS NULL") == 0,
        "spatial_method_and_distance_valid": scalar("SELECT count(*) FROM location WHERE sa4_method IS NULL OR sa4_method NOT IN ('point_in_polygon','coastal_nearest_within_50m') OR sa4_distance_m IS NULL OR NOT isfinite(sa4_distance_m) OR (sa4_method='point_in_polygon' AND sa4_distance_m<>0)") == 0,
        "coastal_assignment_within_50m": scalar("SELECT count(*) FROM location WHERE sa4_method='coastal_nearest_within_50m' AND (sa4_distance_m IS NULL OR NOT isfinite(sa4_distance_m) OR sa4_distance_m<0 OR sa4_distance_m>50)") == 0,
        # Check the actual assigned geometry as well as the recorded number.
        # Projection round trips can differ sub-metre from the original ABS
        # GDA2020 join, so do not claim byte-exact equality of planar distances.
        "coastal_assignments_agree_with_geometry": scalar("""
            WITH distances AS (
                SELECT l.location_id, l.sa4_code AS assigned, r.sa4_code,
                       ST_Intersects(l.geometry,r.geometry) AS intersects,
                       ST_Distance(ST_Transform(l.geometry,'EPSG:4326','EPSG:3577',always_xy := true),
                                   ST_Transform(r.geometry,'EPSG:4326','EPSG:3577',always_xy := true)) AS distance_m
                FROM location l CROSS JOIN region r
                WHERE l.sa4_method='coastal_nearest_within_50m'
            ), ranked AS (
                SELECT *, min(distance_m) OVER (PARTITION BY location_id) AS nearest FROM distances
            )
            SELECT count(*) FROM (
                SELECT location_id FROM ranked GROUP BY location_id
                HAVING bool_or(intersects) OR min(nearest)>50 OR NOT isfinite(min(nearest))
                    OR count(*) FILTER (WHERE abs(distance_m-nearest)<1e-6)<>1
                    OR count(*) FILTER (WHERE sa4_code=assigned AND abs(distance_m-nearest)<1e-6)<>1
            )
        """) == 0,
        "site_enrichment_has_accepted_match": scalar("SELECT count(*) FROM augmentation a WHERE (ocm_id IS NOT NULL OR osm_id IS NOT NULL OR jolt_id IS NOT NULL OR ampol_id IS NOT NULL) AND NOT EXISTS (SELECT 1 FROM site_match m WHERE m.location_id=a.location_id AND m.ocm_id=a.ocm_id) AND NOT EXISTS (SELECT 1 FROM osm_site_match m WHERE m.location_id=a.location_id AND m.osm_id=a.osm_id) AND NOT EXISTS (SELECT 1 FROM jolt_site_match m WHERE m.location_id=a.location_id AND m.jolt_id=a.jolt_id) AND NOT EXISTS (SELECT 1 FROM amp_charge_site_match m WHERE m.location_id=a.location_id AND m.ampol_id=a.ampol_id)") == 0,
        "no_conflicting_address_site_match": scalar("SELECT count(*) FROM site_match JOIN location USING(location_id) WHERE address_conflict") == 0,
        "dc_denominator_nonzero": scalar("SELECT count(DISTINCT location_id) FROM charger_record WHERE charger_type='DC'") > 0,
        "dc_view_contains_exact_source_location_set": scalar("""
            WITH expected AS (SELECT DISTINCT location_id FROM charger_record WHERE charger_type='DC'),
                 missing AS (SELECT * FROM expected EXCEPT SELECT location_id FROM dc_locations),
                 extra AS (SELECT location_id FROM dc_locations EXCEPT SELECT * FROM expected)
            SELECT (SELECT count(*) FROM missing)+(SELECT count(*) FROM extra)
                +abs((SELECT count(*) FROM dc_locations)-(SELECT count(*) FROM expected))
        """) == 0,
        "no_duplicate_site_matches": scalar("SELECT count(*)-count(DISTINCT ocm_id) FROM site_match") == 0,
        "no_duplicate_osm_matches": scalar("SELECT count(*)-count(DISTINCT osm_id) FROM osm_site_match") == 0,
        "no_conflicting_address_osm_match": scalar("SELECT count(*) FROM osm_site_match JOIN location USING(location_id) WHERE address_conflict") == 0,
        "no_conflicting_address_jolt_match": scalar("SELECT count(*) FROM jolt_site_match JOIN location USING(location_id) WHERE address_conflict") == 0,
        "spatial_query_executes": scalar("SELECT count(*) FROM region WHERE ST_IsValid(geometry)") == scalar("SELECT count(*) FROM region"),
        "coordinate_changes_have_resolution_evidence": scalar("SELECT count(*) FROM location l WHERE (latitude<>original_latitude OR longitude<>original_longitude) AND NOT EXISTS (SELECT 1 FROM source_resolution s JOIN charger_record c USING(record_id) WHERE c.location_id=l.location_id AND s.decision='resolved' AND s.new_latitude=l.latitude AND s.new_longitude=l.longitude) AND NOT EXISTS (SELECT 1 FROM reviewed_resolution s JOIN charger_record c USING(record_id) WHERE c.location_id=l.location_id AND s.new_latitude=l.latitude AND s.new_longitude=l.longitude)") == 0,
        "reviewed_resolutions_applied_to_locations": scalar("SELECT count(*) FROM reviewed_resolution s JOIN charger_record c USING(record_id) JOIN location l USING(location_id) WHERE l.address_conflict OR l.latitude IS DISTINCT FROM s.new_latitude OR l.longitude IS DISTINCT FROM s.new_longitude OR l.postcode IS DISTINCT FROM s.new_postcode") == 0,
        "automatic_resolutions_applied_to_analysis_locations": scalar("SELECT count(*) FROM source_resolution s JOIN charger_record c USING(record_id) JOIN location l USING(location_id) WHERE s.decision='resolved' AND NOT l.address_conflict AND (l.latitude IS DISTINCT FROM s.new_latitude OR l.longitude IS DISTINCT FROM s.new_longitude OR l.postcode IS DISTINCT FROM s.new_postcode)") == 0,
        "locations_have_consistent_point_geometry": scalar("SELECT count(*) FROM location WHERE geometry IS NULL OR latitude IS NULL OR longitude IS NULL OR ST_X(geometry) IS DISTINCT FROM longitude OR ST_Y(geometry) IS DISTINCT FROM latitude") == 0,
        "unresolved_conflicts_excluded_from_analysis_view": scalar("SELECT count(*) FROM analysis_ready_locations WHERE address_conflict") == 0,
        "analysis_view_contains_all_eligible_locations": scalar("""
            WITH expected AS (SELECT location_id FROM location WHERE NOT address_conflict AND sa4_code IS NOT NULL),
                 missing AS (SELECT * FROM expected EXCEPT SELECT location_id FROM analysis_ready_locations),
                 extra AS (SELECT location_id FROM analysis_ready_locations EXCEPT SELECT * FROM expected)
            SELECT (SELECT count(*) FROM missing)+(SELECT count(*) FROM extra)
                +abs((SELECT count(*) FROM analysis_ready_locations)-(SELECT count(*) FROM expected))
        """) == 0,
    }
    # Compute the denominator from retained DC records, independently of views.
    total, any_scope, site = con.execute("""
        SELECT count(*),
            count(*) FILTER (WHERE EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=l.location_id)),
            count(*) FILTER (WHERE EXISTS (SELECT 1 FROM augmentation a WHERE a.location_id=l.location_id AND a.scope='site'))
        FROM location l WHERE EXISTS (SELECT 1 FROM charger_record c WHERE c.location_id=l.location_id AND c.charger_type='DC')
    """).fetchone()
    checks["coverage_view_agrees_with_base_tables"] = con.execute("SELECT * FROM dc_augmentation_coverage").fetchall() == [(total, any_scope, site)]
    composition = augmentation_composition(con).set_index("category").dc_locations.to_dict()
    non_identifier = int(composition["non_identifier_site_attribute"])
    station_code_only = int(composition["station_code_only"])
    other_site = scalar("""
        SELECT count(DISTINCT a.location_id) FROM augmentation a
        WHERE a.scope='site' AND a.attribute NOT IN
            ('operator_station_code','operator_network_status_snapshot','operator_evse_status_snapshot')
          AND EXISTS (SELECT 1 FROM charger_record c WHERE c.location_id=a.location_id AND c.charger_type='DC')
    """)
    checks["coverage_composition_agrees"] = (sum(composition.values()) == total
                                            and non_identifier + station_code_only == site)
    return {"integrity_checks": checks, "integrity_passed": all(checks.values()),
            "coverage": {"dc_locations": total, "augmented_any_scope": any_scope, "augmented_site_scope": site,
                         "non_identifier_site_locations": non_identifier, "station_code_only_locations": station_code_only,
                         "non_status_non_identifier_site_locations": other_site,
                         "non_status_non_identifier_site_fraction": other_site / total if total else 0,
                         "non_identifier_site_fraction": non_identifier / total if total else 0,
                         "any_scope_fraction": any_scope / total if total else 0, "site_scope_fraction": site / total if total else 0,
                         "any_scope_target_met": total > 0 and any_scope / total >= 0.5,
                         "site_scope_target_met": total > 0 and site / total >= 0.5}}


def build(offline=True):
    OUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    raw, records, issues, duplicates = load_clean()
    logging.info("Cleaned %s input rows into %s records", len(raw), len(records))
    records, identity_audit = apply_reviewed_identities(records, issues)
    from .identity import identity_evidence_audit
    identity_evidence = identity_evidence_audit()
    records, resolution = resolve_conflicts(records, issues)
    records, reviewed_resolution = apply_reviewed_resolutions(records, issues)
    locations, regions = spatial_assign(records, issues)
    from .regional import regional_reviews, flag_reviewed_geographic_conflicts
    records, locations = flag_reviewed_geographic_conflicts(records, locations, issues)
    region_reviews, region_evidence = regional_reviews(records, locations, regions)
    sites, connectors, matches, audit, details, attributes = augment(locations, records, issues=issues)
    from .matching_review import apply_match_exclusions
    matches, audit, attributes, match_exclusions = apply_match_exclusions(
        locations, records, sites, matches, audit, attributes)
    osm_sites, osm_matches, osm_audit, osm_attrs = osm_augment(locations, records, operator_details=details)
    attributes["osm_id"] = None
    attributes = pd.concat([attributes, osm_attrs], ignore_index=True)
    jolt_sites, jolt_matches, jolt_audit, jolt_attrs = jolt_augment(locations, records)
    attributes["jolt_id"] = None
    attributes = pd.concat([attributes, jolt_attrs], ignore_index=True)
    attributes.insert(0, "augmentation_id", [identifier("a_", list(r)) for r in attributes.itertuples(index=False, name=None)])
    ampol_sites, ampol_matches, ampol_audit, ampol_attrs = ampol_augment(locations, records)
    # Preserve every pre-existing observation ID when adding a new provider.
    attributes["ampol_id"] = None
    ampol_attrs.insert(0, "augmentation_id", [identifier("a_", list(r)) for r in ampol_attrs.itertuples(index=False, name=None)])
    attributes = pd.concat([attributes, ampol_attrs], ignore_index=True)
    from .augmentation_semantics import attribute_differences, connector_quality
    differences = attribute_differences(attributes)
    connector_issues = connector_quality(sites, connectors, matches)
    quality = pd.DataFrame(issues, columns=["record_id", "source_row", "code", "severity", "detail"])
    quality.insert(0, "issue_id", range(1, len(quality) + 1))
    operators = locations[["operator_id", "operator_name"]].drop_duplicates()
    logging.info("Locations=%s; accepted site matches=%s; augmented attributes=%s", len(locations), len(matches), len(attributes))
    temp = DB.with_suffix(".building")
    if temp.exists():
        temp.unlink()  # This exact intermediate is disposable; final DB is untouched.
    with connect(temp, offline=offline) as con:
        con.execute("BEGIN TRANSACTION")
        con.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
        insert(con, "source_snapshot", snapshots())
        region_data = pd.DataFrame({"sa4_code": regions.sa4_code, "sa4_name": regions.sa4_name, "wkt": regions.geometry.to_wkt()})
        con.register("regions_input", region_data)
        con.execute("INSERT INTO region SELECT sa4_code,sa4_name,4,ST_GeomFromText(wkt) FROM regions_input")
        con.unregister("regions_input")
        insert(con, "operator", operators)
        loc = locations[["location_id", "operator_id", "station_name", "address", "latitude", "longitude", "postcode", "address_postcode",
                         "address_conflict", "lga", "sa4_code", "sa4_method", "sa4_distance_m", "original_latitude", "original_longitude",
                         "original_postcode", "original_address_conflict", "resolution_method"]].rename(columns={"lga": "source_lga"})
        con.register("locations_input", loc)
        con.execute("INSERT INTO location SELECT *, CASE WHEN longitude IS NULL OR latitude IS NULL THEN NULL ELSE ST_Point(longitude,latitude) END FROM locations_input")
        con.unregister("locations_input")
        insert(con, "charger_record", records, ["record_id", "location_id", "source_row", "source_objectid", "charger_type", "number_of_plugs",
                                                  "power_min_kw", "power_max_kw", "power_kind", "power_raw", "source_category", "raw_json"])
        insert(con, "reviewed_identity", identity_audit)
        insert(con, "reviewed_identity_evidence", identity_evidence)
        insert(con, "external_site", sites)
        insert(con, "external_connector", connectors)
        m = matches[["location_id", "ocm_id", "distance_m", "address_similarity", "score"]].copy()
        m["method"] = "coordinate_operator_address_match"
        for column in ["address_exception_review_id", "address_exception_source_file"]:
            m[column] = matches[column].replace("", None) if column in matches else None
        insert(con, "site_match", m)
        insert(con, "reviewed_match_exclusion", match_exclusions)
        insert(con, "osm_site", osm_sites)
        om = osm_matches[["location_id", "osm_id", "distance_m", "address_similarity", "score"]].copy()
        om["method"] = "coordinate_operator_address_match"
        insert(con, "osm_site_match", om)
        insert(con, "jolt_site", jolt_sites)
        jm = jolt_matches[["location_id", "jolt_id", "distance_m", "address_similarity", "score"]].copy()
        jm["method"] = "coordinate_operator_address_match"
        insert(con, "jolt_site_match", jm)
        insert(con, "amp_charge_site", ampol_sites)
        am = ampol_matches[["location_id", "ampol_id", "distance_m", "address_similarity", "score"]].copy()
        am["method"] = "coordinate_operator_address_match"
        insert(con, "amp_charge_site_match", am)
        insert(con, "augmentation", attributes)
        insert(con, "source_resolution", resolution)
        insert(con, "reviewed_resolution", reviewed_resolution)
        con.register("regional_input", region_reviews)
        con.execute("INSERT INTO reviewed_region SELECT * EXCLUDE(locality_wkt), ST_GeomFromText(locality_wkt) FROM regional_input")
        con.unregister("regional_input")
        insert(con, "reviewed_region_evidence", region_evidence)
        insert(con, "quality_issue", quality)
        checks = validate(con)
        coverage_attributes = attribute_coverage(con)
        coverage_composition = augmentation_composition(con)
        power_observations = con.execute("SELECT * FROM location_power_observations ORDER BY source_row").df()
        regional_locations = con.execute("SELECT * FROM regional_analysis_locations ORDER BY location_id").df()
        regional_counts = con.execute("""
            SELECT r.sa4_code,r.sa4_name,count(l.location_id) AS locations,
                   count(l.location_id) FILTER (WHERE EXISTS (
                       SELECT 1 FROM charger_record c WHERE c.location_id=l.location_id AND c.charger_type='DC')) AS dc_locations,
                   count(l.location_id) FILTER (WHERE l.regional_review_id IS NOT NULL) AS reviewed_region_only_locations
            FROM region r LEFT JOIN regional_analysis_locations l USING(sa4_code)
            GROUP BY r.sa4_code,r.sa4_name ORDER BY r.sa4_code
        """).df()
        if not checks["integrity_passed"]:
            (QA / "failed_validation.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
            raise ValueError(f"Database integrity checks failed: {checks}; final database not replaced")
        con.execute("COMMIT")
        con.execute("CHECKPOINT")
    regional_lookup = regional_locations.set_index("location_id")
    for source, target in [("sa4_code", "regional_sa4_code"),
                           ("regional_assignment_method", "regional_assignment_method"),
                           ("regional_review_id", "regional_review_id"),
                           ("coordinate_status", "regional_coordinate_status")]:
        locations[target] = locations.location_id.map(regional_lookup[source])
    for name, frame in {"cleaned_records": records, "locations": locations, "augmentation": attributes,
                        "operator_details": details, "site_matches": matches, "external_sites": sites,
                        "external_connectors": connectors, "osm_sites": osm_sites, "osm_site_matches": osm_matches,
                        "jolt_sites": jolt_sites, "jolt_site_matches": jolt_matches,
                        "ampol_sites": ampol_sites, "ampol_site_matches": ampol_matches}.items():
        frame.to_csv(OUT / (name + ".csv"), index=False)
    quality.to_csv(QA / "quality_issues.csv", index=False)
    identity_audit.to_csv(QA / "reviewed_identity.csv", index=False)
    identity_evidence.to_csv(QA / "reviewed_identity_evidence.csv", index=False)
    match_exclusions.to_csv(QA / "reviewed_match_exclusion.csv", index=False)
    coverage_attributes.to_csv(QA / "augmentation_attribute_coverage.csv", index=False)
    coverage_composition.to_csv(QA / "augmentation_composition.csv", index=False)
    resolution.to_csv(QA / "source_resolution.csv", index=False)
    reviewed_resolution.to_csv(QA / "reviewed_resolution.csv", index=False)
    region_reviews.to_csv(QA / "reviewed_region.csv", index=False)
    region_evidence.to_csv(QA / "reviewed_region_evidence.csv", index=False)
    regional_locations.to_csv(OUT / "regional_analysis_locations.csv", index=False)
    regional_counts.to_csv(QA / "regional_sa4_counts.csv", index=False)
    differences.to_csv(QA / "cross_source_attribute_differences.csv", index=False)
    connector_issues.to_csv(QA / "connector_quality_issues.csv", index=False)
    power_observations.to_csv(OUT / "location_power_observations.csv", index=False)
    duplicates.to_csv(QA / "removed_duplicates.csv", index=False)
    audit.to_csv(QA / "matching_candidates.csv", index=False)
    osm_audit.to_csv(QA / "osm_matching_candidates.csv", index=False)
    jolt_audit.to_csv(QA / "jolt_matching_candidates.csv", index=False)
    ampol_audit.to_csv(QA / "ampol_matching_candidates.csv", index=False)
    ampol_matches.sort_values(["score", "location_id"]).to_csv(QA / "ampol_matching_review_sample.csv", index=False)
    jolt_matches.sort_values(["score", "location_id"]).to_csv(QA / "jolt_matching_review_sample.csv", index=False)
    osm_matches.sort_values(["score", "location_id"]).head(30).to_csv(QA / "osm_matching_review_sample.csv", index=False)
    # Reproducible audit sample prioritises weakest accepted matches, not flattering examples.
    matches.sort_values(["score", "location_id"]).head(30).to_csv(QA / "matching_review_sample.csv", index=False)
    dcids = set(records.loc[records.charger_type == "DC", "location_id"])
    site_ids = set(attributes.loc[attributes.scope == "site", "location_id"])
    locations[locations.location_id.isin(dcids) & ~locations.location_id.isin(site_ids)].to_csv(QA / "unmatched_dc_locations.csv", index=False)
    locations[locations.sa4_method != "point_in_polygon"].to_csv(QA / "spatial_exceptions.csv", index=False)
    by_op = []
    for op, group in locations[locations.location_id.isin(dcids)].groupby("operator_name"):
        ids = set(group.location_id)
        by_op.append({"operator": op, "dc_locations": len(ids), "site_matches": len(ids & site_ids),
                      "any_augmentation": len(ids & set(attributes.location_id))})
    pd.DataFrame(by_op).to_csv(QA / "coverage_by_operator.csv", index=False)
    checks.update({"input_rows": len(raw), "cleaned_records": len(records), "locations": len(locations), "regions": len(regions),
                   "duplicate_rows_removed": len(duplicates), "quality_issue_counts": quality.code.value_counts().to_dict(),
                   "reviewed_identity_groups": int(identity_audit.review_id.nunique()),
                   "reviewed_identity_source_records": len(identity_audit),
                   "reviewed_identity_evidence_rows": len(identity_evidence),
                   "reviewed_match_exclusions": len(match_exclusions),
                   "cross_source_attribute_differences": len(differences),
                   "connector_quality_issues": len(connector_issues),
                   "source_conflict_resolution": resolution.decision.value_counts().to_dict(),
                   "reviewed_source_conflict_resolution": reviewed_resolution.decision.value_counts().to_dict(),
                   "unresolved_location_conflicts": int(locations.address_conflict.sum()),
                   "reviewed_region_only_locations": len(region_reviews),
                   "regional_analysis_locations": len(regional_locations),
                   "regional_analysis_dc_locations": int(regional_counts.dc_locations.sum()),
                   "location_conflicts_without_region_review": int(locations.address_conflict.sum())-len(region_reviews),
                   "missing_raw_fields": {k: int(raw[k].str.strip().eq("").sum()) for k in raw},
                   "sa4_assignment_methods": locations.sa4_method.value_counts().to_dict(),
                   "matching_decisions": audit.decision.value_counts().to_dict(),
                   "osm_matching_decisions": osm_audit.decision.value_counts().to_dict(),
                   "jolt_matching_decisions": jolt_audit.decision.value_counts().to_dict(),
                   "ampol_matching_decisions": ampol_audit.decision.value_counts().to_dict(),
                   "source_csv_sha256": sha256((RAW / "ev_20251216.csv").read_bytes()).hexdigest(),
                   "ocm_commit": json.loads((RAW / "ocm_revision.json").read_text(encoding="utf-8"))["sha"],
                   "limitations": ["CSV filename is December 2025; official resource metadata says effective April 2026.",
                                   "TfNSW source does not state coordinate CRS explicitly: WGS84 is an assumption.",
                                   "Operator-scope enrichment is not site-scope verification; coverage is reported separately.",
                                   f"{int(resolution.decision.eq('resolved').sum())} source conflicts resolved automatically; {len(reviewed_resolution)} further records resolved using archived reviewed evidence; {int(locations.address_conflict.sum())} remain excluded from the analysis-ready view.",
                                   f"{len(region_reviews)} conflicting locations have independently reviewed SA4 membership through whole-locality containment; their precise coordinates remain unresolved and are absent from the regional view.",
                                   "Coastal nearest assignment is an approximation, not an exact containment result.",
                                   "OCM observations may be older than the export; prices are unparsed historical text.",
                                   "Ampol connector labels are dated per-location website claims with repeated service descriptions; they are not live verification or a complete equipment inventory."]})
    (QA / "validation.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    (QA / "run_manifest.json").write_text(json.dumps({"completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "duckdb_version": duckdb.__version__, "input_snapshots": len(snapshots()), "database": DB.relative_to(ROOT).as_posix()}, indent=2), encoding="utf-8")
    # Exports can fail (for example, disk-full or a locked CSV). Publish the new
    # database only after all required exports have succeeded. Existing database
    # bytes remain intact on earlier failures; verification rejects partial CSVs.
    (QA / "failed_validation.json").unlink(missing_ok=True)
    temp.replace(DB)
    logging.info("Validation passed. DC augmentation coverage: %s", checks["coverage"])
    return checks


def validate_existing():
    if not DB.exists():
        raise FileNotFoundError(DB)
    with connect(DB) as con:
        checks = validate(con)
    print(json.dumps(checks, indent=2))
    if not checks["integrity_passed"]:
        raise ValueError("Database validation failed")
    return checks
