# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Carpark hours are literal venue notes, not inferred charger availability."""
import json

import pytest

from ev_pipeline import jolt
from tests.test_matching import frames


@pytest.mark.parametrize("address,expected", [
    ("904 Gardeners Rd, NSW 2020\r\nCarpark open 8:30-19:00", "Carpark open 8:30-19:00"),
    ("904 Gardeners Rd, NSW 2020\r\n\r\nCarpark open 8:30-19:00", "Carpark open 8:30-19:00"),
    ("Carpark open 0:00-24:00", "Carpark open 0:00-24:00"),
    ("1 Example St, NSW 2000", None),
    ("Temporarily compatible with front charging ONLY", None),
    ("Carpark open 8:30-19:00 weekdays only", None),
    (None, None),
])
def test_only_explicit_complete_hours_notes_are_extracted(address, expected):
    assert jolt.carpark_hours_text(address) == expected


@pytest.mark.parametrize("note", ["Carpark open 25:00-26:00", "Carpark open 8:70-19:00",
                                  "Carpark open 8:00-24:01",
                                  "Carpark open 8:30-19:00\nCarpark open 7:00-20:00"])
def test_invalid_and_contradictory_notes_do_not_become_access_attributes(note):
    with pytest.raises(ValueError, match="JOLT carpark-hours"):
        jolt.carpark_hours_text(note)


def test_matched_jolt_note_keeps_source_identity_and_original_address(tmp_path, monkeypatch):
    address = "1 Test St, NSW 2000\r\nCarpark open 8:30-19:00"
    points = {"first": dict(id=1, name="TEST001", address=address, lat=-33.86001, lng=151.20001),
              "far": dict(id=2, name="FAR002", address=address, lat=-31.0, lng=149.0)}
    (tmp_path / "jolt_map.html").write_text("var jolt = " + json.dumps({"charging_points": points}) + ";")
    monkeypatch.setattr(jolt, "RAW", tmp_path)
    locations, records, _ = frames()
    locations.loc[0, "operator_name"] = "JOLT"
    sites, matches, _, attributes = jolt.jolt_augment(locations, records)
    assert len(matches) == 1 and sites.address.tolist() == [address, address]
    hours = attributes.loc[attributes.attribute.eq("operator_carpark_hours_text")]
    assert len(hours) == 1 and hours.iloc[0].jolt_id == 1
    assert hours.iloc[0].value == "Carpark open 8:30-19:00"
    assert hours.iloc[0].scope == "site" and hours.iloc[0].source_file == "data/raw/jolt_map.html"
    assert hours.iloc[0].method == "coordinate_operator_address_match"
    assert "opening_hours" not in set(attributes.attribute)
