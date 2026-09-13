# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""OSM full and split addresses must not conceal each other's contradictions."""
import json

import pandas as pd
import pytest

from ev_pipeline import osm
from ev_pipeline.augment import GEOD
from tests.test_matching import frames


def run_osm(tmp_path, monkeypatch, address_tags, *, distance=20, source_address=None,
            source_postcode="2000"):
    locations, records, _ = frames()
    if source_address is not None:
        locations.loc[0, "address"] = source_address
    locations.loc[0, ["postcode", "address_postcode"]] = source_postcode
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, distance)
    nodes = [dict(type="node", id=i, lat=latitude, lon=longitude,
                  tags={"operator": "Evie", "socket:type2_combo": "1", "fee": "no", **tags})
             for i, tags in enumerate(address_tags, 1)]
    monkeypatch.setattr(osm, "RAW", tmp_path)
    (tmp_path / "osm_chargers.json").write_text(json.dumps({"elements": nodes}), encoding="utf-8")
    return osm.osm_augment(locations, records), nodes


@pytest.mark.parametrize("tags,reason,postcode_conflict", [
    ({"addr:full": "999 Test Street, Sydney NSW 2000"}, "house_number_conflict", False),
    ({"addr:full": "1 Test Road, Sydney NSW 2000"}, "street_type_conflict", False),
    ({"addr:full": "1 Test Street, Sydney NSW 2001"}, "", True),
    ({"addr:full": "1 Test Street, Sydney, 2001, Australia"}, "", True),
    ({"addr:full": "1 Test Street, Sydney 2001 NSW"}, "", True),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "999 Test Street, Sydney NSW 2000"}, "house_number_conflict", False),
    ({"addr:housenumber": "999", "addr:street": "Test Street",
      "addr:full": "1 Test Street, Sydney NSW 2000"}, "house_number_conflict", False),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "1 Test Road, Sydney NSW 2000"}, "street_type_conflict", False),
    ({"addr:housenumber": "1", "addr:street": "Test Road",
      "addr:full": "1 Test Street, Sydney NSW 2000"}, "street_type_conflict", False),
    ({"addr:housenumber": "1", "addr:street": "Test Street", "addr:postcode": "2000",
      "addr:full": "1 Test Street, Sydney NSW 2001"}, "", True),
    ({"addr:housenumber": "1", "addr:street": "Test Street", "addr:postcode": "2001",
      "addr:full": "1 Test Street, Sydney NSW 2000"}, "", True),
    ({"addr:housenumber": "1", "addr:street": "Test Street, Sydney NSW 2001",
      "addr:full": "1 Test Street, Sydney NSW 2000"}, "", True),
])
def test_explicit_conflicts_in_any_osm_address_field_block_enrichment(
        tmp_path, monkeypatch, tags, reason, postcode_conflict):
    (sites, matches, audit, attrs), nodes = run_osm(tmp_path, monkeypatch, [tags])
    assert matches.empty and attrs.empty
    assert audit.iloc[0].decision == "rejected_evidence"
    assert audit.iloc[0].extended_address_conflict == reason
    assert bool(audit.iloc[0].postcode_conflict) is postcode_conflict
    # Rejection does not erase either of the original address observations.
    assert json.loads(sites.iloc[0].tags_json) == nodes[0]["tags"]


