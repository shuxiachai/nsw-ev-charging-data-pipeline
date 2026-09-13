# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

import copy
import csv
from hashlib import sha256
import json

import duckdb
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ev_pipeline.acquire import ROOT
from ev_pipeline.clean import FIELDS
from ev_pipeline.matching_review import (
    MATCH_EXCLUSION_COLUMNS, apply_match_exclusions, database_match_exclusions_valid,
)


@pytest.fixture
def exclusion(tmp_path):
    config = json.loads((ROOT / "config/reviewed_match_exclusions.json").read_text(encoding="utf-8"))
    entry = config["exclusions"][0]
    # Exercise all provenance checks with small originals, never copy the 20 MB PDFs.
    entry["source_row"] = entry["expected_source"]["source_row"] = 2
    for role in ["source_snapshot", "external_snapshot", "evidence", "supporting_evidence"]:
        source = entry[role]
        target = tmp_path / source["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if role == "source_snapshot":
            with target.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow(entry["expected_raw_source"])
        elif role == "external_snapshot":
            target.write_text(json.dumps({"ID": entry["ocm_id"], "test_original": True}), encoding="utf-8")
        else:
            target.write_bytes(b"%PDF-1.4 test original " + role.encode())
        source["sha256"] = sha256(target.read_bytes()).hexdigest()
        source["bytes"] = target.stat().st_size
        metadata = {key: value for key, value in source.items() if key not in {"file", "locator"}}
        target.with_name(target.name + ".meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    source = dict(entry["expected_source"], raw_json=json.dumps(entry["expected_raw_source"]))
    records = pd.DataFrame([source])
    locations = records.copy()
    sites = pd.DataFrame([entry["expected_external"]])
    lid, ocm = source["location_id"], entry["ocm_id"]
    pairs = [{"location_id": lid, "ocm_id": ocm, "decision": "accepted"},
             {"location_id": "other-location", "ocm_id": ocm, "decision": "accepted"},
             {"location_id": lid, "ocm_id": 999, "decision": "accepted"}]
    matches, audit = pd.DataFrame(pairs), pd.DataFrame(pairs)
    attributes = pd.DataFrame([
        {"location_id": lid, "ocm_id": ocm, "jolt_id": None, "scope": "site", "value": "0.40"},
        {"location_id": lid, "ocm_id": None, "jolt_id": 52, "scope": "site", "value": "GGR005"},
        {"location_id": lid, "ocm_id": None, "jolt_id": None, "scope": "operator", "value": "jolt-url"},
        {"location_id": "other-location", "ocm_id": ocm, "jolt_id": None, "scope": "site", "value": "other"},
        {"location_id": lid, "ocm_id": 999, "jolt_id": None, "scope": "site", "value": "different-ocm"},
    ])
    return tmp_path, config, locations, records, sites, matches, audit, attributes


def apply(fixture):
    root, config, locations, records, sites, matches, audit, attributes = fixture
    return apply_match_exclusions(locations, records, sites, matches, audit, attributes, root=root, config=config)


def test_only_the_exact_ocm_tuple_is_withheld_and_inputs_are_unchanged(exclusion):
    originals = [frame.copy(deep=True) for frame in exclusion[2:]]
    matches, audit, attributes, ledger = apply(exclusion)
    assert list(matches.index) == [1, 2]
    assert list(attributes.value) == ["GGR005", "jolt-url", "other", "different-ocm"]
    assert audit.loc[0, "decision"] == "withheld_reviewed_evidence"
    assert audit.loc[0, "exclusion_review_id"] == exclusion[1]["exclusions"][0]["review_id"]
    assert audit.loc[1:, "exclusion_review_id"].eq("").all()
    assert list(ledger.columns) == MATCH_EXCLUSION_COLUMNS
    assert len(ledger) == 1
    assert ledger.iloc[0].decision == "withheld_pending_location_evidence"
    for original, current in zip(originals, exclusion[2:]):
        assert_frame_equal(original, current)


def test_repeat_application_is_identical_without_duplicate_ledger_rows(exclusion):
    first = apply(exclusion)
    root, config, locations, records, sites, *_ = exclusion
    second = apply_match_exclusions(locations, records, sites, *first[:3], root=root, config=config)
    for left, right in zip(first, second):
        assert_frame_equal(left, right)


def test_rejected_candidate_keeps_its_existing_decision_but_records_review(exclusion):
    exclusion[5].drop(index=0, inplace=True)
    exclusion[6].loc[0, "decision"] = "rejected_evidence"
    _, audit, attributes, ledger = apply(exclusion)
    assert audit.loc[0, "decision"] == "rejected_evidence"
    assert audit.loc[0, "exclusion_review_id"] == ledger.iloc[0].review_id
    assert "0.40" not in set(attributes.value)


def test_absent_candidate_is_still_recorded_without_inventing_candidate(exclusion):
    exclusion[5].drop(index=0, inplace=True)
    exclusion[6].drop(index=0, inplace=True)
    matches, audit, _, ledger = apply(exclusion)
    assert len(matches) == len(audit) == 2
    assert len(ledger) == 1


@pytest.mark.parametrize("role", ["source_snapshot", "external_snapshot", "evidence", "supporting_evidence"])
def test_changed_original_bytes_fail_atomically(exclusion, role):
    root, config, *frames = exclusion
    original = [frame.copy(deep=True) for frame in frames]
    path = root / config["exclusions"][0][role]["file"]
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="hash mismatch"):
        apply(exclusion)
    for left, right in zip(original, frames):
        assert_frame_equal(left, right)


@pytest.mark.parametrize("role", ["source_snapshot", "external_snapshot", "evidence", "supporting_evidence"])
@pytest.mark.parametrize("field", ["url", "sha256", "bytes", "retrieved_at_utc", "resolved_url"])
def test_each_source_manifest_is_bound(exclusion, role, field):
    root, config, *_ = exclusion
    path = root / (config["exclusions"][0][role]["file"] + ".meta.json")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata[field] = 1 if field == "bytes" else "changed"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata mismatch"):
        apply(exclusion)


@pytest.mark.parametrize("mutation", ["raw", "source_row", "cleaned_power", "representative", "membership", "external", "missing_guard"])
def test_raw_cleaned_representative_and_external_guards_cannot_be_skipped(exclusion, mutation):
    root, config, locations, records, sites, matches, audit, attrs = exclusion
    if mutation == "raw":
        raw = json.loads(records.loc[0, "raw_json"])
        raw["Number_of_plugs"] = "3"
        records.loc[0, "raw_json"] = json.dumps(raw)
    elif mutation == "source_row":
        records.loc[0, "source_row"] = 3
    elif mutation == "cleaned_power":
        records.loc[0, "power_max_kw"] = 99
    elif mutation == "representative":
        locations.loc[0, "record_id"] = "another-representative"
    elif mutation == "membership":
        records.loc[1] = records.loc[0]
        records.loc[1, "record_id"] = "another-member"
    elif mutation == "external":
        sites.loc[0, "usage_cost"] = "new-cost"
    else:
        del config["exclusions"][0]["expected_source"]["power_max_kw"]
    before = [matches.copy(), audit.copy(), attrs.copy()]
    with pytest.raises(ValueError):
        apply(exclusion)
    for left, right in zip(before, [matches, audit, attrs]):
        assert_frame_equal(left, right)


def test_second_invalid_review_cannot_partially_apply_the_first(exclusion):
    root, config, *_ = exclusion
    second = copy.deepcopy(config["exclusions"][0])
    second.update(review_id="second-review", record_id="missing-record")
    config["exclusions"].append(second)
    before = [frame.copy() for frame in exclusion[5:]]
    with pytest.raises(ValueError):
        apply(exclusion)
    for left, right in zip(before, exclusion[5:]):
        assert_frame_equal(left, right)


def test_source_csv_row_is_checked_even_when_config_hash_is_rebound(exclusion):
    root, config, *_ = exclusion
    source = config["exclusions"][0]["source_snapshot"]
    path = root / source["file"]
    path.write_text(path.read_text(encoding="utf-8").replace("25 kW", "26 kW"), encoding="utf-8")
    source["sha256"] = sha256(path.read_bytes()).hexdigest()
    source["bytes"] = path.stat().st_size
    path.with_name(path.name + ".meta.json").write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ValueError, match="CSV/raw identity"):
        apply(exclusion)


