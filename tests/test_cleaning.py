# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

import json
import pandas as pd
import pytest
from ev_pipeline import clean, resolve
from ev_pipeline.clean import (
    power, operator, identifier, load_clean, spatial_assign, location_representatives,
    flag_final_location_conflicts,
)


@pytest.mark.parametrize("raw,expected", [
    ("2x350kW & 6x175kW", (175.0, 350.0, "multiple")),
    ("22", (22.0, 22.0, "single")),
    ("7.4 kW", (7.4, 7.4, "single")),
    ("AC", (None, None, "unknown")),
    ("-22 kW", (None, None, "invalid")),
    ("0 kW", (None, None, "invalid")),
])
def test_power_preserves_units_and_does_not_sum_plugs(raw, expected):
    assert power(raw) == expected


def test_operator_country_and_aliases():
    assert operator(" BP Australia ") == "BP Pulse (AU)"
    assert operator("BP Pulse (UK)") != operator("BP Pulse (AU)")
    assert operator("Non-Networked") == "Non-networked"
    assert operator("Evie Networks") == operator("Evie")
    assert operator("Unknown new provider") == "unknown new provider"


def test_ids_do_not_depend_on_dict_order():
    assert identifier("r_", {"b": 2, "a": 1}) == identifier("r_", {"a": 1, "b": 2})


def test_actual_input_accounting_and_missing_values():
    raw, records, issues, duplicates = load_clean()
    assert len(raw) == len(records) + len(duplicates)
    assert records.record_id.is_unique
    assert records.loc[records.power_raw == "AC", "power_max_kw"].isna().all()
    assert records.loc[records.power_raw.str.contains("350kW"), "power_max_kw"].eq(350).all()
    assert records.loc[raw.PCODE.str.startswith("NSW "), "postcode"].str.fullmatch(r"\d{4}").all()
    assert records.station_name.isna().sum() == raw.Station_name.eq("").sum()
    assert records.address_conflict.any()


def test_actual_address_variants_share_locations_and_preserve_source_evidence():
    raw, records, issues, _ = load_clean()
    by_row = records.set_index("source_row")
    pairs = [(373, 1076), (532, 1075), (557, 1101), (603, 1001), (606, 1089),
             (657, 1052), (776, 1037), (817, 1012), (1096, 1317),
             (262, 1057), (982, 1690)]
    flagged = {issue["record_id"] for issue in issues if issue["code"] == "multiple_records_one_location"}
    for first, second in pairs:
        a, b = by_row.loc[first], by_row.loc[second]
        assert a.location_id == b.location_id, (first, second)
        assert a.record_id != b.record_id  # Both source observations survive.
        assert {a.record_id, b.record_id} <= flagged
        for row in (a, b):
            assert json.loads(row.raw_json) == raw.iloc[row.name - 2].to_dict()
    # A shared location must not erase inconsistent plug counts or power evidence.
    assert by_row.loc[532, "number_of_plugs"] != by_row.loc[1075, "number_of_plugs"]


def test_merged_location_keeps_complete_metadata_and_original_provenance():
    _, records, _, _ = load_clean()
    representatives = location_representatives(records)
    balmain_id = records.set_index("source_row").loc[1096, "location_id"]
    balmain = representatives.set_index("location_id").loc[balmain_id]
    assert balmain.source_row == 1317
    assert balmain.postcode == "2041" and balmain.lga == "Inner West Council"
    assert balmain.raw_json == records.set_index("source_row").loc[1317, "raw_json"]
    assert representatives.location_id.tolist() == records.location_id.drop_duplicates().tolist()
    # Selection is stable even if a caller provides the records in another order.
    shuffled = location_representatives(records.iloc[::-1]).set_index("location_id")
    assert shuffled.source_row.to_dict() == representatives.set_index("location_id").source_row.to_dict()


def test_address_format_cleanup_does_not_merge_distinct_location_identities(tmp_path, monkeypatch):
    base = dict.fromkeys(clean.FIELDS, "")
    base.update(Station_address="Unit 1/10 Test St, Sydney NSW 2000", Operator="Evie",
                Number_of_plugs="2", Charger_Type="DC", Charger_rating="50 kW",
                Latitude="-33.86", Longitude="151.20", PCODE="2000")
    variants = [
        {},
        {"Station_address": " unit 1/10 Test St\nSydney NSW 2000 "},
        {"Station_address": "Unit 2/10 Test St, Sydney NSW 2000"},
        {"Station_address": "Unit 1/100 Test St, Sydney NSW 2000"},
        {"Station_address": "Unit 1-10 Test St, Sydney NSW 2000"},
        {"Station_address": "Level 2 Unit 1/10 Test St, Sydney NSW 2000"},
        {"Operator": "Tesla"},
        {"Longitude": "151.2001"},
    ]
    source = pd.DataFrame([dict(base, OBJECTID=str(i), **change) for i, change in enumerate(variants)])
    source.to_csv(tmp_path / "ev_20251216.csv", index=False)
    monkeypatch.setattr(clean, "RAW", tmp_path)
    _, records, _, duplicates = load_clean()
    assert len(records) == len(variants) and duplicates.empty
    assert records.iloc[0].location_id == records.iloc[1].location_id
    assert records.location_id.nunique() == len(variants) - 1


