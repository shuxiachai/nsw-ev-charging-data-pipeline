# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Verify narrowly scoped, manually reviewed address-conflict exceptions.

An exception only supplies address evidence to the ordinary matcher. It never
overrides distance, operator, postcode, source-conflict, ambiguity or reuse gates.
"""
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from .acquire import ROOT
from .clean import text


def _pinned_source(root, source, *, extracted_evidence=False):
    filename = source["file"]
    path = (root / filename).resolve()
    if not path.is_relative_to((root / "data/raw").resolve()):
        raise ValueError(f"Matching review source escapes raw directory: {filename}")
    expected = source["sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"Invalid matching review SHA-256: {filename}")
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Matching review source hash mismatch: {filename}")
    if extracted_evidence:
        metadata = json.loads(path.with_name(path.name + ".meta.json").read_text(encoding="utf-8"))
        if (metadata.get("sha256") != actual or metadata.get("bytes") != path.stat().st_size
                or metadata.get("url") != source["url"] or not metadata.get("retrieved_at_utc")
                or metadata.get("capture_method") != "web_tool_extract_transcript"
                or metadata.get("original_http_response") is not False):
            raise ValueError(f"Matching review evidence metadata mismatch: {filename}")
    return path


def _guard(row, expected, label):
    for field, value in expected.items():
        actual = row.get(field)
        if field in {"latitude", "longitude"}:
            try:
                valid = math.isclose(float(actual), value, rel_tol=0, abs_tol=1e-10)
            except (TypeError, ValueError):
                valid = False
        else:
            valid = text(actual) == text(value)
        if not valid:
            raise ValueError(f"Matching review {label} guard failed: {field}")


def load_address_exceptions(locations, records, sites, *, root=ROOT, config=None):
    """Return verified exceptions keyed by current location and OCM identity.

    Both original source snapshots and the actual rows supplied to the matcher
    are guarded, so refreshing data or changing a reviewed site needs a review.
    Source record IDs, rather than mutable location IDs, anchor the decisions.
    """
    root = Path(root)
    if config is None:
        config = json.loads((root / "config/reviewed_match_exceptions.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported matching review configuration")
    date.fromisoformat(config["review_date"])
    result, review_ids = {}, set()
    for entry in config["exceptions"]:
        review_id = entry["review_id"]
        if not review_id or review_id in review_ids:
            raise ValueError("Missing or duplicate matching review identifier")
        review_ids.add(review_id)
        if entry["allowed_conflict"] not in {"house_number_conflict", "street_type_conflict"}:
            raise ValueError("Unsupported matching review conflict")
        _pinned_source(root, entry["source_snapshot"])
        external_path = _pinned_source(root, entry["external_snapshot"])
        _pinned_source(root, entry["evidence"], extracted_evidence=True)
        source = records.loc[records.record_id.eq(entry["record_id"])]
        external = sites.loc[sites.ocm_id.eq(entry["ocm_id"])]
        if len(source) != 1 or len(external) != 1:
            raise ValueError(f"Matching review source/external record missing or ambiguous: {review_id}")
        source, external = source.iloc[0], external.iloc[0]
        _guard(source, entry["expected_source"], "source")
        original = json.loads(source.raw_json)
        if original != entry["expected_raw_source"]:
            raise ValueError(f"Matching review original source guard failed: {review_id}")
        _guard(external, entry["expected_external"], "external")
        original_external = json.loads(external_path.read_text(encoding="utf-8"))
        if original_external.get("ID") != entry["ocm_id"] or external.source_file != entry["external_snapshot"]["file"]:
            raise ValueError(f"Matching review external identity guard failed: {review_id}")
        representative = locations.loc[locations.location_id.eq(source.location_id)]
        if len(representative) != 1:
            raise ValueError(f"Matching review location missing or ambiguous: {review_id}")
        _guard(representative.iloc[0], {field: entry["expected_source"][field] for field in
                                      ["address", "operator_name", "postcode", "latitude", "longitude"]}, "location")
        key = (source.location_id, entry["ocm_id"])
        if key in result:
            raise ValueError(f"Duplicate matching review pair: {review_id}")
        result[key] = {"allowed_conflict": entry["allowed_conflict"], "review_id": review_id,
                       "record_id": source.record_id, "source_file": entry["evidence"]["file"],
                       "evidence_sha256": entry["evidence"]["sha256"], "reason": entry["reason"]}
    return result


def database_address_exceptions_valid(con, *, root=ROOT, config=None):
    """Independently check accepted OCM conflicts against the reviewed ledger.

    Inspect the actual database addresses even if both review columns were
    cleared. A nonempty review label or an arbitrary existing snapshot alone
    cannot establish the reviewed source/external pair or its evidence.
    """
    # Local import avoids the matching_review -> augment -> matching_review
    # import cycle while sharing the exact address-conflict interpretation.
    from .augment import extended_address_conflict

    if config is None:
        config = json.loads((Path(root) / "config/reviewed_match_exceptions.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        return False
    record_locations = dict(con.execute("SELECT record_id,location_id FROM charger_record").fetchall())
    approved = {}
    for entry in config["exceptions"]:
        location_id = record_locations.get(entry["record_id"])
        if location_id is None:
            continue
        key = (location_id, entry["ocm_id"])
        if key in approved:
            return False
        approved[key] = entry
    rows = con.execute("""
        SELECT m.location_id, m.ocm_id, l.address, e.address,
               m.address_exception_review_id, m.address_exception_source_file,
               s.sha256
        FROM site_match m JOIN location l USING(location_id)
        JOIN external_site e USING(ocm_id)
        LEFT JOIN source_snapshot s ON s.source_file=m.address_exception_source_file
    """).fetchall()
    for location_id, ocm_id, source_address, external_address, review_id, evidence_file, digest in rows:
        conflict = extended_address_conflict(source_address, external_address)
        if not conflict:
            if review_id is not None or evidence_file is not None:
                return False  # An ordinary match cannot claim an unused review.
            continue
        entry = approved.get((location_id, ocm_id))
        if (entry is None or conflict != entry["allowed_conflict"]
                or review_id != entry["review_id"] or evidence_file != entry["evidence"]["file"]
                or digest != entry["evidence"]["sha256"]
                or text(source_address) != text(entry["expected_source"]["address"])
                or text(external_address) != text(entry["expected_external"]["address"])):
            return False
    return True


# Exclusions are separate from the positive address evidence above: they never
# make another candidate eligible and only remove an explicitly reviewed OCM pair.
MATCH_EXCLUSION_COLUMNS = [
    "review_id", "record_id", "source_row", "location_id", "ocm_id", "source_file",
    "external_source_file", "evidence_source_file", "supporting_source_file",
    "decision", "reason", "review_date",
]
_EXCLUSION_RECORD_FIELDS = {
    "record_id", "location_id", "source_row", "source_objectid", "station_name",
    "address", "operator_name", "operator_id", "latitude", "longitude", "postcode",
    "address_postcode", "address_conflict", "lga", "charger_type", "number_of_plugs",
    "power_min_kw", "power_max_kw", "power_kind", "power_raw", "source_category",
}
_EXCLUSION_EXTERNAL_FIELDS = {
    "ocm_id", "ocm_operator_id", "ocm_operator", "title", "address", "town", "postcode",
    "latitude", "longitude", "usage_cost", "access_comments", "usage_type", "status",
    "last_verified", "number_of_points", "data_provider", "data_license", "source_file",
    "source_url", "has_dc",
}
_EXCLUSION_SOURCES = ["source_snapshot", "external_snapshot", "evidence", "supporting_evidence"]


def _exclusion_guard(row, expected, label):
    """Compare every configured cleaned field without normalising changed text."""
    import pandas as pd

    for field, value in expected.items():
        if field not in row:
            raise ValueError(f"Match exclusion {label} guard missing field: {field}")
        actual = row[field]
        if pd.isna(actual):
            actual = None
        if isinstance(value, float):
            valid = actual is not None and math.isfinite(float(actual)) and math.isclose(
                float(actual), value, rel_tol=0, abs_tol=1e-10)
        else:
            valid = actual == value
        if not valid:
            raise ValueError(f"Match exclusion {label} guard failed: {field}")


def _exclusion_snapshot(root, source):
    """Bind original response bytes and provenance, including their original time."""
    from datetime import datetime

    required = {"file", "url", "resolved_url", "retrieved_at_utc", "sha256", "bytes"}
    if not required.issubset(source) or not source["url"].startswith("https://"):
        raise ValueError("Incomplete match exclusion source provenance")
    if (type(source["bytes"]) is not int or source["bytes"] <= 0
            or datetime.fromisoformat(source["retrieved_at_utc"]).tzinfo is None):
        raise ValueError("Invalid match exclusion source provenance")
    path = _pinned_source(root, source)
    metadata = json.loads(path.with_name(path.name + ".meta.json").read_text(encoding="utf-8"))
    if (any(metadata.get(key) != source[key] for key in required - {"file"})
            or path.stat().st_size != source["bytes"]
            or metadata.get("original_http_response") is False):
        raise ValueError(f"Match exclusion source metadata mismatch: {source['file']}")
    return path


def _validated_match_exclusions(locations, records, sites, *, root, config):
    """Validate the entire plan before any caller-owned frame can be changed."""
    import csv
    from .clean import FIELDS, identifier

    root = Path(root)
    if config is None:
        config = json.loads((root / "config/reviewed_match_exclusions.json").read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported match exclusion configuration")
    date.fromisoformat(config["review_date"])
    reviewed, review_ids, pairs = [], set(), set()
    for entry in config["exclusions"]:
        rid, ocm_id, review_id = entry["record_id"], entry["ocm_id"], entry["review_id"]
        if not review_id or review_id in review_ids or (rid, ocm_id) in pairs:
            raise ValueError("Duplicate or missing match exclusion identity")
        review_ids.add(review_id)
        pairs.add((rid, ocm_id))
        if (entry["decision"] != "withheld_pending_location_evidence"
                or entry["reason"] != "withheld_pending_location_evidence"
                or type(entry["source_row"]) is not int or entry["source_row"] < 2
                or type(ocm_id) is not int or ocm_id <= 0
                or entry["representative_record_id"] != rid):
            raise ValueError("Invalid single-record match exclusion scope")
        if (set(entry["expected_source"]) != _EXCLUSION_RECORD_FIELDS
                or set(entry["expected_external"]) != _EXCLUSION_EXTERNAL_FIELDS
                or set(entry["expected_raw_source"]) != set(FIELDS)):
            raise ValueError("Incomplete match exclusion row guard")
        paths = {role: _exclusion_snapshot(root, entry[role]) for role in _EXCLUSION_SOURCES}
        for role in ["evidence", "supporting_evidence"]:
            if not entry[role].get("locator"):
                raise ValueError("Match exclusion evidence locator missing")
        with paths["source_snapshot"].open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if set(reader.fieldnames or []) != set(FIELDS):
                raise ValueError("Match exclusion source CSV fields changed")
            original = next((row for number, row in enumerate(reader, 2)
                             if number == entry["source_row"]), None)
        expected_raw = entry["expected_raw_source"]
        if (original != expected_raw
                or identifier("r_", {key: text(value) for key, value in expected_raw.items()}) != rid):
            raise ValueError("Match exclusion source CSV/raw identity guard failed")
        source = records.loc[records.record_id.eq(rid)]
        external = sites.loc[sites.ocm_id.eq(ocm_id)]
        if len(source) != 1 or len(external) != 1:
            raise ValueError("Match exclusion source/external missing or ambiguous")
        source, external = source.iloc[0], external.iloc[0]
        _exclusion_guard(source, entry["expected_source"], "source")
        if source.source_row != entry["source_row"] or json.loads(source.raw_json) != expected_raw:
            raise ValueError("Match exclusion original source guard failed")
        members = records.loc[records.location_id.eq(source.location_id)]
        representative = locations.loc[locations.location_id.eq(source.location_id)]
        if len(members) != 1 or len(representative) != 1:
            raise ValueError("Match exclusion reviewed location membership changed")
        _exclusion_guard(representative.iloc[0], entry["expected_source"], "representative")
        _exclusion_guard(external, entry["expected_external"], "external")
        if (json.loads(paths["external_snapshot"].read_text(encoding="utf-8")).get("ID") != ocm_id
                or external.source_file != entry["external_snapshot"]["file"]):
            raise ValueError("Match exclusion external source relationship changed")
        ledger = dict(zip(MATCH_EXCLUSION_COLUMNS, [review_id, rid, entry["source_row"],
            source.location_id, ocm_id, entry["source_snapshot"]["file"],
            entry["external_snapshot"]["file"], entry["evidence"]["file"],
            entry["supporting_evidence"]["file"], entry["decision"], entry["reason"], config["review_date"]]))
        reviewed.append((entry, ledger))
    return reviewed


def apply_match_exclusions(locations, records, sites, matches, audit, attributes, *, root=ROOT, config=None):
    """Withhold exact reviewed OCM pairs, preserving other networks and operators.

    All guards and candidate consistency checks precede copies/mutations. Calling
    this again yields the same frames and one ledger row per configured decision.
    """
    import pandas as pd

    reviewed = _validated_match_exclusions(locations, records, sites, root=root, config=config)
    for _, entry in reviewed:
        key = (entry["location_id"], entry["ocm_id"])
        selected = matches.location_id.eq(key[0]) & matches.ocm_id.eq(key[1])
        candidate = audit.location_id.eq(key[0]) & audit.ocm_id.eq(key[1])
        if selected.sum() > 1 or candidate.sum() > 1 or (selected.any() and not candidate.any()):
            raise ValueError("Match exclusion candidate audit missing or duplicated")
        if "exclusion_review_id" in audit and candidate.any():
            old_review = text(audit.loc[candidate, "exclusion_review_id"].iloc[0])
            if old_review and old_review != entry["review_id"]:
                raise ValueError("Match exclusion candidate already names another review")
    matches, audit, attributes = matches.copy(), audit.copy(), attributes.copy()
    if "exclusion_review_id" not in audit:
        audit["exclusion_review_id"] = ""
    for _, entry in reviewed:
        lid, ocm_id = entry["location_id"], entry["ocm_id"]
        matches = matches.loc[~(matches.location_id.eq(lid) & matches.ocm_id.eq(ocm_id))].copy()
        candidate = audit.location_id.eq(lid) & audit.ocm_id.eq(ocm_id)
        audit.loc[candidate & audit.decision.eq("accepted"), "decision"] = "withheld_reviewed_evidence"
        audit.loc[candidate, "exclusion_review_id"] = entry["review_id"]
        attributes = attributes.loc[~(attributes.location_id.eq(lid) & attributes.ocm_id.eq(ocm_id)
                                      & attributes.scope.eq("site"))].copy()
    ledger = pd.DataFrame([row for _, row in reviewed], columns=MATCH_EXCLUSION_COLUMNS)
    return matches, audit, attributes, ledger


def database_match_exclusions_valid(con, *, root=ROOT, config=None):
    """Independently bind the stored exclusion ledger and prove no OCM remnants.

    Reconstruct original/representative fields from stored base tables, without
    running the matcher or accepting a ledger label as proof of its own validity.
    """
    from datetime import datetime
    import duckdb

    try:
        records = con.execute("""
            SELECT c.*,l.station_name,l.address,o.operator_name,l.operator_id,
                   l.latitude,l.longitude,l.postcode,l.address_postcode,l.address_conflict,
                   l.source_lga AS lga
            FROM charger_record c JOIN location l USING(location_id)
            JOIN operator o USING(operator_id)
        """).df()
        sites = con.execute("SELECT * FROM external_site").df()
        reviewed = _validated_match_exclusions(records, records, sites, root=root, config=config)
        actual = con.execute("SELECT " + ",".join(MATCH_EXCLUSION_COLUMNS)
                             + " FROM reviewed_match_exclusion ORDER BY review_id").fetchall()
        expected = sorted([tuple(row[column] if column != "review_date" else date.fromisoformat(row[column])
                                 for column in MATCH_EXCLUSION_COLUMNS) for _, row in reviewed])
        if actual != expected:
            return False
        for entry, row in reviewed:
            for role in _EXCLUSION_SOURCES:
                source = entry[role]
                snapshots = con.execute("""
                    SELECT url,sha256,byte_count,retrieved_at_utc FROM source_snapshot WHERE source_file=?
                """, [source["file"]]).fetchall()
                if (len(snapshots) != 1 or snapshots[0][:3] != (source["url"], source["sha256"], source["bytes"])
                        or snapshots[0][3] != datetime.fromisoformat(source["retrieved_at_utc"])):
                    return False
            pair = [row["location_id"], row["ocm_id"]]
            if con.execute("SELECT count(*) FROM site_match WHERE location_id=? AND ocm_id=?", pair).fetchone()[0]:
                return False
            if con.execute("SELECT count(*) FROM augmentation WHERE location_id=? AND ocm_id=? AND scope='site'", pair).fetchone()[0]:
                return False
        return True
    except (ValueError, KeyError, TypeError, IndexError, OSError, AttributeError, duckdb.Error):
        return False
