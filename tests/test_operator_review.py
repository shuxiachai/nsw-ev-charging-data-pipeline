"""Reviewed identity uncertainty cannot become a confirmed operator assignment."""
from copy import deepcopy
import json

import duckdb
import pandas as pd
import pytest

from ev_pipeline import augment
from ev_pipeline.acquire import ROOT
from ev_pipeline.augmentation_semantics import operator_website_hosts
from ev_pipeline.operator_review import (ISSUE_CODE, database_operator_reviews_valid,
                                         load_operator_reviews, usable_operator_details)


@pytest.fixture
def review_inputs():
    with duckdb.connect(str(ROOT / "data/processed/ev_chargers.duckdb"), read_only=True) as con:
        locations = con.execute("SELECT l.location_id,l.address,o.operator_id,o.operator_name FROM location l JOIN operator o USING(operator_id)").df()
        records = con.execute("SELECT record_id,source_row,location_id,raw_json,charger_type FROM charger_record").df()
    reference = json.loads((ROOT / "data/raw/ocm_reference.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "config/reviewed_operator_assignments.json").read_text(encoding="utf-8"))
    return locations, records, reference, config


def operator_observations(locations, details, reviews):
    return {(loc.location_id, int(row.ocm_operator_id), row.attribute, row.value)
            for loc in locations.itertuples()
            for row in details.loc[details.operator_name.eq(loc.operator_name)].itertuples()
            if (loc.location_id, int(row.ocm_operator_id), row.attribute, row.value) not in reviews}


def test_actual_review_withholds_only_one_ac_assignment_and_preserves_dc(review_inputs):
    locations, records, reference, config = review_inputs
    originals = records.raw_json.copy()
    reviews = load_operator_reviews(locations, records, reference, config=config)
    assert len(reviews) == 1
    key, warning = next(iter(reviews.items()))
    assert records.loc[records.location_id.eq(key[0]), "charger_type"].tolist() == ["AC"]
    assert warning["source_row"] == 1620 and warning["code"] == ISSUE_CODE
    evidence = json.loads(warning["detail"])
    assert evidence["candidate_value"] == "https://www.countiesenergy.co.nz/articles/ev-charging"
    assert evidence["source_snapshot"]["sha256"] == config["source_snapshot"]["sha256"]
    assert evidence["external_snapshot"]["sha256"] == config["external_snapshot"]["sha256"]
    candidates = augment.operator_details(locations, reference)
    usable = usable_operator_details(locations, candidates, reviews)
    before = operator_observations(locations, candidates, {})
    after = operator_observations(locations, usable, reviews)
    assert before - after == {key} and not after - before
    dc_ids = set(records.loc[records.charger_type.eq("DC"), "location_id"])
    assert {row for row in before if row[0] in dc_ids} == {row for row in after if row[0] in dc_ids}
    assert "Counties Energy" not in operator_website_hosts(usable)
    assert records.raw_json.equals(originals)


def test_review_does_not_globally_block_a_second_same_name_location(review_inputs):
    locations, records, reference, config = review_inputs
    other = locations.loc[locations.operator_name.eq("Counties Energy")].iloc[[0]].copy()
    other["location_id"] = "another_counties_location"
    other["address"] = "Another site"
    locations = pd.concat([locations, other], ignore_index=True)
    reviews = load_operator_reviews(locations, records, reference, config=config)
    usable = usable_operator_details(locations, augment.operator_details(locations, reference), reviews)
    observations = operator_observations(locations, usable, reviews)
    assert any(row[0] == "another_counties_location" and row[1] == 3547 for row in observations)
    assert not any(row in observations for row in reviews)


@pytest.mark.parametrize("change", ["source_row", "raw_operator", "raw_type", "location", "external_id", "external_title", "value", "attribute", "duplicate", "missing_record", "source_hash"])
def test_changed_review_evidence_fails_explicitly(review_inputs, change):
    locations, records, reference, config = review_inputs
    config = deepcopy(config)
    entry = config["reviews"][0]
    target = records.record_id.eq(entry["record_id"])
    if change == "source_row":
        entry["source_row"] += 1
    elif change in {"raw_operator", "raw_type"}:
        raw = json.loads(records.loc[target, "raw_json"].iloc[0])
        raw["Operator" if change == "raw_operator" else "Charger_Type"] = "changed"
        records.loc[target, "raw_json"] = json.dumps(raw)
    elif change == "location":
        locations.loc[locations.location_id.eq(records.loc[target, "location_id"].iloc[0]), "operator_name"] = "Different operator"
    elif change == "external_id":
        entry["ocm_operator_id"] = 3339
    elif change == "external_title":
        reference["Operators"] = [dict(op, Title="Different operator") if op["ID"] == 3547 else op for op in reference["Operators"]]
    elif change == "value":
        entry["value"] = "https://example.org/other"
    elif change == "attribute":
        entry["attribute"] = "dc_connector_types"
    elif change == "duplicate":
        config["reviews"].append(deepcopy(entry))
    elif change == "missing_record":
        records = records.loc[~target]
    else:
        config["source_snapshot"]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        load_operator_reviews(locations, records, reference, config=config)


def test_augmentation_exports_warning_and_not_the_withheld_value(review_inputs, monkeypatch):
    locations, records, reference, _ = review_inputs
    monkeypatch.setattr(augment, "external_data", lambda: (pd.DataFrame(columns=["ocm_id"]), pd.DataFrame(), reference))
    monkeypatch.setattr(augment, "load_address_exceptions", lambda *args: {})
    monkeypatch.setattr(augment, "match_sites", lambda *args, **kwargs: (pd.DataFrame(), pd.DataFrame()))
    issues = []
    _, _, _, _, details, observations = augment.augment(locations, records, issues=issues)
    assert len(issues) == 1 and issues[0]["code"] == ISSUE_CODE
    assert not details.ocm_operator_id.eq(3547).any()
    assert not observations.ocm_operator_id.eq(3547).any()
    assert observations.ocm_operator_id.eq(3339).any()


@pytest.mark.parametrize("mutation", [None, "missing_audit", "changed_audit", "reintroduced_value", "changed_value"])
def test_database_check_detects_erased_audit_or_reintroduced_assignment(review_inputs, mutation):
    locations, records, reference, config = review_inputs
    reviews = load_operator_reviews(locations, records, reference, config=config)
    warnings = pd.DataFrame(reviews.values())
    operators = locations[["operator_id", "operator_name"]].drop_duplicates()
    with duckdb.connect(":memory:") as con:
        con.register("input_locations", locations)
        con.register("input_records", records)
        con.register("input_operators", operators)
        con.register("input_warnings", warnings)
        con.execute("CREATE TABLE location AS SELECT location_id,operator_id,address FROM input_locations")
        con.execute("CREATE TABLE charger_record AS SELECT * FROM input_records")
        con.execute("CREATE TABLE operator AS SELECT * FROM input_operators")
        con.execute("CREATE TABLE quality_issue AS SELECT * FROM input_warnings")
        con.execute("CREATE TABLE augmentation(location_id VARCHAR,ocm_operator_id BIGINT,attribute VARCHAR,value VARCHAR)")
        if mutation == "missing_audit":
            con.execute("DELETE FROM quality_issue")
        elif mutation == "changed_audit":
            con.execute("UPDATE quality_issue SET detail='unverified text'")
        elif mutation in {"reintroduced_value", "changed_value"}:
            key = list(next(iter(reviews)))
            if mutation == "changed_value":
                key[3] = "https://example.org/changed"
            con.execute("INSERT INTO augmentation VALUES (?,?,?,?)", key)
        assert database_operator_reviews_valid(con, config=config) is (mutation is None)
