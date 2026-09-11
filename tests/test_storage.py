import json
from hashlib import sha256
import pytest
import duckdb
from ev_pipeline.acquire import fetch
from ev_pipeline.pipeline import DB, connect, validate


def test_offline_cache_requires_matching_hash_and_source(tmp_path):
    path = tmp_path / "input.json"
    path.write_bytes(b"{}")
    meta = path.with_name("input.json.meta.json")
    meta.write_text(json.dumps({"url": "https://example.test/input", "sha256": sha256(b"{}").hexdigest()}))
    assert fetch("https://example.test/input", path, offline=True) == path
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="mismatch"):
        fetch("https://example.test/input", path, offline=True)
    with pytest.raises(FileNotFoundError, match="Offline"):
        fetch("https://example.test/missing", tmp_path / "missing", offline=True)


def test_database_integrity_and_coverage_use_distinct_locations():
    assert DB.exists(), "Run python -m ev_pipeline all before integration tests"
    with connect(DB) as con:
        result = validate(con)
        assert result["integrity_passed"]
        assert result["coverage"]["site_scope_target_met"], result["coverage"]
        expected = con.execute("SELECT count(DISTINCT location_id) FROM charger_record WHERE charger_type='DC'").fetchone()[0]
        assert result["coverage"]["dc_locations"] == expected
        assert result["coverage"]["augmented_site_scope"] <= expected
        assert con.execute("SELECT count(*) FROM quality_issue WHERE code='postcode_address_conflict'").fetchone()[0] > 0


def test_foreign_keys_and_checks_reject_bad_data():
    with connect(DB) as con:
        con.execute("BEGIN TRANSACTION")
        with pytest.raises(duckdb.ConstraintException):
            con.execute("INSERT INTO operator VALUES ('test-id',NULL)")
        con.execute("ROLLBACK")
        con.execute("BEGIN TRANSACTION")
        with pytest.raises(duckdb.ConstraintException):
            con.execute("INSERT INTO charger_record(record_id,location_id,source_row,charger_type,power_kind,power_raw,raw_json) VALUES ('invalid','missing-location',1,'DC','unknown','AC','{}')")
        con.execute("ROLLBACK")


@pytest.mark.parametrize("column", ["address_similarity", "cross_source_distance_m", "new_postcode", "new_latitude", "new_longitude"])
def test_resolved_source_requires_nonnull_evidence(column):
    with connect(DB) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            with pytest.raises(duckdb.ConstraintException):
                con.execute(f"UPDATE source_resolution SET {column}=NULL WHERE decision='resolved'")
        finally:
            con.execute("ROLLBACK")