@pytest.mark.parametrize("tags,distance", [
    ({"addr:full": "1 Test Street, Sydney NSW 2000"}, 20),
    ({"addr:full": "1 Test Street, Sydney NSW 2000"}, 180),
    ({"addr:housenumber": " ", "addr:street": "\t",
      "addr:full": "1 Test Street, Sydney NSW 2000"}, 180),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "1 Test St, Sydney NSW 2000", "addr:postcode": "2000"}, 180),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "1-3 Test St, Sydney NSW 2000"}, 20),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "Test Street, Sydney NSW 2000"}, 20),
    ({"addr:housenumber": "1", "addr:street": "Test Street"}, 20),
    ({"addr:full": "Shopping Centre"}, 20),
    ({"addr:full": ""}, 20),
    ({}, 20),
])
def test_compatible_or_missing_osm_evidence_can_still_match(tmp_path, monkeypatch, tags, distance):
    (sites, matches, audit, attrs), nodes = run_osm(tmp_path, monkeypatch, [tags], distance=distance)
    assert matches.osm_id.tolist() == ["node/1"]
    assert set(attrs.attribute) == {"dc_connector_types", "fee"}
    assert not audit.postcode_conflict.any()
    assert audit.iloc[0].extended_address_conflict == ""
    assert json.loads(sites.iloc[0].tags_json) == nodes[0]["tags"]
    if "addr:street" not in tags:
        assert sites.iloc[0].address == tags.get("addr:full", "")


@pytest.mark.parametrize("tags,reason,postcode_conflict", [
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "999 Test Street, Sydney NSW 2000"}, "house_number_conflict", False),
    ({"addr:housenumber": "1", "addr:street": "Test Street",
      "addr:full": "1 Test Road, Sydney NSW 2000"}, "street_type_conflict", False),
    ({"addr:full": "1 Test Street, Sydney NSW 2000", "addr:postcode": "2001"}, "", True),
])
def test_internally_conflicting_osm_fields_remain_rejected_when_source_evidence_is_unknown(
        tmp_path, monkeypatch, tags, reason, postcode_conflict):
    (_, matches, audit, attrs), _ = run_osm(tmp_path, monkeypatch, [tags],
                                          source_address="Shopping Centre", source_postcode=None)
    assert matches.empty and attrs.empty
    assert audit.iloc[0].extended_address_conflict == reason
    assert bool(audit.iloc[0].postcode_conflict) is postcode_conflict


def test_four_digit_house_number_in_full_address_is_not_a_postcode(tmp_path, monkeypatch):
    tags = {"addr:full": "1250 George Street, Sydney"}
    (_, matches, audit, _), _ = run_osm(tmp_path, monkeypatch, [tags], source_address="1250 George St")
    assert len(matches) == 1
    assert not audit.postcode_conflict.any()


def test_rejection_precedes_ranking_so_valid_competitor_can_be_selected(tmp_path, monkeypatch):
    tags = [{"addr:housenumber": "1", "addr:street": "Test Street",
             "addr:full": "999 Test Street, Sydney NSW 2000"},
            {"addr:housenumber": "1", "addr:street": "Test Street",
             "addr:full": "1 Test Street, Sydney NSW 2000"}]
    (_, matches, audit, attrs), _ = run_osm(tmp_path, monkeypatch, tags)
    assert matches.osm_id.tolist() == ["node/2"]
    assert audit.set_index("osm_id").decision.to_dict() == {
        "node/1": "rejected_evidence", "node/2": "accepted"}
    assert set(attrs.osm_id) == {"node/2"}


def test_compatible_full_address_does_not_reweight_existing_split_address_score(tmp_path, monkeypatch):
    tags = {"addr:housenumber": "1", "addr:street": "Test Street"}
    (before_sites, _, before_audit, _), _ = run_osm(tmp_path, monkeypatch, [tags], distance=180)
    (after_sites, _, after_audit, _), _ = run_osm(tmp_path, monkeypatch,
        [{**tags, "addr:full": "1 Test Street, Sydney NSW 2000"}], distance=180)
    assert before_sites.iloc[0].address == after_sites.iloc[0].address == "1 Test Street"
    pd.testing.assert_frame_equal(before_audit, after_audit)


def test_missing_addresses_still_fail_at_extended_distance(tmp_path, monkeypatch):
    (_, matches, audit, _), _ = run_osm(tmp_path, monkeypatch, [{}], distance=180)
    assert matches.empty
    assert audit.iloc[0].address_similarity == 0
    assert audit.iloc[0].extended_address_conflict == ""
