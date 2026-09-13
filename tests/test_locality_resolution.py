# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Postal codes cannot override differing, explicitly parsed locality evidence."""
import json

import pandas as pd
import pytest

from ev_pipeline import resolve
from ev_pipeline.clean import load_clean
from ev_pipeline.resolve import locality_relation, normalize_locality, resolve_conflicts, source_locality


@pytest.mark.parametrize("address,expected", [
    ("10 Main St, Northside NSW 2000", "northside"),
    ("10 Main St Northside NSW 2000 Australia", "northside"),
    ("Car park, Little Hoskins St, Temora, NSW 2666", "temora"),
    ("Kintore Headframe Car Park, 51 Bromide St, Broken Hill, NSW 2880, Australia", "broken hill"),
    ("10 Northside Street, Southside NSW 2000", "southside"),
    ("10 Main St, Sydney, 2000", "sydney"),
    ("10 Main St, St. Leonards NSW 2065", "saint leonards"),
    ("10 Main St, Mt Victoria NSW 2786", "mount victoria"),
    ("10 Main St, The Entrance NSW 2261", "the entrance"),
    ("180 The Entrance Rd The Entrance NSW 2261 Australia", "the entrance"),
    ("10 Main St, The Entrance North NSW 2261", "the entrance north"),
    ("10 Main St NSW 2000", None),
    ("10 Main St, Building A NSW 2000", None),
    ("10 Main St, Northside", None),
    ("Station somewhere, NSW 2000", None),
])
def test_only_explicit_postal_locality_is_extracted(address, expected):
    assert source_locality(address) == expected


@pytest.mark.parametrize("value", [None, "", "NSW", "Australia", "Northside, NSW", "unknown", "2000"])
def test_missing_or_compound_external_town_stays_unknown(value):
    assert normalize_locality(value) is None


@pytest.mark.parametrize("value", ["Entrance", "Main entrance", "Rear pedestrian entrance", "North entrance", "Entrance via Bay Road"])
def test_explicit_entrance_instructions_are_not_locality_names(value):
    assert normalize_locality(value) is None


@pytest.mark.parametrize("source,external,postcode,latitude,longitude,expected", [
    ("Northside", "Southside", "2000", -34.3, 151, "unverified_difference"),
    ("Fairview", "Lakeside", "2000", -34.3, 151, "unverified_difference"),
    ("Sydney", "Broken Hill", "2150", -33.815, 151.005, "unverified_difference"),
    ("Sydney", "Parramatta", "2150", -33.815, 151.005, "reviewed_hierarchy"),
    ("Parramatta", "Sydney", "2150", -33.815, 151.005, "reviewed_hierarchy"),
    ("Sydney", "Parramatta", "2000", -33.815, 151.005, "unverified_difference"),
    ("Sydney", "Parramatta", "2150", -31, 151.005, "unverified_difference"),
    ("Sydney", "Parramatta", "2150", -33.815, 152, "unverified_difference"),
    ("St Leonards", "Saint Leonards", "2065", -33.8, 151.2, "same"),
    (None, "Lakeside", "2000", -34.3, 151, "unknown"),
    ("Fairview", None, "2000", -34.3, 151, "unknown"),
])
def test_different_names_need_a_bounded_relationship(source, external, postcode, latitude, longitude, expected):
    assert locality_relation(source, external, postcode, postcode, latitude, longitude) == expected


def test_reviewed_hierarchy_also_requires_both_postcodes_to_agree():
    assert locality_relation("Sydney", "Parramatta", "2150", "2151", -33.815, 151.005) == "unverified_difference"


@pytest.mark.parametrize("source_address,town,postcode,external_postcode,point,decision", [
    ("10 Main St, Northside NSW 2000", "Southside", "2000", "2000", (-34.3, 151), "unresolved"),
    ("10 Main St, Fairview NSW 2000", "Lakeside", "2000", "2000", (-34.3, 151), "unresolved"),
    ("10 Main St, The Entrance NSW 2261", "Long Jetty", "2261", "2261", (-34.843, 151), "unresolved"),
    ("10 Main St, The Entrance NSW 2261", "The Entrance", "2261", "2261", (-34.843, 151), "resolved"),
    ("10 Main St, Sydney NSW 2150", "Parramatta", "2150", "2150", (-33.815, 151.005), "resolved"),
    ("10 Main St, Sydney NSW 2150", "Parramatta", "2150", "2150", (-31, 151.005), "unresolved"),
    ("10 Main St, Sydney NSW 2150", "Broken Hill", "2150", "2150", (-33.815, 151.005), "unresolved"),
    ("10 Main St, Northside NSW 2000", None, "2000", "2000", (-34.3, 151), "resolved"),
    ("10 Main St NSW 2000", "Southside", "2000", "2000", (-34.3, 151), "resolved"),
    # A town name embedded in a street is not town evidence for a malformed postcode.
    ("10 Main St, Northside NSW 2000", "Main", "2000", "NSW", (-34.3, 151), "unresolved"),
])
def test_locality_evidence_controls_correction_without_changing_unknown_policy(
        monkeypatch, source_address, town, postcode, external_postcode, point, decision):
    source = pd.DataFrame([dict(record_id="r_fixture", source_row=2, location_id="l_fixture",
                                operator_name="Evie", address=source_address, latitude=-33.0, longitude=151.0,
                                postcode="2999", address_postcode=postcode, address_conflict=True)])
    external = pd.DataFrame([dict(ocm_id=1, ocm_operator="Evie", postcode=external_postcode,
                                  town=town, address="10 Main Street", latitude=point[0], longitude=point[1],
                                  source_file="synthetic.json")])
    osm = {"elements": [dict(type="node", id=1, lat=point[0], lon=point[1],
                             tags={"operator": "Evie", "amenity": "charging_station"})]}

    class MemorySnapshot:
        def __truediv__(self, filename):
            return self

        def read_text(self, **kwargs):
            return json.dumps(osm)

    monkeypatch.setattr(resolve, "external_data", lambda: (external, None, None))
    monkeypatch.setattr(resolve, "RAW", MemorySnapshot())
    issues = []
    result, audit = resolve_conflicts(source, issues)
    assert audit.iloc[0].decision == decision
    if decision == "unresolved":
        pd.testing.assert_frame_equal(source, result[source.columns])
        assert not issues
        if external_postcode == postcode:
            assert "locality_not_verified" in audit.iloc[0].reason
    else:
        assert not result.iloc[0].address_conflict
        assert (result.iloc[0].latitude, result.iloc[0].longitude) == point


def test_current_eleven_auto_resolutions_have_no_new_locality_disagreement():
    _, records, issues, _ = load_clean()
    _, audit = resolve_conflicts(records, issues)
    assert set(audit.loc[audit.decision.eq("resolved"), "source_row"]) == {
        4, 29, 96, 197, 333, 417, 593, 731, 736, 824, 888,
    }
