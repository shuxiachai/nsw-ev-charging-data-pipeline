"""Reported per-site network/EVSE observations must not become live claims."""
import json
from hashlib import sha256

import pandas as pd
import pytest

from ev_pipeline import jolt
from ev_pipeline.acquire import ROOT
from tests.test_matching import frames


@pytest.mark.parametrize("field,value,expected", [
    ("networkStatus", "available", "available"),
    ("networkStatus", " long-term unavailable ", "long-term unavailable"),
    ("networkStatus", "temporarily unavailable", "temporarily unavailable"),
    ("evseStatus", "AVAILABLE", "available"),
    ("evseStatus", "occupied", "occupied"),
    ("evseStatus", "out of order", "out of order"),
    ("evseStatus", "unavailable", "unavailable"),
])
def test_reported_states_have_explicit_source_specific_meaning(field, value, expected):
    assert jolt.snapshot_status(value, field) == expected


@pytest.mark.parametrize("value", [None, "", " ", "unknown", "UNKNOWN", "n/a"])
@pytest.mark.parametrize("field", ["networkStatus", "evseStatus"])
def test_missing_or_unknown_state_never_invents_availability(field, value):
    assert jolt.snapshot_status(value, field) is None


@pytest.mark.parametrize("field,value", [
    ("networkStatus", "active"), ("evseStatus", "active"),
    ("networkStatus", "occupied"), ("evseStatus", "long-term unavailable"),
    ("networkStatus", "new-status"), ("evseStatus", "reserved"),
    ("networkStatus", True), ("evseStatus", 1),
    ("evseStatus", ["available"]), ("networkStatus", {"value": "available"}),
])
def test_cms_values_unreviewed_states_and_nontext_input_fail(field, value):
    with pytest.raises(ValueError, match="JOLT"):
        jolt.snapshot_status(value, field)


def fixture_map(tmp_path, monkeypatch, **values):
    point = dict(id=1, name="TEST001", address="1 Test St, NSW 2000", lat=-33.86001, lng=151.20001, **values)
    other = dict(id=2, name="FAR002", address="2 Other St, NSW 2000", lat=-32.0, lng=150.0,
                 status="active", networkStatus="available", evseStatus="occupied")
    page = 'var jolt = ' + json.dumps({"charging_points": {"first": point, "second": other}}) + ';'
    (tmp_path / "jolt_map.html").write_text(page, encoding="utf-8")
    monkeypatch.setattr(jolt, "RAW", tmp_path)
    locations, records, _ = frames()
    locations.loc[0, "operator_name"] = "JOLT"
    return jolt.jolt_augment(locations, records)


def test_cms_active_alone_remains_station_code_only(tmp_path, monkeypatch):
    sites, matches, _, attrs = fixture_map(tmp_path, monkeypatch, status="active")
    assert len(matches) == 1
    assert sites.loc[sites.jolt_id.eq(1), ["network_status_snapshot", "evse_status_snapshot"]].isna().all().all()
    assert attrs.attribute.tolist() == ["operator_station_code"]


def test_network_and_evse_disagreement_is_retained_separately_and_only_for_accepted_id(tmp_path, monkeypatch):
    sites, matches, _, attrs = fixture_map(tmp_path, monkeypatch, status="active",
                                         networkStatus="available", evseStatus="out of order")
    assert len(sites) == 2 and len(matches) == 1
    assert set(attrs.jolt_id) == {1}
    actual = attrs.set_index("attribute").value.to_dict()
    assert actual == {"operator_station_code": "TEST001", "operator_network_status_snapshot": "available",
                      "operator_evse_status_snapshot": "out of order"}
    assert set(attrs.source_file) == {"data/raw/jolt_map.html"}
    assert set(attrs.method) == {"coordinate_operator_address_match"}
    assert set(attrs.scope) == {"site"}
    assert not any("live" in key for key in actual)


def test_one_missing_state_does_not_remove_a_distinct_reported_state(tmp_path, monkeypatch):
    _, _, _, attrs = fixture_map(tmp_path, monkeypatch, status="out of order",
                                networkStatus="unknown", evseStatus="available")
    assert attrs.set_index("attribute").value.to_dict() == {
        "operator_station_code": "TEST001", "operator_evse_status_snapshot": "available"}


def test_actual_pinned_map_states_are_extracted_by_id_without_changing_matching_or_inputs():
    raw = ROOT / "data/raw/jolt_map.html"
    before = sha256(raw.read_bytes()).hexdigest()
    metadata = json.loads(raw.with_name(raw.name + ".meta.json").read_text(encoding="utf-8"))
    assert before == metadata["sha256"]
    assert metadata["retrieved_at_utc"] == "2026-09-06T05:00:00.972541+00:00"
    points = {int(p["id"]): p for p in jolt.parse_map(raw.read_text(encoding="utf-8"))}
    locations = pd.read_csv(ROOT / "data/processed/locations.csv", dtype={"postcode": str, "address_postcode": str})
    records = pd.read_csv(ROOT / "data/processed/cleaned_records.csv", dtype={"postcode": str, "address_postcode": str})
    sites, matches, _, attrs = jolt.jolt_augment(locations, records)
    assert len(sites) == len(points) == 173
    prior = pd.read_csv(ROOT / "data/processed/jolt_site_matches.csv")
    assert set(zip(matches.location_id, matches.jolt_id)) == set(zip(prior.location_id, prior.jolt_id))
    for site in sites.itertuples():
        point = points[site.jolt_id]
        assert site.network_status_snapshot == point["networkStatus"]
        assert site.evse_status_snapshot == point["evseStatus"]
    for attribute, raw_field in [("operator_network_status_snapshot", "networkStatus"),
                                  ("operator_evse_status_snapshot", "evseStatus")]:
        selected = attrs.loc[attrs.attribute.eq(attribute)]
        assert len(selected) == len(matches)
        for row in selected.itertuples():
            assert row.value == points[row.jolt_id][raw_field]
            assert row.source_file == "data/raw/jolt_map.html"
    assert sha256(raw.read_bytes()).hexdigest() == before
