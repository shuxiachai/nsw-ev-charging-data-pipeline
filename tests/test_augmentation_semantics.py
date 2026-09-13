# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Regressions for observation meaning, provenance and cross-field review."""
from datetime import timezone
import csv
import hashlib
import json

import pandas as pd
import pytest

from ev_pipeline import augment, osm
from ev_pipeline.augmentation_semantics import (
    attribute_differences, classify_url_attribute, connector_difference_category,
    connector_quality, operator_website_hosts, source_verified_at,
)
from tests.test_matching import frames


def attrs(*observations):
    return pd.DataFrame([dict(location_id="l1", scope="site", attribute=attribute, value=value,
                              source_file=source, ocm_id=1 if source.endswith(".json") else None,
                              osm_id="node/2" if source.endswith(".osm") else None)
                         for attribute, value, source in observations])


@pytest.mark.parametrize("cost", ["50c per kWh energy consumed.", "60c / 54c for members",
                                  "$0.60/kWh", "Free first 7 kWh then AUD 0.50/kWh"])
def test_no_fee_and_positive_price_are_reviewed_across_names_without_overwriting(cost):
    original = attrs(("fee", "no", "map.osm"), ("usage_cost_text", cost, "poi.json"))
    before = original.copy(deep=True)
    review = attribute_differences(original)
    assert review.category.tolist() == ["fee_semantic_review"]
    assert review.iloc[0].attribute == "fee_vs_usage_cost_text"
    observations = json.loads(review.iloc[0].observations_json)
    assert {(row["attribute"], row["value"], row["source_file"]) for row in observations} == {
        ("fee", "no", "map.osm"), ("usage_cost_text", cost, "poi.json")}
    assert {row["osm_id"] for row in observations} == {None, "node/2"}
    pd.testing.assert_frame_equal(original, before)


@pytest.mark.parametrize("cost", ["Free", "$0/kWh", "0c per kWh", "Free first 7 kWh",
                                  "Free parking 2 hours", "Prices in app", "24/7"])
def test_numbers_and_unknown_pricing_do_not_invent_a_positive_fee(cost):
    assert attribute_differences(attrs(("fee", "no", "map.osm"),
                                       ("usage_cost_text", cost, "poi.json"))).empty


@pytest.mark.parametrize("cost", ["FREE", "Free charging", "No charge.", "free of charge"])
def test_yes_fee_and_unconditional_free_statement_are_reviewed_symmetrically(cost):
    original = attrs(("fee", "yes", "map.osm"), ("usage_cost_text", cost, "poi.json"))
    review = attribute_differences(original)
    assert review.category.tolist() == ["fee_semantic_review"]
    assert "fee=yes" in review.iloc[0].note
    assert json.loads(review.iloc[0].values_json) == sorted(["yes", cost])


@pytest.mark.parametrize("cost", ["First 7kWh free then 50c/kWh", "Free for members",
    "Currently free but will be fee at some point for non NRMA Members",
    "Chargers free of charge for now but will require you to be a member in the future or you will need to pay per charge."])
def test_conditional_free_text_is_not_treated_as_unconditional_free(cost):
    assert attribute_differences(attrs(("fee", "yes", "map.osm"),
                                       ("usage_cost_text", cost, "poi.json"))).empty


def test_fee_review_needs_both_observations_at_the_same_site():
    original = attrs(("fee", "no", "map.osm"), ("usage_cost_text", "$0.60/kWh", "poi.json"))
    original.loc[1, "location_id"] = "l2"
    assert attribute_differences(original).empty
    original.loc[1, "location_id"] = "l1"
    original.loc[1, "scope"] = "operator"
    assert attribute_differences(original).empty


@pytest.mark.parametrize("values,category", [
    (["CCS (Type 2); CHAdeMO", "CCS (Type 1); CHAdeMO"], "connector_physical_type_conflict"),
    (["CCS (Type 2)", "CCS (Type 2); CHAdeMO"], "connector_set_inclusion"),
    (["CCS (Type 2)", "Tesla CCS; Tesla Supercharger"], "connector_tesla_naming_or_hardware_review"),
    (["CCS (Type 2)", "Tesla Supercharger"], "connector_tesla_naming_or_hardware_review"),
    (["CCS (Type 2); CHAdeMO", "CHAdeMO; CCS (Type 2)"], "connector_order_or_format"),
    (["CCS (Type 2); Tesla CCS", "CCS (Type 1); Tesla CCS"], "connector_physical_type_conflict"),
])
def test_connector_sets_are_classified_without_equating_tesla_and_ccs(values, category):
    assert connector_difference_category(values) == category
    review = attribute_differences(attrs(*[("dc_connector_types", value, source)
                                          for value, source in zip(values, ["poi.json", "map.osm"])]))
    assert review.category.tolist() == [category]
    assert json.loads(review.iloc[0].values_json) == sorted(values)


