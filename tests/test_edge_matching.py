"""Regressions for street-token ambiguity and empty/conflicting map sources."""
import json

import pytest

from ev_pipeline import jolt, osm
from ev_pipeline.augment import GEOD, address_similarity, extended_address_conflict, match_sites, street_component
from tests.test_matching import frames


@pytest.mark.parametrize("left,right", [
    ("10 St Johns Road", "100 St Johns Road"),
    ("10 St. Johns Road", "100 Saint Johns Rd"),
    ("Unit 1/10 St Johns Road", "Unit 2/100 St Johns Rd"),
    ("10 Avenue Road", "100 Avenue Rd"),
    ("10 Parade Road", "100 Parade Rd"),
])
def test_street_name_tokens_cannot_hide_disjoint_house_numbers(left, right):
    loc, records, sites = frames()
    loc.loc[0, "address"] = left
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, 180)
    sites.loc[0, ["address", "longitude", "latitude"]] = [right, longitude, latitude]
    assert extended_address_conflict(left, right) == "house_number_conflict"
    matches, audit = match_sites(loc, records, sites)
    assert matches.empty
    assert audit.iloc[0].decision == "rejected_evidence"


def test_saint_st_does_not_discard_the_street_name():
    loc, records, sites = frames()
    loc.loc[0, "address"] = "1 St Vincent De Paul Road"
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, 180)
    sites.loc[0, ["address", "longitude", "latitude"]] = ["1 St Mary Road", longitude, latitude]
    assert street_component(loc.loc[0, "address"]) == "1 st vincent de paul rd"
    assert address_similarity(loc.loc[0, "address"], sites.loc[0, "address"]) < 0.65
    assert match_sites(loc, records, sites)[0].empty
    # Ordinary Saint addresses still match when both sources identify the street.
    sites.loc[0, "address"] = "1 St Vincent De Paul Rd"
    assert len(match_sites(loc, records, sites)[0]) == 1


@pytest.mark.parametrize("long,short", [("Parade", "Pde"), ("Crescent", "Cres"), ("Place", "Pl"), ("Court", "Ct")])
def test_recognized_street_type_aliases_have_identical_text_evidence(long, short):
    assert address_similarity(f"10 Anzac {long}", f"10 Anzac {short}") == 1


def test_complete_empty_osm_response_preserves_all_output_schemas(tmp_path, monkeypatch):
    monkeypatch.setattr(osm, "RAW", tmp_path)
    (tmp_path / "osm_chargers.json").write_text(json.dumps({"elements": []}), encoding="utf-8")
    locations, records, _ = frames()
    sites, matches, audit, attrs = osm.osm_augment(locations, records)
    assert all(frame.empty for frame in (sites, matches, audit, attrs))
    assert {"osm_id", "latitude", "longitude", "tags_json"} <= set(sites.columns)
    assert {"osm_id", "location_id", "decision", "distance_m"} <= set(matches.columns)
    assert set(matches.columns) == set(audit.columns)
    assert {"osm_id", "location_id", "attribute", "value"} <= set(attrs.columns)
    (tmp_path / "osm_chargers.json").write_text(json.dumps({"elements": [], "remark": "timed out"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Partial Overpass"):
        osm.osm_augment(locations, records)


def jolt_frames(tmp_path, monkeypatch, addresses, *, same_id=False, code="TEST001"):
    points = {str(i): dict(id=1 if same_id else i + 1, name=code, address=address,
                           lat=-33.86001, lng=151.20001) for i, address in enumerate(addresses)}
    page = "var jolt = " + json.dumps({"charging_points": points}) + ";"
    (tmp_path / "jolt_map.html").write_text(page, encoding="utf-8")
    monkeypatch.setattr(jolt, "RAW", tmp_path)
    locations, records, _ = frames()
    locations.loc[0, "operator_name"] = "JOLT"
    return locations, records


def test_jolt_missing_postcode_does_not_use_four_digit_house_number(tmp_path, monkeypatch):
    locations, records = jolt_frames(tmp_path, monkeypatch, ["1250 George St, Sydney"])
    _, matches, audit, attrs = jolt.jolt_augment(locations, records)
    assert len(matches) == 1
    assert not audit.postcode_conflict.any()
    assert attrs.iloc[0].value == "TEST001"


@pytest.mark.parametrize("address", [
    "904 Gardeners Rd, Mascot NSW 2020\r\nCarpark open 8:30-19:00",
    "904 Gardeners Rd, Mascot NSW 2020, Australia\r\nTemporarily compatible with front charging ONLY",
    "1 Main St, Melbourne VIC 3000, Australia",
])
def test_jolt_postal_suffix_still_blocks_conflicting_postcode(tmp_path, monkeypatch, address):
    locations, records = jolt_frames(tmp_path, monkeypatch, [address])
    _, matches, audit, _ = jolt.jolt_augment(locations, records)
    assert matches.empty
    assert audit.postcode_conflict.all()


def test_jolt_conflicting_duplicate_ids_fail_instead_of_picking_first(tmp_path, monkeypatch):
    locations, records = jolt_frames(tmp_path, monkeypatch, ["1 Test St, NSW 2000", "100 Test St, NSW 2000"], same_id=True)
    with pytest.raises(ValueError, match="Conflicting JOLT entries for station ID 1"):
        jolt.jolt_augment(locations, records)


def test_jolt_identical_duplicate_ids_are_harmless(tmp_path, monkeypatch):
    locations, records = jolt_frames(tmp_path, monkeypatch, ["1 Test St, NSW 2000"] * 2, same_id=True)
    sites, matches, _, attrs = jolt.jolt_augment(locations, records)
    assert len(sites) == len(matches) == len(attrs) == 1


def test_jolt_integer_and_numeric_string_ids_share_one_identity(tmp_path, monkeypatch):
    locations, records = jolt_frames(tmp_path, monkeypatch, ["1 Test St, NSW 2000"])
    point = dict(id=1, name="TEST001", address="1 Test St, NSW 2000", lat=-33.86001, lng=151.20001)
    page = "var jolt = " + json.dumps({"charging_points": {"a": point, "b": dict(point, id="1")}}) + ";"
    (tmp_path / "jolt_map.html").write_text(page, encoding="utf-8")
    sites, matches, _, attrs = jolt.jolt_augment(locations, records)
    assert len(sites) == len(matches) == len(attrs) == 1
    assert sites.iloc[0].jolt_id == 1


def test_jolt_empty_map_or_station_code_cannot_claim_enrichment(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="charging_points missing/empty"):
        jolt.parse_map('var jolt = {"charging_points": {}};')
    locations, records = jolt_frames(tmp_path, monkeypatch, ["1 Test St, NSW 2000"], code=" ")
    with pytest.raises(ValueError, match="station code missing"):
        jolt.jolt_augment(locations, records)
