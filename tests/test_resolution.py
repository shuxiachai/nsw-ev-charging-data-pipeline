import json
import pandas as pd
import pytest
from ev_pipeline import resolve
from ev_pipeline.clean import load_clean
from ev_pipeline.resolve import resolve_conflicts
from ev_pipeline.augment import address_similarity, GEOD
from ev_pipeline.pipeline import connect, DB


@pytest.mark.parametrize("a,b", [
    ("Car park, Little Hoskins St, Temora NSW 2666", "Little Hoskins Street"),
    ("20-22 Camden Rd Campbelltown NSW 2560 Australia", "20-22 Camden Road"),
    ("Kintore Headframe Car Park, 51 Bromide St, Broken Hill NSW 2880", "51 Bromide Street"),
])
def test_street_comparison_ignores_site_labels_and_locality(a, b):
    assert address_similarity(a, b) == 1


def test_absent_addresses_are_not_similar():
    assert address_similarity(None, None) == 0


def test_resolution_preserves_originals_and_requires_corroboration():
    _, original, issues, _ = load_clean()
    resolved, audit = resolve_conflicts(original, issues)
    pd.testing.assert_series_equal(original.latitude, resolved.original_latitude, check_names=False)
    pd.testing.assert_series_equal(original.longitude, resolved.original_longitude, check_names=False)
    pd.testing.assert_series_equal(original.postcode, resolved.original_postcode, check_names=False)
    accepted = audit[audit.decision == "resolved"]
    assert len(accepted) > 0
    assert accepted.ocm_id.notna().all() and accepted.osm_id.notna().all()
    assert accepted.address_similarity.ge(0.85).all()
    assert accepted.cross_source_distance_m.le(150).all()
    for row in audit[audit.decision == "unresolved"].itertuples():
        a = resolved.set_index("record_id").loc[row.record_id]
        assert a.address_conflict
        assert a.latitude == a.original_latitude and a.longitude == a.original_longitude


def test_stored_resolution_evidence_matches_actual_external_geometry():
    with connect(DB) as con:
        rows = con.execute("SELECT s.cross_source_distance_m,e.longitude,e.latitude,o.longitude,o.latitude FROM source_resolution s JOIN external_site e USING(ocm_id) JOIN osm_site o USING(osm_id) WHERE decision='resolved'").fetchall()
        for recorded, x1, y1, x2, y2 in rows:
            actual = GEOD.inv(x1,y1,x2,y2)[2]
            assert actual == pytest.approx(recorded, abs=1e-6)
        assert con.execute("SELECT count(*) FROM analysis_ready_locations WHERE address_conflict").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM location WHERE address_conflict").fetchone()[0] > 0


@pytest.fixture
def corroborated_candidate(monkeypatch):
    """One OCM/OSM point agrees exactly; source address identity still matters."""
    def configure(address, osm_tags=None, extra_osm=None):
        external = pd.DataFrame([dict(ocm_id=1, ocm_operator="Evie", postcode="2000", town="Sydney",
                                     address=address, latitude=-33.85, longitude=151.20,
                                     source_file="synthetic.json")])
        osm = {"elements": [dict(type="node", id=1, lat=-33.85, lon=151.20,
                                 tags={"operator": "Evie", "amenity": "charging_station", **(osm_tags or {})})]}
        osm["elements"].extend(extra_osm or [])

        class MemorySnapshot:
            def __truediv__(self, filename):
                return self

            def read_text(self, **kwargs):
                return json.dumps(osm)

        monkeypatch.setattr(resolve, "external_data", lambda: (external, None, None))
        monkeypatch.setattr(resolve, "RAW", MemorySnapshot())
        return dict(record_id="r_fixture", source_row=2, location_id="l_fixture", operator_name="Evie",
                    latitude=-33.86, longitude=151.20, postcode="2001", address_postcode="2000",
                    address_conflict=True, address="10 Test St, Sydney NSW 2000")
    return configure


@pytest.mark.parametrize("source_address,external_address,reason", [
    ("10 Test St, Sydney NSW 2000", "100 Test Street", "house_number_conflict"),
    ("10 Constitution St, Sydney NSW 2000", "10 Constitution Road", "street_type_conflict"),
    ("8/24 Cross St, Sydney NSW 2000", "8 Cross Street", "house_number_conflict"),
])
def test_fuzzy_address_cannot_overrule_explicit_street_contradictions(
        corroborated_candidate, source_address, external_address, reason):
    source = corroborated_candidate(external_address)
    source["address"] = source_address
    assert address_similarity(source_address, external_address) >= 0.85
    records = pd.DataFrame([source])
    resolved, audit = resolve_conflicts(records, [])
    assert audit.iloc[0].decision == "unresolved" and reason in audit.iloc[0].reason
    pd.testing.assert_frame_equal(records, resolved[records.columns])


