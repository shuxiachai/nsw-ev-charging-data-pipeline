# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

import pandas as pd
import pytest
from ev_pipeline.augment import (
    GEOD, acceptable_candidate, address_similarity, extended_address_conflict, match_sites,
)
from ev_pipeline.jolt import parse_map
from ev_pipeline.osm import positive_socket


@pytest.mark.parametrize("args,expected", [
    ((20, True, 0, False, False), True),
    ((20, False, 1, False, False), False),
    ((20, True, 1, True, False), False),
    ((20, True, 1, False, True), False),
    ((200, True, 0.9, False, False), True),
    ((200, True, 0.1, False, False), False),
    ((251, True, 1, False, False), False),
    ((-1, True, 1, False, False), False),
])
def test_evidence_gates(args, expected):
    assert acceptable_candidate(*args) is expected


def frames():
    loc = pd.DataFrame([dict(location_id="l1", latitude=-33.86, longitude=151.20,
                             operator_name="Evie", address="1 Test St, Sydney, 2000", postcode="2000",
                             address_postcode="2000", address_conflict=False)])
    records = pd.DataFrame([dict(location_id="l1", charger_type="DC")])
    sites = pd.DataFrame([dict(ocm_id=1, latitude=-33.86001, longitude=151.20001,
                               ocm_operator="Evie", address="1 Test Street", postcode="2000", has_dc=True)])
    return loc, records, sites


def test_unique_match_and_ac_exclusion():
    loc, records, sites = frames()
    assert len(match_sites(loc, records, sites)[0]) == 1
    sites["has_dc"] = False
    assert match_sites(loc, records, sites)[0].empty


def test_competing_external_sites_are_not_cherry_picked():
    loc, records, sites = frames()
    second = sites.copy()
    second["ocm_id"] = 2
    matches, audit = match_sites(loc, records, pd.concat([sites, second], ignore_index=True))
    assert matches.empty
    assert set(audit.decision) == {"ambiguous_candidates"}


def test_one_external_site_cannot_enrich_two_locations():
    loc, records, sites = frames()
    second = loc.copy()
    second["location_id"] = "l2"
    records = pd.concat([records, pd.DataFrame([dict(location_id="l2", charger_type="DC")])], ignore_index=True)
    matches, audit = match_sites(pd.concat([loc, second], ignore_index=True), records, sites)
    assert matches.empty
    assert set(audit.decision) == {"external_poi_reused_review"}


def test_operator_conflict_rejected_even_at_same_coordinates():
    loc, records, sites = frames()
    sites["ocm_operator"] = "Tesla"
    assert match_sites(loc, records, sites)[0].empty


@pytest.mark.parametrize("missing", [None, pd.NA, ""])
def test_two_missing_operators_do_not_establish_identity(missing):
    loc, records, sites = frames()
    loc["operator_name"] = missing
    sites["ocm_operator"] = missing
    matches, audit = match_sites(loc, records, sites)
    assert matches.empty
    assert not audit.same_operator.any()


@pytest.mark.parametrize("left,right,reason", [
    ("46 Wynter St, Taree 2430", "37 Wynter Street", "house_number_conflict"),
    ("42 Camden Rd", "38 Camden Road", "house_number_conflict"),
    ("1 Test St", "999 Test St", "house_number_conflict"),
    ("17 Stanley St", "17-25 Stanley Street", ""),
    ("17-25 Stanley St", "25-27 Stanley Street", ""),
    ("17-25 Stanley St", "26-27 Stanley Street", "house_number_conflict"),
    ("1/10 High St", "2/10 High Street", ""),
    ("Unit 1/10 High St", "Unit 2/10 High Street", ""),
    ("15c Mitchell St", "15 Mitchell Street", ""),
    ("1 Park Rd", "1 Park St", "street_type_conflict"),
    ("10 Winery Dr", "764 Pacific Highway", ""),
    ("17 Stanley St", "Stanley Street", ""),
    ("Lot 17 Stanley St", "Lot 25 Stanley Street", ""),
    ("Corner High St & Main Rd", "99 High St", ""),
    ("Shopping Centre", "17 Stanley St", ""),
    (None, "17 Stanley St", ""),
])
def test_only_explicit_simple_street_evidence_establishes_conflict(left, right, reason):
    assert extended_address_conflict(left, right) == reason
    assert extended_address_conflict(right, left) == reason


def test_high_fuzzy_score_cannot_override_disjoint_house_numbers_at_extended_distance():
    loc, records, sites = frames()
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, 180)
    sites.loc[0, ["latitude", "longitude", "address"]] = [latitude, longitude, "999 Test Street"]
    # This is the failure mode: the original text score independently passes.
    assert address_similarity(loc.loc[0, "address"], sites.loc[0, "address"]) >= 0.65
    matches, audit = match_sites(loc, records, sites)
    assert matches.empty
    assert audit.iloc[0].extended_address_conflict == "house_number_conflict"
    assert audit.iloc[0].decision == "rejected_evidence"


def test_extended_distance_accepts_overlapping_house_number_range():
    loc, records, sites = frames()
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, 180)
    loc.loc[0, "address"] = "17 Stanley St, Sydney, 2000"
    sites.loc[0, ["latitude", "longitude", "address"]] = [latitude, longitude, "17-25 Stanley Street"]
    assert len(match_sites(loc, records, sites)[0]) == 1


def test_nearby_explicit_number_conflict_requires_reviewed_evidence():
    loc, records, sites = frames()
    sites.loc[0, "address"] = "999 Test Street"
    matches, audit = match_sites(loc, records, sites)
    assert matches.empty
    assert audit.iloc[0].extended_address_conflict == "house_number_conflict"


@pytest.mark.parametrize("distance,accepted", [(20, True), (180, False)])
def test_missing_external_address_has_only_the_nearby_matching_route(distance, accepted):
    loc, records, sites = frames()
    longitude, latitude, _ = GEOD.fwd(151.20, -33.86, 0, distance)
    sites.loc[0, ["latitude", "longitude", "address"]] = [latitude, longitude, None]
    matches, audit = match_sites(loc, records, sites)
    assert (len(matches) == 1) is accepted
    assert audit.iloc[0].address_similarity == 0


def test_jolt_json_parsing_does_not_execute_javascript():
    page = '<script>var jolt = {"charging_points":{"a":{"id":1,"name":"TEST;001"}}}; alert("ignore");</script>'
    assert parse_map(page) == [{"id": 1, "name": "TEST;001"}]
    with pytest.raises(ValueError, match="missing"):
        parse_map("<html>Changed page</html>")


@pytest.mark.parametrize("value,result", [
    ("2", True), ("yes", True), ("0", False), ("no", False), (None, False),
    ("0;2", True), ("1;2", True), ("bad;2", True), ("2;bad", True),
    ("yes;0", True), ("0;yes", True), ("inf", False), ("-inf", False),
    ("NaN", False), ("-1", False), ("bad;0", False),
])
def test_socket_presence_is_not_inferred_from_zero(value, result):
    assert positive_socket(value) is result