@pytest.mark.parametrize("value", [None, "2023-07-12T22:38:00Z", "2024-01-01T01:00:00+01:00"])
def test_verified_timestamp_preserves_source_instant_only(value):
    result = source_verified_at(value)
    if value is None:
        assert result is None
    else:
        assert result.tzinfo == timezone.utc
        assert result.isoformat().startswith("2023-07-12T22:38:00" if value.endswith("Z") else "2024-01-01T00:00:00")


@pytest.mark.parametrize("value", ["", "2024-01-01", "2024-01-01T00:00:00", "2024-02-30T00:00:00Z", True])
def test_verified_timestamp_does_not_assume_timezone_or_accept_invalid_dates(value):
    with pytest.raises(ValueError, match="DateLastVerified"):
        source_verified_at(value)


@pytest.mark.parametrize("url,expected", [
    ("https://www.goevie.com.au/", ("operator_website", "operator")),
    ("https://goevie.com.au/our-network/", ("operator_network_map_url", "operator")),
    ("https://goevie.com.au/our-network/site-1/", ("access_information_url", "site")),
    ("https://goevie.com.au/our-network/?station=1", ("access_information_url", "site")),
    ("https://unknown.example/", ("access_information_url", "site")),
    ("https://goevie.com.au.evil.example/", ("access_information_url", "site")),
    ("Enter from Manning Drive; see https://goevie.com.au/", ("access_comments", "site")),
])
def test_only_known_operator_landing_urls_are_generalized(url, expected):
    details = pd.DataFrame([dict(attribute="operator_website", operator_name="Evie", value="http://goevie.com.au/")])
    assert classify_url_attribute(url, "Evie", operator_website_hosts(details), original_attribute="access_comments") == expected


@pytest.mark.parametrize("url", [
    "https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network",
    "https://mynrma.com.au/cars-and-driving/electric-vehicles/charging-network/",
    "https://www.mynrma.com.au/electric-vehicles/charging",
    "https://mynrma.com.au/electric-vehicles/charging/",
])
@pytest.mark.parametrize("attribute", ["website", "access_comments"])
def test_nrma_archived_network_urls_are_operator_scope(url, attribute):
    details = pd.DataFrame([dict(attribute="operator_website", operator_name="NRMA",
                                value="https://www.mynrma.com.au/cars-and-driving/electric-vehicles")])
    assert classify_url_attribute(url, "NRMA", operator_website_hosts(details), original_attribute=attribute) == (
        "operator_network_map_url", "operator")