def test_export_failure_preserves_previous_database(tmp_path, monkeypatch):
    from ev_pipeline import pipeline
    import pandas as pd

    out, qa = tmp_path / "data/processed", tmp_path / "outputs"
    out.mkdir(parents=True)
    database = out / "ev_chargers.duckdb"
    previous = b"previous completed database must survive an export failure"
    database.write_bytes(previous)
    monkeypatch.setattr(pipeline, "OUT", out)
    monkeypatch.setattr(pipeline, "QA", qa)
    monkeypatch.setattr(pipeline, "DB", database)

    def fail_export(*args, **kwargs):
        raise OSError("injected CSV export failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_export)
    with pytest.raises(OSError, match="injected CSV export failure"):
        pipeline.build(offline=True)
    assert database.read_bytes() == previous


@pytest.fixture
def logical_database_copy():
    """Corrupt an isolated logical copy to test validation independently of DDL.

    The live deliverable is only attached read-only. The copy deliberately lacks
    constraints so bad persisted/imported states reach the validation queries.
    """
    with connect(":memory:") as con:
        con.execute("ATTACH '" + str(DB).replace("'", "''") + "' AS baseline (READ_ONLY)")
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_catalog='baseline' AND table_schema='main' AND table_type='BASE TABLE'").fetchall()
        for (name,) in tables:
            con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM baseline."{name}"')
        for name in ["dc_locations", "analysis_ready_locations", "regional_analysis_locations", "dc_augmentation_coverage", "location_power_observations"]:
            con.execute(con.execute("SELECT sql FROM duckdb_views() WHERE database_name='baseline' AND view_name=?", [name]).fetchone()[0])
        con.execute("DETACH baseline")
        assert validate(con)["integrity_passed"]
        yield con


@pytest.mark.parametrize("mutation", [
    "UPDATE amp_charge_site SET dc_connector_types='invented connector' WHERE has_dc",
    "UPDATE amp_charge_site SET longitude=longitude+0.01 WHERE has_dc",
    "UPDATE source_snapshot SET retrieved_at_utc=retrieved_at_utc+INTERVAL '1 day' WHERE source_file LIKE 'data/raw/ampol/%'",
    "DELETE FROM amp_charge_site_match",
    "UPDATE amp_charge_site_match SET distance_m=0",
    "UPDATE augmentation SET value='invented connector' WHERE ampol_id IS NOT NULL",
    "DELETE FROM augmentation WHERE ampol_id IS NOT NULL",
    "INSERT INTO augmentation SELECT 'misattributed-ampol',a.location_id,a.attribute,'invented CCS1',a.scope,NULL,NULL,m.osm_id,NULL,NULL,a.source_file,a.method FROM augmentation a JOIN osm_site_match m USING(location_id) WHERE a.ampol_id IS NOT NULL LIMIT 1",
    "DELETE FROM quality_issue WHERE code='address_postcode_locality_mismatch'",
    "UPDATE quality_issue SET detail='not a problem' WHERE code='address_postcode_locality_mismatch'",
    "DELETE FROM quality_issue WHERE code='operator_label_review_required'",
    "UPDATE jolt_site SET carpark_hours_text='Carpark open 0:00-24:00' WHERE carpark_hours_text IS NOT NULL",
    "DELETE FROM augmentation WHERE attribute='operator_carpark_hours_text'",
    "UPDATE augmentation SET value='Carpark open 0:00-24:00' WHERE attribute='operator_carpark_hours_text'",
    "UPDATE charger_record SET source_row=2",
    "UPDATE source_snapshot SET sha256=repeat('g',64)",
    "UPDATE charger_record SET power_max_kw=-1,power_min_kw=NULL WHERE power_min_kw IS NULL",
    "UPDATE external_connector SET power_kw='NaN'::DOUBLE WHERE power_kw IS NOT NULL",
    "CREATE TABLE saved_power AS SELECT * FROM location_power_observations; CREATE OR REPLACE VIEW location_power_observations AS SELECT * FROM saved_power WHERE FALSE",
    "DELETE FROM reviewed_region_evidence WHERE role='venue_address'",
    "UPDATE reviewed_region SET reviewed_sa4_code=source_point_sa4_code",
    "UPDATE reviewed_region SET coordinate_status='precise'",
    "UPDATE reviewed_region SET locality_geometry=ST_Buffer(ST_Point(151,-33),0.01)",
    "UPDATE reviewed_region SET operator_element_id='NRMA wrong place'",
    "UPDATE reviewed_region SET reason='unsupported decision'",
    "UPDATE source_snapshot SET retrieved_at_utc=retrieved_at_utc+INTERVAL '1 day' WHERE source_file IN (SELECT locality_source_file FROM reviewed_region)",
    "DELETE FROM reviewed_region",
    "CREATE TABLE saved_regional AS SELECT * FROM regional_analysis_locations; CREATE OR REPLACE VIEW regional_analysis_locations AS SELECT v.*,l.geometry FROM saved_regional v JOIN location l USING(location_id)",
    "CREATE OR REPLACE VIEW regional_analysis_locations AS SELECT location_id,sa4_code,sa4_code AS source_point_sa4_code,sa4_method AS regional_assignment_method,NULL::VARCHAR AS regional_review_id,'unresolved' AS coordinate_status FROM location WHERE FALSE",
    "UPDATE source_snapshot SET sha256=repeat('0',64) WHERE source_file='data/raw/jolt_map.html'",
    "UPDATE source_snapshot SET retrieved_at_utc=retrieved_at_utc+INTERVAL '1 day' WHERE source_file='data/raw/jolt_map.html'",
    "UPDATE source_snapshot SET url='https://example.com/wrong-map' WHERE source_file='data/raw/jolt_map.html'",
    "UPDATE source_snapshot SET byte_count=byte_count+1 WHERE source_file='data/raw/jolt_map.html'",
    "UPDATE reviewed_resolution SET corroborating_role='same_operator_charger' WHERE corroborating_role='mapped_landmark'",
    "DELETE FROM reviewed_match_exclusion",
    "UPDATE reviewed_match_exclusion SET source_row=99999",
    "UPDATE reviewed_match_exclusion SET evidence_source_file=source_file",
    "INSERT INTO site_match SELECT location_id,ocm_id,10,1,1,'tampered',NULL,NULL FROM reviewed_match_exclusion",
    "INSERT INTO augmentation(augmentation_id,location_id,attribute,value,scope,ocm_id,source_file,method) SELECT 'held-attribute',location_id,'usage_cost_text','unsafe','site',ocm_id,external_source_file,'tampered' FROM reviewed_match_exclusion",
    "UPDATE jolt_site SET network_status_snapshot='temporarily unavailable' WHERE network_status_snapshot='available'",
    "UPDATE augmentation SET value='unavailable' WHERE attribute='operator_evse_status_snapshot' AND value='available'",
    "DELETE FROM augmentation WHERE attribute='operator_network_status_snapshot'",
    "UPDATE augmentation SET source_file='data/raw/ev_20251216.csv' WHERE attribute='operator_evse_status_snapshot'",
    "UPDATE location SET sa4_method='typo_method',sa4_code=(SELECT min(sa4_code) FROM region) WHERE location_id=(SELECT location_id FROM location WHERE sa4_code<>(SELECT min(sa4_code) FROM region) LIMIT 1)",
    "UPDATE location SET sa4_distance_m=-1 WHERE sa4_method='coastal_nearest_within_50m'",
    "UPDATE location SET sa4_distance_m='NaN'::DOUBLE WHERE sa4_method='coastal_nearest_within_50m'",
    "UPDATE location SET sa4_code=(SELECT min(sa4_code) FROM region) WHERE sa4_method='coastal_nearest_within_50m'",
    "UPDATE source_resolution SET new_postcode='9999' WHERE decision='resolved'",
    "UPDATE reviewed_identity SET source_row=999999 WHERE record_id=(SELECT min(record_id) FROM reviewed_identity)",
    "DELETE FROM reviewed_identity WHERE record_id=(SELECT min(record_id) FROM reviewed_identity)",
    "DELETE FROM reviewed_identity_evidence WHERE review_id=(SELECT min(review_id) FROM reviewed_identity_evidence)",
    "UPDATE reviewed_identity_evidence SET sha256=repeat('0',64) WHERE review_id=(SELECT min(review_id) FROM reviewed_identity_evidence)",
    "UPDATE reviewed_resolution SET supporting_address_source_file=NULL,supporting_address_locator=NULL WHERE supporting_address_source_file IS NOT NULL",
    "UPDATE reviewed_resolution SET address_source_file='data/raw/ev_20251216.csv' WHERE source_row=727",
    "UPDATE location SET latitude=latitude+0.000001 WHERE location_id=(SELECT min(location_id) FROM reviewed_identity)",
    "UPDATE site_match SET address_exception_review_id='unpaired-review' WHERE location_id=(SELECT min(location_id) FROM site_match)",
    "UPDATE external_connector SET quantity=-1 WHERE ocm_id=(SELECT min(ocm_id) FROM external_connector)",
    "CREATE OR REPLACE VIEW analysis_ready_locations AS SELECT * FROM location WHERE FALSE",
    "CREATE OR REPLACE VIEW dc_locations AS SELECT l.*,o.operator_name FROM location l JOIN operator o USING(operator_id) WHERE FALSE",
    "CREATE OR REPLACE VIEW dc_augmentation_coverage AS SELECT 1 AS dc_locations,1 AS augmented_any_scope,1 AS augmented_site_scope",
])
def test_independent_validation_rejects_bad_spatial_and_resolution_states(logical_database_copy, mutation):
    logical_database_copy.execute(mutation)
    assert not validate(logical_database_copy)["integrity_passed"]


@pytest.mark.parametrize("assignment", [
    "original_latitude=NULL,original_longitude=NULL",
    "original_latitude=NULL,latitude=latitude+0.000001,geometry=ST_Point(longitude,latitude+0.000001)",
    "original_latitude=latitude+0.000001,latitude=latitude+0.000001,geometry=ST_Point(longitude,latitude+0.000001)",
])
def test_original_coordinate_evidence_cannot_be_erased_or_rewritten(logical_database_copy, assignment):
    logical_database_copy.execute(
        "UPDATE location SET " + assignment +
        " WHERE location_id=(SELECT location_id FROM charger_record WHERE source_row=2)")
    result = validate(logical_database_copy)
    assert not result["integrity_passed"]
    assert not result["integrity_checks"]["original_coordinates_match_source_representatives"]
    if "NULL" in assignment:
        assert not result["integrity_checks"]["coordinate_changes_have_resolution_evidence"]


@pytest.mark.parametrize("assignment", ["sa4_method='typo_method'", "sa4_distance_m=-1", "sa4_distance_m='Infinity'::DOUBLE"])
def test_spatial_constraints_reject_invalid_method_and_distance(assignment):
    with connect(DB) as con:
        con.execute("BEGIN TRANSACTION")
        try:
            with pytest.raises(duckdb.ConstraintException):
                con.execute(f"UPDATE location SET {assignment} WHERE sa4_method='coastal_nearest_within_50m'")
        finally:
            con.execute("ROLLBACK")
