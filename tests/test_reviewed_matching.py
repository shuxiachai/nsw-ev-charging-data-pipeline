import json
from pathlib import Path
import shutil

import duckdb
import pandas as pd
import pytest

from ev_pipeline.acquire import ROOT
from ev_pipeline.augment import GEOD, match_sites
from ev_pipeline.matching_review import database_address_exceptions_valid, load_address_exceptions
from tests.test_matching import frames


@pytest.fixture
def reviewed(tmp_path):
    config = json.loads((ROOT / "config/reviewed_match_exceptions.json").read_text(encoding="utf-8"))
    entry = config["exceptions"][0]
    for source in [entry["source_snapshot"], entry["external_snapshot"], entry["evidence"]]:
        target = tmp_path / source["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source["file"], target)
        metadata = (ROOT / source["file"]).with_name(Path(source["file"]).name + ".meta.json")
        if metadata.exists():
            shutil.copyfile(metadata, target.with_name(target.name + ".meta.json"))
    record = dict(entry["expected_source"], record_id=entry["record_id"], location_id="reviewed_location",
                  raw_json=json.dumps(entry["expected_raw_source"]), address_conflict=False)
    records = pd.DataFrame([record])
    sites = pd.DataFrame([dict(entry["expected_external"], ocm_id=entry["ocm_id"], has_dc=True,
                              source_file=entry["external_snapshot"]["file"])])
    return tmp_path, config, records.copy(), records, sites


def test_only_pinned_dan_murphy_pair_can_bypass_its_address_conflict(reviewed):
    root, config, locations, records, sites = reviewed
    assert match_sites(locations, records, sites)[0].empty
    exceptions = load_address_exceptions(locations, records, sites, root=root, config=config)
    matches, audit = match_sites(locations, records, sites, address_exceptions=exceptions)
    assert len(matches) == 1
    row = audit.iloc[0]
    assert row.extended_address_conflict == "house_number_conflict"
    assert row.address_exception_applied
    assert row.address_exception_record_id == records.iloc[0].record_id
    assert row.address_exception_review_id == config["exceptions"][0]["review_id"]
    assert row.address_exception_evidence_sha256 == config["exceptions"][0]["evidence"]["sha256"]
    other = locations.copy()
    other.loc[0, "location_id"] = "other_location"
    other_records = records.copy()
    other_records.loc[0, "location_id"] = "other_location"
    assert match_sites(other, other_records, sites, address_exceptions=exceptions)[0].empty


@pytest.mark.parametrize("source", ["source_snapshot", "external_snapshot", "evidence"])
def test_changed_pinned_source_cannot_silently_reuse_review(reviewed, source):
    root, config, locations, records, sites = reviewed
    path = root / config["exceptions"][0][source]["file"]
    path.write_bytes(path.read_bytes() + b"\nchanged\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_address_exceptions(locations, records, sites, root=root, config=config)


def test_evidence_transcript_cannot_be_misrepresented_as_original_http_response(reviewed):
    root, config, locations, records, sites = reviewed
    path = root / (config["exceptions"][0]["evidence"]["file"] + ".meta.json")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["original_http_response"] = True
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata mismatch"):
        load_address_exceptions(locations, records, sites, root=root, config=config)


@pytest.mark.parametrize("changed", ["source_address", "source_point", "raw_source", "external_address", "location_address"])
def test_review_rejects_drift_in_rows_actually_supplied_to_matcher(reviewed, changed):
    root, config, locations, records, sites = reviewed
    if changed == "source_address":
        records.loc[0, "address"] = "999 Orient St"
    elif changed == "source_point":
        records.loc[0, "latitude"] += 0.001
    elif changed == "raw_source":
        raw = json.loads(records.iloc[0].raw_json)
        raw["Station_address"] = "999 Orient St"
        records.loc[0, "raw_json"] = json.dumps(raw)
    elif changed == "external_address":
        sites.loc[0, "address"] = "999 Orient St"
    else:
        locations.loc[0, "address"] = "999 Orient St"
    with pytest.raises(ValueError, match="guard failed"):
        load_address_exceptions(locations, records, sites, root=root, config=config)


@pytest.mark.parametrize("gate", ["operator", "postcode", "source_conflict", "distance", "ambiguity", "reuse"])
def test_verified_exception_still_obeys_all_other_matching_gates(reviewed, gate):
    root, config, locations, records, sites = reviewed
    exceptions = load_address_exceptions(locations, records, sites, root=root, config=config)
    if gate == "operator":
        sites.loc[0, "ocm_operator"] = "Other operator"
    elif gate == "postcode":
        sites.loc[0, "postcode"] = "2000"
    elif gate == "source_conflict":
        locations.loc[0, "address_conflict"] = True
    elif gate == "distance":
        longitude, latitude, _ = GEOD.fwd(locations.iloc[0].longitude, locations.iloc[0].latitude, 0, 260)
        sites.loc[0, ["longitude", "latitude"]] = [longitude, latitude]
    elif gate == "ambiguity":
        other = sites.copy()
        other.loc[0, "ocm_id"] += 1
        other.loc[0, "address"] = locations.iloc[0].address
        sites = pd.concat([sites, other], ignore_index=True)
    else:
        other = locations.copy()
        other.loc[0, "location_id"] = "other_location"
        other.loc[0, "address"] = sites.iloc[0].address
        locations = pd.concat([locations, other], ignore_index=True)
        records = pd.concat([records, pd.DataFrame([{"location_id": "other_location", "charger_type": "DC"}])], ignore_index=True)
    assert match_sites(locations, records, sites, address_exceptions=exceptions)[0].empty


@pytest.mark.parametrize("distance", [0, 20, 100, 180])
@pytest.mark.parametrize("external_address", ["999 Test Street", "1 Test Road"])
def test_explicit_conflicts_are_rejected_at_all_distances(distance, external_address):
    locations, records, sites = frames()
    longitude, latitude, _ = GEOD.fwd(locations.iloc[0].longitude, locations.iloc[0].latitude, 0, distance)
    sites.loc[0, ["address", "longitude", "latitude"]] = [external_address, longitude, latitude]
    matches, audit = match_sites(locations, records, sites)
    assert matches.empty
    assert not audit.address_exception_applied.any()


@pytest.fixture
def reviewed_database():
    config = json.loads((ROOT / "config/reviewed_match_exceptions.json").read_text(encoding="utf-8"))
    entry = config["exceptions"][0]
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE charger_record(record_id VARCHAR,location_id VARCHAR)")
    con.execute("CREATE TABLE location(location_id VARCHAR,address VARCHAR)")
    con.execute("CREATE TABLE external_site(ocm_id BIGINT,address VARCHAR)")
    con.execute("CREATE TABLE source_snapshot(source_file VARCHAR,sha256 VARCHAR)")
    con.execute("CREATE TABLE site_match(location_id VARCHAR,ocm_id BIGINT,address_exception_review_id VARCHAR,address_exception_source_file VARCHAR)")
    con.execute("INSERT INTO charger_record VALUES (?,?)", [entry["record_id"], "reviewed"])
    con.execute("INSERT INTO location VALUES (?,?)", ["reviewed", entry["expected_source"]["address"]])
    con.execute("INSERT INTO external_site VALUES (?,?)", [entry["ocm_id"], entry["expected_external"]["address"]])
    con.execute("INSERT INTO source_snapshot VALUES (?,?)", [entry["evidence"]["file"], entry["evidence"]["sha256"]])
    con.execute("INSERT INTO source_snapshot VALUES (?,?)", ["data/raw/ev_20251216.csv", entry["source_snapshot"]["sha256"]])
    con.execute("INSERT INTO site_match VALUES (?,?,?,?)", ["reviewed", entry["ocm_id"], entry["review_id"], entry["evidence"]["file"]])
    yield con, config
    con.close()


def test_database_conflict_review_matches_the_approved_record_and_evidence(reviewed_database):
    con, config = reviewed_database
    assert database_address_exceptions_valid(con, config=config)


@pytest.mark.parametrize("mutation", [
    "UPDATE site_match SET address_exception_review_id='unapproved-review'",
    "UPDATE site_match SET address_exception_source_file='data/raw/ev_20251216.csv'",
    "UPDATE site_match SET address_exception_review_id=NULL,address_exception_source_file=NULL",
    "UPDATE source_snapshot SET sha256=repeat('0',64)",
    "UPDATE charger_record SET location_id='another-location'",
    "UPDATE location SET address='99 Orient St, Batemans Bay, 2536'",
    "UPDATE external_site SET address='101 Orient Street'",
    "UPDATE external_site SET ocm_id=999; UPDATE site_match SET ocm_id=999",
])
def test_database_validation_detects_review_corruption_and_cleared_review_columns(reviewed_database, mutation):
    con, config = reviewed_database
    con.execute(mutation)
    assert not database_address_exceptions_valid(con, config=config)


def test_database_validation_requires_the_reviewed_conflict_type(reviewed_database):
    con, config = reviewed_database
    config["exceptions"][0]["allowed_conflict"] = "street_type_conflict"
    assert not database_address_exceptions_valid(con, config=config)


def test_database_ordinary_match_needs_no_address_exception(reviewed_database):
    con, config = reviewed_database
    con.execute("UPDATE external_site SET address='53A Orient Street'")
    con.execute("UPDATE site_match SET address_exception_review_id=NULL,address_exception_source_file=NULL")
    assert database_address_exceptions_valid(con, config=config)