def test_house_number_is_not_the_unit_number(corroborated_candidate):
    source = corroborated_candidate("24 Cross Street")
    source["address"] = "8/24 Cross St, Sydney NSW 2000"
    resolved, audit = resolve_conflicts(pd.DataFrame([source]), [])
    assert audit.iloc[0].decision == "resolved"
    assert not resolved.iloc[0].address_conflict


def test_correcting_one_record_does_not_reuse_its_street_evidence_for_another(corroborated_candidate):
    first = corroborated_candidate("100 Test Street")
    first["address"] = "100 Test St, Sydney NSW 2000"
    second = dict(first, record_id="r_second", source_row=3, location_id="l_second",
                  address="10 Test St, Sydney NSW 2000")
    records = pd.DataFrame([first, second])
    resolved, audit = resolve_conflicts(records, [])
    assert audit.decision.tolist() == ["resolved", "unresolved"]
    assert resolved.address_conflict.tolist() == [False, True]
    pd.testing.assert_series_equal(records.iloc[1], resolved[records.columns].iloc[1])


def test_no_conflicts_keeps_the_audit_schema_without_reading_external_sources(monkeypatch):
    records = pd.DataFrame([dict(record_id="r_fixture", latitude=-33.86, longitude=151.20,
                                 postcode="2000", address_conflict=False)])
    monkeypatch.setattr(resolve, "external_data", lambda: pytest.fail("Unneeded external read"))
    for source in (records, records.iloc[:0].copy()):
        issues = []
        resolved, audit = resolve_conflicts(source, issues)
        assert audit.empty and list(audit.columns) == resolve.AUDIT_COLUMNS
        assert audit.decision.value_counts().to_dict() == {}
        assert not issues
        pd.testing.assert_frame_equal(source, resolved[source.columns])


def test_wagga_unit_and_house_number_conflict_is_withheld_in_the_actual_snapshot():
    _, original, issues, _ = load_clean()
    resolved, audit = resolve_conflicts(original, issues)
    row = resolved.loc[resolved.source_row.eq(727)].iloc[0]
    decision = audit.loc[audit.record_id.eq(row.record_id)].iloc[0]
    assert row.address == "8/24 Cross St, Wagga Wagga, NSW 2650"
    assert decision.decision == "unresolved" and "house_number_conflict" in decision.reason
    assert row.address_conflict and row.resolution_method == "unchanged"
    assert (row.latitude, row.longitude, row.postcode) == (row.original_latitude, row.original_longitude, row.original_postcode)


@pytest.mark.parametrize("tags,reason", [
    ({"addr:housenumber": "999", "addr:street": "Test Street"}, "house_number_conflict"),
    ({"addr:housenumber": "10", "addr:street": "Test Road"}, "street_type_conflict"),
    ({"addr:postcode": "2001"}, "postcode_conflict"),
    ({"addr:full": "999 Test Street, Sydney NSW 2000"}, "house_number_conflict"),
    ({"addr:full": "10 Test Street, Sydney NSW 2001"}, "postcode_conflict"),
    ({"addr:postcode": "2000", "addr:full": "10 Test Street, Sydney NSW 2001"}, "postcode_conflict"),
])
def test_explicit_osm_contradiction_cannot_corroborate_correction(corroborated_candidate, tags, reason):
    source = corroborated_candidate("10 Test Street", osm_tags=tags)
    records = pd.DataFrame([source])
    issues = []
    resolved, audit = resolve_conflicts(records, issues)
    assert audit.iloc[0].decision == "unresolved"
    assert "OSM node/1" in audit.iloc[0].reason and reason in audit.iloc[0].reason
    pd.testing.assert_frame_equal(records, resolved[records.columns])
    assert not issues


@pytest.mark.parametrize("tags", [
    {},
    {"addr:postcode": "2000"},
    {"addr:housenumber": "8/10", "addr:street": "Test Street"},
    {"addr:housenumber": "8-12", "addr:street": "Test Street"},
    {"addr:full": "10 Test Street, Sydney NSW 2000"},
])
def test_compatible_or_missing_osm_address_keeps_corroboration(corroborated_candidate, tags):
    source = corroborated_candidate("10 Test Street", osm_tags=tags)
    result, audit = resolve_conflicts(pd.DataFrame([source]), [])
    assert audit.iloc[0].decision == "resolved"
    assert not result.iloc[0].address_conflict
    assert (result.iloc[0].latitude, result.iloc[0].longitude) == (-33.85, 151.20)


def test_contradictory_nearest_osm_does_not_hide_a_valid_corroborator(corroborated_candidate):
    source = corroborated_candidate("10 Test Street", osm_tags={"addr:postcode": "2001"}, extra_osm=[
        {"type": "way", "id": 2, "center": {"lat": -33.8501, "lon": 151.20},
         "tags": {"operator": "Evie", "amenity": "charging_station", "addr:postcode": "2000"}}])
    _, audit = resolve_conflicts(pd.DataFrame([source]), [])
    assert audit.iloc[0].decision == "resolved" and audit.iloc[0].osm_id == "way/2"