@pytest.mark.parametrize("url,op,hosts", [
    ("https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network/yass", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au/electric-vehicles/charging/yass", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au/electric-vehicles/charging-yass", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au/electric-vehicles/charging?station=yass", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au/cars-and-driving/electric-vehicles/charging-network#yass", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au.evil.example/electric-vehicles/charging", "NRMA", {"NRMA": {"mynrma.com.au"}}),
    ("https://www.mynrma.com.au/electric-vehicles/charging", "NRMA", {}),
    ("https://www.mynrma.com.au/electric-vehicles/charging", "Evie", {"Evie": {"mynrma.com.au"}}),
    ("https://goevie.com.au/electric-vehicles/charging", "Evie", {"Evie": {"goevie.com.au"}}),
])
def test_nrma_network_rule_does_not_swallow_station_pages_or_other_operators(url, op, hosts):
    assert classify_url_attribute(url, op, hosts, original_attribute="website") == ("website", "site")


def test_yass_network_reclassification_preserves_source_and_other_site_attributes(tmp_path, monkeypatch):
    raw = osm.RAW
    page = (raw / "nrma_network.html").read_bytes()
    manifest = json.loads((raw / "nrma_network.html.meta.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(page).hexdigest() == manifest["sha256"] and len(page) == manifest["bytes"]
    assert b"NRMA Electric Vehicle Fast Charger Network" in page
    assert b"Find a charger near you" in page
    elements = json.loads((raw / "osm_chargers.json").read_text(encoding="utf-8"))["elements"]
    node = next(e for e in elements if e["type"] == "node" and e["id"] == 7816558586)
    assert node["tags"]["website"] == manifest["url"]
    with (raw / "ev_20251216.csv").open(encoding="utf-8-sig", newline="") as stream:
        source = list(csv.DictReader(stream))[731 - 2]
    assert source["Operator"] == "NRMA" and source["Charger_Type"] == "DC"
    assert source["Station_address"] == "81 Meehan St, Yass NSW 2582, Australia"
    locations, records, _ = frames()
    # Exercise scope after an accepted association; source-point corrections
    # precede matching and are covered separately. This fixture uses the OSM point.
    for field, value in {"operator_name": "NRMA", "latitude": node["lat"],
                         "longitude": node["lon"], "address": source["Station_address"],
                         "postcode": "2582", "address_postcode": "2582"}.items():
        locations.loc[0, field] = value
    monkeypatch.setattr(osm, "RAW", tmp_path)
    (tmp_path / "osm_chargers.json").write_text(json.dumps({"elements": [node]}), encoding="utf-8")
    details = pd.DataFrame([dict(attribute="operator_website", operator_name="NRMA",
                                value="https://www.mynrma.com.au/cars-and-driving/electric-vehicles")])
    assert classify_url_attribute(manifest["resolved_url"], "NRMA", operator_website_hosts(details),
                                  original_attribute="website") == ("operator_network_map_url", "operator")
    sites, matches, _, attributes = osm.osm_augment(locations, records, operator_details=details)
    assert matches.osm_id.tolist() == ["node/7816558586"]
    assert sites.iloc[0].website == manifest["url"]
    assert json.loads(sites.iloc[0].tags_json) == node["tags"]
    network = attributes.loc[attributes.attribute.eq("operator_network_map_url")].iloc[0]
    assert (network.value, network.scope, network.osm_id, network.source_file) == (
        manifest["url"], "operator", "node/7816558586", "data/raw/osm_chargers.json")
    assert not attributes.attribute.eq("website").any()
    assert set(attributes.loc[attributes.scope.eq("site"), "attribute"]) == {"dc_connector_types", "access", "fee"}


def test_osm_homepage_retains_osm_provenance_but_is_operator_scope(tmp_path, monkeypatch):
    loc, records, _ = frames()
    monkeypatch.setattr(osm, "RAW", tmp_path)
    (tmp_path / "osm_chargers.json").write_text(json.dumps({"elements": [dict(type="node", id=2,
        lat=-33.86001, lon=151.20001, tags={"operator": "Evie", "socket:type2_combo": "1",
        "addr:housenumber": "1", "addr:street": "Test Street", "website": "https://goevie.com.au/"})]}))
    details = pd.DataFrame([dict(attribute="operator_website", operator_name="Evie", value="http://goevie.com.au/")])
    sites, matches, _, attributes = osm.osm_augment(loc, records, operator_details=details)
    website = attributes.loc[attributes.attribute.eq("operator_website")].iloc[0]
    assert len(matches) == 1 and sites.iloc[0].website == "https://goevie.com.au/"
    assert website.scope == "operator" and website.osm_id == "node/2"
    assert website.source_file == "data/raw/osm_chargers.json"


def test_zero_quantity_and_different_statuses_preserve_original_connections(tmp_path, monkeypatch):
    monkeypatch.setattr(augment, "RAW", tmp_path)
    reference = {name: [] for name in ["Operators", "ConnectionTypes", "DataProviders", "UsageTypes", "StatusTypes"]}
    reference.update(Operators=[dict(ID=1, Title="Evie", WebsiteURL="https://goevie.com.au/")],
        ConnectionTypes=[dict(ID=33, Title="CCS (Type 2)"), dict(ID=2, Title="CHAdeMO")],
        StatusTypes=[dict(ID=50, Title="Operational", IsOperational=True),
                     dict(ID=100, Title="Not Operational", IsOperational=False),
                     dict(ID=150, Title="Planned For Future Date", IsOperational=False)])
    (tmp_path / "ocm_reference.json").write_text(json.dumps(reference))
    (tmp_path / "ocm_au_tree.json").write_text(json.dumps({"tree": [{"type": "blob", "path": "OCM-1.json"}]}))
    (tmp_path / "ocm").mkdir()
    poi = dict(ID=1, OperatorID=1, StatusTypeID=50, DateLastVerified="2020-11-19T13:08:00Z",
        AddressInfo=dict(CountryID=18, Latitude=-33.86001, Longitude=151.20001, AddressLine1="1 Test Street",
                         Postcode="2000", AccessComments="https://goevie.com.au/our-network/"),
        Connections=[dict(ID=11, ConnectionTypeID=33, CurrentTypeID=30, StatusTypeID=50, Quantity=0),
                     dict(ID=12, ConnectionTypeID=2, CurrentTypeID=30, StatusTypeID=100, Quantity=1),
                     dict(ID=13, ConnectionTypeID=2, CurrentTypeID=30, StatusTypeID=150)])
    (tmp_path / "ocm/OCM-1.json").write_text(json.dumps(poi))
    monkeypatch.setattr(augment, "load_address_exceptions", lambda *args: {})
    monkeypatch.setattr(augment, "load_operator_reviews", lambda *args: {})
    locations, records, _ = frames()
    sites, connectors, matches, _, _, attributes = augment.augment(locations, records)
    assert len(matches) == 1 and len(connectors) == 3
    assert connectors.status_type_id.tolist() == [50, 100, 150]
    assert connectors.is_operational.tolist() == [True, False, False]
    assert attributes.loc[attributes.attribute.eq("dc_connector_types"), "value"].tolist() == ["CHAdeMO"]
    assert sites.iloc[0].last_verified == "2020-11-19T13:08:00Z"
    assert sites.iloc[0].last_verified_at.isoformat() == "2020-11-19T13:08:00+00:00"
    url = attributes.loc[attributes.attribute.eq("operator_network_map_url")].iloc[0]
    assert url.scope == "operator" and url.ocm_id == 1
    quality = connector_quality(sites, connectors, matches)
    assert set(zip(quality.connection_id, quality.category)) == {
        (11, "zero_quantity_dc_connection"), (12, "site_connection_status_difference"),
        (13, "site_connection_status_difference")}
    assert connector_quality(sites, connectors, matches.iloc[:0]).empty