def test_optional_postal_suffix_does_not_hide_conflicting_known_postcodes(tmp_path, monkeypatch):
    base = dict.fromkeys(clean.FIELDS, "")
    base.update(Station_address="10 Test St Sydney NSW 2000 Australia", Operator="Evie",
                Number_of_plugs="2", Charger_Type="DC", Charger_rating="50 kW",
                Latitude="-33.86", Longitude="151.20", PCODE="2000")
    other = dict(base, OBJECTID="2", Station_address="10 Test St Sydney NSW 2001", PCODE="2001")
    pd.DataFrame([dict(base, OBJECTID="1"), other]).to_csv(tmp_path / "ev_20251216.csv", index=False)
    monkeypatch.setattr(clean, "RAW", tmp_path)
    _, records, issues, _ = load_clean()
    assert len(records) == 2 and records.location_id.nunique() == 1
    assert records.address_conflict.all()
    assert sum(i["code"] == "cross_record_postcode_conflict" for i in issues) == 2


def test_individually_resolved_rows_cannot_hide_a_conflicting_location_group(monkeypatch):
    base = dict.fromkeys(clean.FIELDS, "")
    base.update(Station_address="10 Test St Sydney NSW 2000 Australia", Operator="Evie",
                Number_of_plugs="2", Charger_Type="DC", Charger_rating="50 kW",
                Latitude="-33.86", Longitude="151.20", PCODE="2000")
    raw = pd.DataFrame([dict(base, OBJECTID="1"),
                        dict(base, OBJECTID="2", Station_address="10 Test St Sydney NSW 2001", PCODE="2001")])
    monkeypatch.setattr(clean.pd, "read_csv", lambda *args, **kwargs: raw.copy())
    _, records, issues, _ = load_clean()
    assert records.location_id.nunique() == 1 and records.address_conflict.all()

    # Synthetic external observations each resolve one row, but disagree about
    # the final identity represented by their shared original location_id.
    external = pd.DataFrame([
        dict(ocm_id=i, ocm_operator="Evie", postcode=postcode, town="Sydney", address="10 Test Street",
             latitude=latitude, longitude=151.20, source_file=f"synthetic-{i}.json")
        for i, postcode, latitude in [(1, "2000", -33.85), (2, "2001", -33.87)]
    ])
    osm = {"elements": [dict(type="node", id=i, lat=latitude, lon=151.20, tags={"operator": "Evie"})
                        for i, latitude in [(1, -33.85), (2, -33.87)]]}

    class MemorySnapshot:
        def __truediv__(self, name):
            return self

        def read_text(self, **kwargs):
            return json.dumps(osm)

    monkeypatch.setattr(resolve, "external_data", lambda: (external, None, None))
    monkeypatch.setattr(resolve, "RAW", MemorySnapshot())
    resolved, audit = resolve.resolve_conflicts(records, issues)
    assert audit.decision.eq("resolved").all() and not resolved.address_conflict.any()
    before = resolved.drop(columns="address_conflict").copy(deep=True)

    locations, _ = spatial_assign(resolved, issues)
    assert len(resolved) == 2 and len(locations) == 1
    assert resolved.address_conflict.all() and locations.address_conflict.all()
    assert locations.loc[~locations.address_conflict].empty  # Excluded by the analysis-ready view predicate.
    pd.testing.assert_frame_equal(before, resolved.drop(columns="address_conflict"))
    final_issues = [issue for issue in issues if issue["code"] == "post_resolution_location_conflict"]
    assert {issue["record_id"] for issue in final_issues} == set(resolved.record_id)


@pytest.mark.parametrize("second_change", [
    {"latitude": -33.87},
    {"postcode": "2001"},
    {"address_postcode": "2001"},
])
def test_final_group_checks_each_coordinate_and_postal_source_independently(second_change):
    first = dict(record_id="r1", source_row=2, location_id="l1", latitude=-33.86, longitude=151.20,
                 postcode="2000", address_postcode="2000", address_conflict=False)
    second = dict(first, record_id="r2", source_row=3, **second_change)
    records = pd.DataFrame([first, second])
    issues = []
    flag_final_location_conflicts(records, issues)
    assert records.address_conflict.all() and len(issues) == 2


def test_final_group_agreement_tolerates_missing_postcodes_and_same_coordinate_key():
    first = dict(record_id="r1", source_row=2, location_id="l1", latitude=-33.86, longitude=151.20,
                 postcode="2000", address_postcode="2000", address_conflict=False)
    second = dict(first, record_id="r2", source_row=3, latitude=-33.8600001, postcode=None)
    records = pd.DataFrame([first, second])
    issues = []
    flag_final_location_conflicts(records, issues)
    assert not records.address_conflict.any() and not issues
    # Consistency checking must never clear a remaining per-record conflict.
    records.loc[1, "address_conflict"] = True
    flag_final_location_conflicts(records, issues)
    assert records.loc[1, "address_conflict"] and not issues


def test_actual_spatial_assignment_preserves_coordinates():
    _, records, issues, _ = load_clean()
    locations, regions = spatial_assign(records, issues)
    assert locations.location_id.is_unique
    assert locations.sa4_code.notna().all()
    assert set(locations.sa4_code) <= set(regions.sa4_code)
    approximate = locations[locations.sa4_method != "point_in_polygon"]
    assert approximate.sa4_distance_m.between(0, 50).all()
    before = records.drop_duplicates("location_id").set_index("location_id")
    after = locations.set_index("location_id")
    pd.testing.assert_frame_equal(before[["latitude", "longitude"]], after[["latitude", "longitude"]])