@pytest.mark.parametrize("problem", ["missing", "duplicate", "other_review"])
def test_candidate_audit_cannot_lose_or_misattribute_an_accepted_exclusion(exclusion, problem):
    audit = exclusion[6]
    if problem == "missing":
        audit.drop(index=0, inplace=True)
    elif problem == "duplicate":
        audit.loc[3] = audit.loc[0]
    else:
        audit["exclusion_review_id"] = ""
        audit.loc[0, "exclusion_review_id"] = "another-review"
    with pytest.raises(ValueError):
        apply(exclusion)


@pytest.fixture
def excluded_database(exclusion):
    root, config, locations, records, sites, *_ = exclusion
    matches, _, attributes, ledger = apply(exclusion)
    con = duckdb.connect(":memory:")
    con.register("record_input", records)
    con.execute("CREATE TABLE charger_record AS SELECT record_id,location_id,source_row,source_objectid,charger_type,number_of_plugs,power_min_kw,power_max_kw,power_kind,power_raw,source_category,raw_json FROM record_input")
    con.execute("CREATE TABLE location AS SELECT location_id,operator_id,station_name,address,latitude,longitude,postcode,address_postcode,address_conflict,lga AS source_lga FROM record_input")
    con.execute("CREATE TABLE operator AS SELECT DISTINCT operator_id,operator_name FROM record_input")
    con.register("sites_input", sites)
    con.execute("CREATE TABLE external_site AS SELECT * FROM sites_input")
    con.register("match_input", matches)
    con.execute("CREATE TABLE site_match AS SELECT * FROM match_input")
    con.register("attr_input", attributes)
    con.execute("CREATE TABLE augmentation AS SELECT * FROM attr_input")
    con.register("ledger_input", ledger)
    con.execute("CREATE TABLE reviewed_match_exclusion AS SELECT * REPLACE(CAST(review_date AS DATE) AS review_date) FROM ledger_input")
    con.execute("CREATE TABLE source_snapshot(source_file VARCHAR,url VARCHAR,sha256 VARCHAR,byte_count BIGINT,retrieved_at_utc TIMESTAMPTZ)")
    for role in ["source_snapshot", "external_snapshot", "evidence", "supporting_evidence"]:
        source = config["exclusions"][0][role]
        con.execute("INSERT INTO source_snapshot VALUES (?,?,?,?,?)", [source["file"], source["url"], source["sha256"], source["bytes"], source["retrieved_at_utc"]])
    yield con, root, config
    con.close()


