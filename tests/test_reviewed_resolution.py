from copy import deepcopy
from hashlib import sha256
import json
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from ev_pipeline.acquire import ROOT
from ev_pipeline.clean import load_clean
from ev_pipeline.resolve import resolve_conflicts
from ev_pipeline.reviewed import METHOD, acquire_reviewed, apply_reviewed_resolutions


def rebind_fixture(root, config, filename):
    """Bind synthetic test evidence, never a production source or review."""
    path = root / filename
    source = next(item for item in config["sources"] if item["file"] == filename)
    source["sha256"] = sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name + ".meta.json").write_text(json.dumps({
        "url": source["url"], "sha256": source["sha256"], "bytes": path.stat().st_size,
        "retrieved_at_utc": "2026-09-09T00:00:00+00:00",
    }), encoding="utf-8")


@pytest.fixture
def reviewed_fixture(tmp_path):
    config = json.loads((ROOT / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
    config["resolutions"] = config["resolutions"][:1]
    entry = config["resolutions"][0]
    # Most edge cases need one synthetic review; do not copy the 50 MB Wagga
    # original (or construct unrelated evidence files) for every fixture.
    needed = {entry["coordinate"]["file"], entry["corroborating"]["file"], entry["address_source_file"],
              config["map_publication"]["source_file"], config["map_publication"]["map_file"]}
    config["sources"] = [source for source in config["sources"] if source["file"] in needed]
    expected = entry["expected_source"]
    row = {**expected, "record_id": entry["record_id"], "address_conflict": True,
           "original_latitude": expected["latitude"], "original_longitude": expected["longitude"],
           "original_postcode": expected["postcode"], "original_address_conflict": True,
           "resolution_method": "unchanged"}
    for source in config["sources"]:
        path = tmp_path / source["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic reviewed-address evidence", encoding="utf-8")
    osm = {"elements": [{"type": "node", "id": 8209129030, "lat": -29.0573208, "lon": 152.0189416,
                         "tags": {"amenity": "charging_station", "operator": "NRMA"}}]}
    (tmp_path / entry["coordinate"]["file"]).write_text(json.dumps(osm), encoding="utf-8")
    kml = ('<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>'
           + entry["corroborating"]["element_id"]
           + '</name><Point><coordinates>152.0186428,-29.057221,0</coordinates>'
             '</Point></Placemark></Document></kml>')
    (tmp_path / entry["corroborating"]["file"]).write_text(kml, encoding="utf-8")
    map_url = next(item["url"] for item in config["sources"]
                   if item["file"] == config["map_publication"]["map_file"])
    (tmp_path / config["map_publication"]["source_file"]).write_text(f'<iframe src="{map_url}"></iframe>', encoding="utf-8")
    for source in config["sources"]:
        rebind_fixture(tmp_path, config, source["file"])
    return tmp_path, config, pd.DataFrame([row])


def test_actual_archived_review_applies_seven_corrections_preserving_originals():
    _, original, issues, _ = load_clean()
    automated, _ = resolve_conflicts(original, issues)
    before = automated.copy(deep=True)
    reviewed, audit = apply_reviewed_resolutions(automated, issues)
    assert set(audit.source_row) == {78, 195, 217, 226, 727, 756, 956}
    assert len(audit) == 7 and audit.record_id.is_unique
    assert audit.evidence_distance_m.between(0, 150).all()
    for name in ["original_latitude", "original_longitude", "original_postcode", "original_address_conflict",
                 "address", "raw_json"]:
        pd.testing.assert_series_equal(before[name], reviewed[name])
    pd.testing.assert_frame_equal(automated, before)
    actual_osm = json.loads((ROOT / "data/raw/osm_chargers.json").read_text(encoding="utf-8"))["elements"]
    for row in audit.itertuples():
        if row.coordinate_element_id.startswith("OCM-"):
            point = json.loads((ROOT / row.coordinate_source_file).read_text(encoding="utf-8"))["AddressInfo"]
            assert (row.new_latitude, row.new_longitude) == (point["Latitude"], point["Longitude"])
        else:
            point = next(item for item in actual_osm if f"{item['type']}/{item['id']}" == row.coordinate_element_id)
            assert (row.new_latitude, row.new_longitude) == (point["lat"], point["lon"])
        stored = reviewed.set_index("record_id").loc[row.record_id]
        assert not stored.address_conflict and stored.resolution_method == METHOD
    wollongong = reviewed.loc[reviewed.source_row.eq(217)].iloc[0]
    assert not wollongong.address_conflict and wollongong.resolution_method == METHOD
    assert reviewed.address_conflict.sum() == automated.address_conflict.sum() - 7
    wollongong_audit = audit.loc[audit.source_row.eq(217)].iloc[0]
    assert wollongong_audit.coordinate_element_id == "OCM-191177"
    assert wollongong_audit.evidence_distance_m == pytest.approx(8.393113, abs=0.00001)
    wagga = audit.loc[audit.source_row.eq(727)].iloc[0]
    assert wagga.coordinate_element_id == "node/7932870081"
    assert wagga.evidence_distance_m == pytest.approx(10.915, abs=0.001)
    assert wagga.coordinate_change_m == pytest.approx(394052.851, abs=0.001)
    assert wagga.supporting_address_source_file == "data/raw/reviewed/wagga_council_agenda_20221107.html"
    assert "2043-2047" in wagga.supporting_address_locator
    walcha = audit.loc[audit.source_row.eq(78)].iloc[0]
    assert walcha.coordinate_element_id == "OCM-480135"
    assert walcha.corroborating_element_id == "way/737228454"
    assert walcha.corroborating_role == "mapped_landmark"
    assert walcha.evidence_distance_m == pytest.approx(76.7560055, abs=0.00001)
    assert audit.loc[~audit.source_row.eq(78), "corroborating_role"].eq("same_operator_charger").all()
    walcha_issue = next(item for item in issues if item["source_row"] == 78 and item["code"] == METHOD)
    assert "approximate road-reserve" in walcha_issue["detail"] and "not a second charger" in walcha_issue["detail"]
    previous = audit.loc[~audit.source_row.isin([78, 217, 727])]
    assert previous.supporting_address_source_file.isna().all()
    assert previous.supporting_address_locator.isna().all()
    # The reviewed site identity does not weaken ordinary unit/house-number guards.
    from ev_pipeline.augment import extended_address_conflict
    assert extended_address_conflict("8/24 Cross St", "8 Cross Street")


def test_tampered_address_document_is_rejected_even_with_updated_download_manifest(reviewed_fixture):
    root, config, records = reviewed_fixture
    filename = config["resolutions"][0]["address_source_file"]
    source = next(item for item in config["sources"] if item["file"] == filename)
    reviewed_hash = source["sha256"]
    (root / filename).write_text("Replaced document with new claims", encoding="utf-8")
    rebind_fixture(root, config, filename)
    source["sha256"] = reviewed_hash  # The review hash is deliberately not refreshed.
    issues = []
    with pytest.raises(ValueError, match="source/hash/metadata mismatch"):
        apply_reviewed_resolutions(records, issues, root=root, config=config)
    assert issues == [] and records.address_conflict.all()


def test_missing_archived_original_never_clears_a_conflict(reviewed_fixture):
    root, config, records = reviewed_fixture
    (root / config["resolutions"][0]["address_source_file"]).unlink()
    with pytest.raises(FileNotFoundError, match="Reviewed evidence missing"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


@pytest.mark.parametrize("field,value", [
    ("source_row", 999), ("operator_name", "Tesla"), ("address", "An unrelated street"),
    ("original_latitude", -20.0), ("original_postcode", "9999"),
    ("address_postcode", "9999"), ("charger_type", "AC"),
])
def test_original_identity_and_values_are_guarded(reviewed_fixture, field, value):
    root, config, records = reviewed_fixture
    records.loc[0, field] = value
    with pytest.raises(ValueError, match="Reviewed source guard failed"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


def test_missing_or_duplicate_record_identifier_is_rejected(reviewed_fixture):
    root, config, records = reviewed_fixture
    for candidate in [records.iloc[:0], pd.concat([records, records], ignore_index=True)]:
        with pytest.raises(ValueError, match="record missing or duplicated"):
            apply_reviewed_resolutions(candidate, [], root=root, config=config)


def test_no_overwrite_of_a_previous_resolution_or_second_application(reviewed_fixture):
    root, config, records = reviewed_fixture
    issues = []
    first, audit = apply_reviewed_resolutions(records, issues, root=root, config=config)
    count = len(issues)
    second, repeated = apply_reviewed_resolutions(first, issues, root=root, config=config)
    pd.testing.assert_frame_equal(first, second)
    assert len(audit) == 1 and repeated.empty and len(issues) == count
    automatic = records.copy()
    automatic.loc[0, ["address_conflict", "latitude", "resolution_method"]] = [False, -30.0, "coordinates_verified_ocm_osm"]
    untouched, skipped = apply_reviewed_resolutions(automatic, [], root=root, config=config)
    pd.testing.assert_frame_equal(automatic, untouched)
    assert skipped.empty


@pytest.mark.parametrize("change", ["operator", "distance"])
def test_cached_point_is_parsed_and_checked_instead_of_trusting_config(reviewed_fixture, change):
    root, config, records = reviewed_fixture
    filename = config["resolutions"][0]["coordinate"]["file"]
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    if change == "operator":
        data["elements"][0]["tags"]["operator"] = "Tesla"
    else:
        data["elements"][0]["lat"] = -35.0
    (root / filename).write_text(json.dumps(data), encoding="utf-8")
    rebind_fixture(root, config, filename)
    with pytest.raises(ValueError, match="expected operator|exceeds 150"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


def test_failure_does_not_leave_partial_mutations_or_quality_issues(reviewed_fixture):
    root, config, records = reviewed_fixture
    second_entry = deepcopy(config["resolutions"][0])
    second_entry["record_id"] = "second_record"
    config["resolutions"].append(second_entry)
    second_row = records.iloc[0].copy()
    second_row["record_id"] = "second_record"
    second_row["source_row"] = 999
    records = pd.concat([records, second_row.to_frame().T], ignore_index=True)
    before = records.copy(deep=True)
    issues = []
    with pytest.raises(ValueError, match="Reviewed source guard failed"):
        apply_reviewed_resolutions(records, issues, root=root, config=config)
    pd.testing.assert_frame_equal(records, before)
    assert issues == []


def test_acquisition_passes_review_hash_to_fetch(reviewed_fixture, monkeypatch):
    root, config, _ = reviewed_fixture
    requested = []
    def fake_fetch(url, path, offline, expected_sha256):
        requested.append((url, path, offline, expected_sha256))
        return path
    monkeypatch.setattr("ev_pipeline.reviewed.fetch", fake_fetch)
    acquire_reviewed(True, root=root, config=config)
    assert len(requested) == len(config["sources"])
    assert all(offline and len(digest) == 64 for _, _, offline, digest in requested)


@pytest.fixture
def supported_review_fixture(reviewed_fixture):
    root, config, records = reviewed_fixture
    filename = "data/raw/reviewed/second_primary.html"
    config["sources"].append({"file": filename, "url": "https://council.example/agenda", "sha256": ""})
    (root / filename).write_text("Synthetic council document linking the operator and named car park", encoding="utf-8")
    rebind_fixture(root, config, filename)
    config["resolutions"][0].update({"supporting_address_source_file": filename,
                                    "supporting_address_locator": "Council agenda, project paragraph"})
    return root, config, records


def test_second_primary_source_is_pinned_and_exported(supported_review_fixture):
    root, config, records = supported_review_fixture
    result, audit = apply_reviewed_resolutions(records, [], root=root, config=config)
    assert not result.address_conflict.any()
    entry = config["resolutions"][0]
    for field in ["supporting_address_source_file", "supporting_address_locator"]:
        assert audit.iloc[0][field] == entry[field]


def test_changed_supporting_original_cannot_be_authorized_by_refreshing_download_metadata(supported_review_fixture):
    root, config, records = supported_review_fixture
    filename = config["resolutions"][0]["supporting_address_source_file"]
    source = next(item for item in config["sources"] if item["file"] == filename)
    reviewed_hash = source["sha256"]
    (root / filename).write_text("Different document with different site identity", encoding="utf-8")
    rebind_fixture(root, config, filename)
    source["sha256"] = reviewed_hash
    issues = []
    with pytest.raises(ValueError, match="source/hash/metadata mismatch"):
        apply_reviewed_resolutions(records, issues, root=root, config=config)
    assert issues == [] and records.address_conflict.all()


@pytest.mark.parametrize("change", ["unlisted_file", "missing_locator", "missing_source", "blank_locator", "same_source"])
def test_supporting_source_and_locator_must_reference_distinct_pinned_evidence(supported_review_fixture, change):
    root, config, records = supported_review_fixture
    entry = config["resolutions"][0]
    if change == "unlisted_file":
        entry["supporting_address_source_file"] = "data/raw/reviewed/unreviewed.html"
    elif change == "missing_locator":
        del entry["supporting_address_locator"]
    elif change == "missing_source":
        del entry["supporting_address_source_file"]
    elif change == "blank_locator":
        entry["supporting_address_locator"] = " "
    else:
        entry["supporting_address_source_file"] = entry["address_source_file"]
    with pytest.raises(ValueError, match="Supporting address evidence"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


def test_missing_supporting_original_blocks_correction(supported_review_fixture):
    root, config, records = supported_review_fixture
    (root / config["resolutions"][0]["supporting_address_source_file"]).unlink()
    with pytest.raises(FileNotFoundError, match="Reviewed evidence missing"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


@pytest.fixture
def reviewed_ocm_fixture(tmp_path):
    config = json.loads((ROOT / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
    config["resolutions"] = [entry for entry in config["resolutions"] if entry["expected_source"]["source_row"] == 217]
    entry = config["resolutions"][0]
    needed = {entry["coordinate"]["file"], entry["coordinate"]["operator_reference_file"], entry["corroborating"]["file"],
              entry["address_source_file"], entry["supporting_address_source_file"], config["map_publication"]["source_file"]}
    config["sources"] = [source for source in config["sources"] if source["file"] in needed]
    for source in config["sources"]:
        path = tmp_path / source["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / source["file"]).read_bytes())
        rebind_fixture(tmp_path, config, source["file"])
    expected = entry["expected_source"]
    row = {**expected, "record_id": entry["record_id"], "address_conflict": True,
           "original_latitude": expected["latitude"], "original_longitude": expected["longitude"],
           "original_postcode": expected["postcode"], "original_address_conflict": True,
           "raw_json": json.dumps(expected["raw_values"]), "resolution_method": "unchanged"}
    return tmp_path, config, pd.DataFrame([row])


@pytest.mark.parametrize("change", ["id", "operator", "street", "town", "postcode", "country", "coordinate"])
def test_reviewed_ocm_original_is_parsed_and_semantically_guarded(reviewed_ocm_fixture, change):
    root, config, records = reviewed_ocm_fixture
    filename = config["resolutions"][0]["coordinate"]["file"]
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    if change == "id":
        data["ID"] += 1
    elif change == "operator":
        data["OperatorID"] = 23
    else:
        field, value = {"street": ("AddressLine1", "99 Other Road"), "town": ("Town", "Other Town"),
                        "postcode": ("Postcode", "9999"), "country": ("CountryID", 1),
                        "coordinate": ("Latitude", -30.0)}[change]
        data["AddressInfo"][field] = value
    (root / filename).write_text(json.dumps(data), encoding="utf-8")
    rebind_fixture(root, config, filename)
    issues = []
    with pytest.raises(ValueError, match="Reviewed OCM|exceeds 150"):
        apply_reviewed_resolutions(records, issues, root=root, config=config)
    assert not issues and records.address_conflict.all()


def test_ocm_operator_id_cannot_silently_change_meaning(reviewed_ocm_fixture):
    root, config, records = reviewed_ocm_fixture
    filename = config["resolutions"][0]["coordinate"]["operator_reference_file"]
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    next(op for op in data["Operators"] if op["ID"] == 3388)["Title"] = "Tesla"
    (root / filename).write_text(json.dumps(data), encoding="utf-8")
    rebind_fixture(root, config, filename)
    with pytest.raises(ValueError, match="operator reference"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


def test_ocm_review_guards_every_original_source_field(reviewed_ocm_fixture):
    root, config, records = reviewed_ocm_fixture
    original = json.loads(records.loc[0, "raw_json"])
    original["Number_of_plugs"] = "999"
    records.loc[0, "raw_json"] = json.dumps(original)
    with pytest.raises(ValueError, match="complete original fields"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


@pytest.fixture
def mapped_landmark_fixture(tmp_path):
    config = json.loads((ROOT / "config/reviewed_resolutions.json").read_text(encoding="utf-8"))
    config["resolutions"] = [entry for entry in config["resolutions"] if entry["expected_source"]["source_row"] == 78]
    entry = config["resolutions"][0]
    needed = {entry["coordinate"]["file"], entry["coordinate"]["operator_reference_file"], entry["corroborating"]["file"],
              entry["address_source_file"], entry["supporting_address_source_file"],
              config["map_publication"]["source_file"], config["map_publication"]["map_file"]}
    config["sources"] = [source for source in config["sources"] if source["file"] in needed]
    for source in config["sources"]:
        path = tmp_path / source["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / source["file"]).read_bytes())
        rebind_fixture(tmp_path, config, source["file"])
    expected = entry["expected_source"]
    row = {**expected, "record_id": entry["record_id"], "address_conflict": True,
           "original_latitude": expected["latitude"], "original_longitude": expected["longitude"],
           "original_postcode": expected["postcode"], "original_address_conflict": True,
           "raw_json": json.dumps(expected["raw_values"]), "resolution_method": "unchanged"}
    return tmp_path, config, pd.DataFrame([row])


@pytest.mark.parametrize("change", ["missing_way", "missing_node", "duplicate_node", "node_coordinate", "tags", "node_order"])
def test_mapped_landmark_requires_complete_original_geometry_and_tags(mapped_landmark_fixture, change):
    root, config, records = mapped_landmark_fixture
    reference = config["resolutions"][0]["corroborating"]
    filename = reference["file"]
    xml = ET.parse(root / filename).getroot()
    way = next(item for item in xml.findall("way") if item.get("id") == "737228454")
    node = next(item for item in xml.findall("node") if item.get("id") == reference["node_refs"][0])
    if change == "missing_way":
        xml.remove(way)
    elif change == "missing_node":
        xml.remove(node)
    elif change == "duplicate_node":
        xml.append(deepcopy(node))
    elif change == "node_coordinate":
        node.set("lat", "-31.0")
    elif change == "tags":
        next(t for t in way.findall("tag") if t.get("k") == "amenity").set("v", "charging_station")
    else:
        way.findall("nd")[0].set("ref", reference["node_refs"][1])
    ET.ElementTree(xml).write(root / filename, encoding="utf-8")
    rebind_fixture(root, config, filename)
    issues = []
    with pytest.raises(ValueError, match="Reviewed landmark"):
        apply_reviewed_resolutions(records, issues, root=root, config=config)
    assert not issues and records.address_conflict.all()


@pytest.mark.parametrize("bearing,distance,error", [
    (258, 10, "distance/direction"), (80, 76, "distance/direction"), (251, 80, "street corridor"),
])
def test_mapped_landmark_checks_relative_position_and_road_corridor(mapped_landmark_fixture, bearing, distance, error):
    from ev_pipeline.augment import GEOD
    root, config, records = mapped_landmark_fixture
    filename = config["resolutions"][0]["coordinate"]["file"]
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    lon, lat, _ = GEOD.fwd(151.59330287820373, -30.98287004334803, bearing, distance)
    data["AddressInfo"].update({"Longitude": lon, "Latitude": lat})
    (root / filename).write_text(json.dumps(data), encoding="utf-8")
    rebind_fixture(root, config, filename)
    with pytest.raises(ValueError, match=error):
        apply_reviewed_resolutions(records, [], root=root, config=config)


@pytest.mark.parametrize("field", ["address_source_file", "supporting_address_source_file"])
def test_mapped_landmark_cannot_replace_missing_official_site_evidence(mapped_landmark_fixture, field):
    root, config, records = mapped_landmark_fixture
    (root / config["resolutions"][0][field]).unlink()
    with pytest.raises(FileNotFoundError, match="Reviewed evidence missing"):
        apply_reviewed_resolutions(records, [], root=root, config=config)


def test_mapped_landmark_is_never_labelled_same_operator_charger(mapped_landmark_fixture):
    root, config, records = mapped_landmark_fixture
    # A caller-supplied role cannot override the actual evidence kind.
    config["resolutions"][0]["corroborating_role"] = "same_operator_charger"
    result, audit = apply_reviewed_resolutions(records, [], root=root, config=config)
    assert not result.address_conflict.any()
    assert audit.iloc[0].corroborating_role == "mapped_landmark"
    config["resolutions"][0]["corroborating"]["kind"] = "kml"
    with pytest.raises(ValueError, match="KML is not the published map"):
        apply_reviewed_resolutions(records, [], root=root, config=config)