def test_database_validation_accepts_complete_ledger_with_independent_source_binding(excluded_database):
    con, root, config = excluded_database
    assert database_match_exclusions_valid(con, root=root, config=config)


@pytest.mark.parametrize("mutation", [
    "DELETE FROM reviewed_match_exclusion",
    "UPDATE reviewed_match_exclusion SET evidence_source_file=source_file",
    "UPDATE reviewed_match_exclusion SET reason='wrongmatch'",
    "UPDATE source_snapshot SET url='https://wrong.example/'",
    "UPDATE source_snapshot SET sha256=repeat('0',64)",
    "UPDATE source_snapshot SET byte_count=1",
    "UPDATE charger_record SET source_row=3",
    "UPDATE charger_record SET raw_json='{}'",
    "UPDATE location SET address='different address'",
    "UPDATE external_site SET usage_cost='new cost'",
    "INSERT INTO site_match SELECT location_id,ocm_id,'accepted' FROM reviewed_match_exclusion",
    "INSERT INTO augmentation SELECT location_id,ocm_id,NULL,'site','residual' FROM reviewed_match_exclusion",
])
def test_database_validation_rejects_partial_ledger_drift_or_residual_attributes(excluded_database, mutation):
    con, root, config = excluded_database
    con.execute(mutation)
    assert not database_match_exclusions_valid(con, root=root, config=config)
