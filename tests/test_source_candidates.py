"""Candidate retrieval uses simulated HTTP and isolated project directories."""
from hashlib import sha256
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from ev_pipeline import acquire
from scripts import stage_source_candidates as stage


CSV_URL = "https://example.test/ev_20260909.csv"
PDF_URL = "https://example.test/metadata.pdf"
BOUNDARY_URL = "https://example.test/SA4_2026_AUST_SHP_GDA2020.zip"
MAP_URL = "https://www.google.com/maps/d/kml?mid=candidate-map&forcekml=1"
CURRENT_RESOURCE_ID = "7bbb6461-e52d-4fe7-ace4-a15c30198de0"
HISTORICAL_RESOURCE_ID = "66a7ef4c-aece-4732-bc22-e95fc8613522"


def encoded(value):
    return json.dumps(value).encode()


@pytest.fixture
def candidate_fixture(tmp_path, monkeypatch):
    catalogue = {"success": True, "result": {"resources": [
        {"id": "new-csv", "name": "new observation", "format": "CSV", "url": CSV_URL},
        {"format": "PDF", "url": PDF_URL},
    ]}}
    osm = {"osm3s": {"timestamp_osm_base": "2026-09-08T00:00:00Z"}, "elements": []}
    payloads = {
        stage.TFNSW: encoded(catalogue), CSV_URL: b"Station_name,Station_address\nExample,1 Road\n",
        PDF_URL: b"%PDF-1.4 synthetic metadata", stage.ABS: f'<a href="{BOUNDARY_URL}">SA4</a>'.encode(),
        BOUNDARY_URL: b"PK synthetic boundary", stage.OSM_URL: encoded(osm), stage.JOLT_URL: b"JOLT synthetic page",
        stage.NRMA_URL: b'<iframe src="https://www.google.com/maps/d/embed?mid=candidate-map"></iframe>',
        MAP_URL: b'<kml xmlns="http://www.opengis.net/kml/2.2"/>',
    }
    urls = dict(zip(stage.SOURCES, [stage.TFNSW, CSV_URL, PDF_URL, stage.ABS, BOUNDARY_URL,
                                   stage.OSM_URL, stage.JOLT_URL, stage.NRMA_URL, MAP_URL]))
    for name, (_, current_name) in stage.SOURCES.items():
        path = tmp_path / "data/raw" / current_name
        path.parent.mkdir(parents=True, exist_ok=True)
        content = payloads[urls[name]]
        path.write_bytes(content)
        path.with_name(path.name + ".meta.json").write_bytes(encoded({
            "url": urls[name], "sha256": sha256(content).hexdigest(), "bytes": len(content),
            "retrieved_at_utc": "2026-09-08T00:00:00Z"}))
    config = {
        "sources": [{"file": "data/raw/" + stage.SOURCES[name][1],
                     "url": urls[name],
                     "sha256": sha256(payloads[urls[name]]).hexdigest()} for name in ["osm", "nrma_page", "nrma_map"]],
        "map_publication": {"source_file": "data/raw/nrma_network.html", "map_file": "data/raw/nrma_stations.kml"},
        "resolutions": [{"record_id": f"reviewed-{i}", "coordinate": {"file": "data/raw/osm_chargers.json"},
                         "corroborating": {"file": "data/raw/nrma_stations.kml"}} for i in range(4)],
    }
    for name, content in {"config/reviewed_resolutions.json": encoded(config), "outputs/validation.json": b"existing validation",
                          "config/reviewed_match_exceptions.json": encoded({"exceptions": [{
                              "review_id": "Dan-venue", "record_id": "Dan-source-record",
                              "source_snapshot": {"file": "data/raw/ev_20251216.csv", "sha256": sha256(payloads[CSV_URL]).hexdigest()},
                              "external_snapshot": {"file": "data/raw/ocm/OCM-190706.json", "sha256": "a" * 64},
                              "evidence": {"file": "data/raw/reviewed/dan-page.txt", "sha256": "b" * 64}}]}),
                          "config/reviewed_identities.json": encoded({"source_file": "data/raw/ev_20251216.csv",
                              "groups": [{"review_id": name} for name in ["RI01", "RI02", "RI03"]]}),
                          "data/processed/current.csv": b"existing output", "submission/current.zip": b"existing ZIP"}.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    protected = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    requested = []

    class Response:
        headers = {"ETag": '"candidate"'}

        def __init__(self, url):
            self.url = url

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            value = payloads[self.url]
            if isinstance(value, Exception):
                yield b"interrupted prefix"
                raise value
            yield value

    class Session:
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            assert url in payloads, "Unexpected network target"
            requested.append(url)
            return Response(url)

    monkeypatch.setattr(acquire, "session", Session)

    def forbidden(*args, **kwargs):
        raise AssertionError("Candidate staging must not run the active pipeline")

    monkeypatch.setattr(acquire, "acquire", forbidden)
    return SimpleNamespace(root=tmp_path, payloads=payloads, catalogue=catalogue, osm=osm,
                           requested=requested, protected=protected, config=config)


def assert_protected_unchanged(fixture):
    for path, content in fixture.protected.items():
        assert path.read_bytes() == content
    current_files = {path for path in fixture.root.rglob("*") if path.is_file()
                     and ".runtime" not in path.relative_to(fixture.root).parts}
    assert current_files == set(fixture.protected)


def test_candidate_downloads_all_dynamic_sources_with_manifests_without_touching_active_project(candidate_fixture):
    fixture = candidate_fixture
    report_path = stage.stage_candidates("2026-09-09-a", root=fixture.root)
    report = json.loads(report_path.read_text())
    assert report_path == fixture.root / ".runtime/source_candidates/2026-09-09-a/candidate_report.json"
    assert report["complete"] is True and report["status"] == "downloaded_for_review"
    assert len(fixture.requested) == len(report["sources"]) == 9
    assert report["ocm"] == {"refreshed": False, "retained_commit": stage.OCM_REVISION}
    assert report["tfnsw_selected_resource"]["url"] == CSV_URL
    assert report["sources"]["tfnsw_csv"]["candidate_file"] == "data/raw/tfnsw_chargers.csv"
    assert report["sources"]["tfnsw_csv"]["identity_review_groups"] == ["RI01", "RI02", "RI03"]
    assert report["sources"]["tfnsw_csv"]["matching_review_dependencies"][0]["snapshot_status"] == "unchanged_pinned_bytes"
    for entry in report["sources"].values():
        assert entry["status"] == "downloaded" and entry["comparison"] == "identical"
        assert entry["regional_review_dependencies"] == []  # Older fixtures need no regional configuration.
        source = report_path.parent / entry["candidate_file"]
        meta = json.loads((report_path.parent / entry["manifest_file"]).read_text())
        assert sha256(source.read_bytes()).hexdigest() == meta["sha256"] == entry["sha256"]
        assert meta["url"] == entry["requested_url"] and meta["bytes"] == source.stat().st_size
    assert_protected_unchanged(fixture)


def test_response_timestamp_change_is_staged_and_identifies_all_reviewed_dependents(candidate_fixture):
    fixture = candidate_fixture
    fixture.osm["osm3s"]["timestamp_osm_base"] = "2026-09-09T00:00:00Z"
    fixture.payloads[stage.OSM_URL] = encoded(fixture.osm)
    report = json.loads(stage.stage_candidates("new-time", root=fixture.root).read_text())
    entry = report["sources"]["osm"]
    assert entry["comparison"] == "changed"
    assert entry["review_evidence_status"] == "new_bytes_require_review_before_adoption"
    assert entry["sha256"] != entry["review_pinned_sha256"]
    assert entry["reviewed_dependencies"] == [{"record_id": f"reviewed-{i}", "roles": ["coordinate"]} for i in range(4)]
    assert len(report["sources"]["nrma_page"]["reviewed_dependencies"]) == 4
    assert report["sources"]["nrma_map"]["reviewed_dependencies"][0]["roles"] == ["corroborating"]
    assert_protected_unchanged(fixture)


def test_same_map_bytes_at_a_new_published_url_still_require_review(candidate_fixture):
    fixture = candidate_fixture
    new_url = "https://www.google.com/maps/d/kml?mid=new-map&forcekml=1"
    fixture.payloads[stage.NRMA_URL] = b'<iframe src="https://www.google.com/maps/d/embed?mid=new-map"></iframe>'
    fixture.payloads[new_url] = fixture.payloads[MAP_URL]
    report = json.loads(stage.stage_candidates("new-map-url", root=fixture.root).read_text())
    entry = report["sources"]["nrma_map"]
    assert entry["comparison"] == "identical"
    assert entry["review_source_url_changed"] is True
    assert entry["review_evidence_status"] == "new_source_url_requires_review_before_adoption"
    assert entry["requested_url"] == new_url and entry["review_pinned_url"] == MAP_URL
    assert_protected_unchanged(fixture)


def test_changed_source_csv_reports_matching_exception_dependency_and_identity_review_groups(candidate_fixture):
    fixture = candidate_fixture
    fixture.payloads[CSV_URL] += b"Additional unrelated source row,2 Road\n"
    report = json.loads(stage.stage_candidates("changed-source", root=fixture.root).read_text())
    entry = report["sources"]["tfnsw_csv"]
    assert entry["comparison"] == "changed"
    assert entry["matching_review_dependencies"] == [{
        "review_id": "Dan-venue", "record_id": "Dan-source-record", "role": "source_snapshot",
        "pinned_sha256": sha256(fixture.protected[fixture.root / "data/raw/ev_20251216.csv"]).hexdigest(),
        "snapshot_status": "new_bytes_require_review_before_adoption"}]
    assert entry["identity_review_groups"] == ["RI01", "RI02", "RI03"]
    assert report["complete"] is True  # Staging does not apply or invalidate any reviewed decision.
    assert len(fixture.requested) == 9  # No fixed OCM or reviewed venue document is re-fetched.
    assert_protected_unchanged(fixture)


@pytest.fixture
def regional_candidate_fixture(candidate_fixture):
    fixture = candidate_fixture
    evidence = [
        ("data/raw/ev_20251216.csv", CSV_URL, "source_record"),
        ("data/raw/SA4_2026_AUST_SHP_GDA2020.zip", BOUNDARY_URL, "statistical_boundary"),
        ("data/raw/nrma_network.html", stage.NRMA_URL, "operator_publication"),
        ("data/raw/nrma_stations.kml", MAP_URL, "operator_locality"),
    ]
    config = {
        "sources": [{"file": filename, "url": url, "sha256": sha256(fixture.payloads[url]).hexdigest()}
                    for filename, url, _ in evidence],
        "reviews": [
            {"review_id": "regional-Braidwood", "record_id": "Braidwood-source",
             "evidence": [{"source_file": filename, "role": role} for filename, _, role in evidence]},
            {"review_id": "regional-Walgett", "record_id": "Walgett-source",
             "evidence": [{"source_file": filename, "role": role} for filename, _, role in evidence]},
        ],
    }
    path = fixture.root / "config/reviewed_regions.json"
    path.write_bytes(encoded(config))
    fixture.protected[path] = path.read_bytes()
    return fixture


@pytest.mark.parametrize("name,url,role", [
    ("tfnsw_csv", CSV_URL, "source_record"),
    ("abs_boundary", BOUNDARY_URL, "statistical_boundary"),
])
def test_regional_reviews_are_identified_when_candidate_source_or_boundary_changes(regional_candidate_fixture, name, url, role):
    fixture = regional_candidate_fixture
    original = fixture.payloads[url]
    fixture.payloads[url] += b"additional candidate observation"
    report = json.loads(stage.stage_candidates("regional-change", root=fixture.root).read_text())
    changed = report["sources"][name]
    assert changed["comparison"] == "changed"
    dependencies = changed["regional_review_dependencies"]
    assert {(item["review_id"], item["record_id"]) for item in dependencies} == {
        ("regional-Braidwood", "Braidwood-source"), ("regional-Walgett", "Walgett-source")}
    for item in dependencies:
        assert item["role"] == role
        assert item["pinned_url"] == url and item["pinned_sha256"] == sha256(original).hexdigest()
        assert item["bytes_changed"] is True and item["source_url_changed"] is False
        assert item["requires_review"] is True
        assert item["snapshot_status"] == "new_bytes_require_review_before_adoption"
    assert report["sources"]["osm"]["regional_review_dependencies"] == []
    assert all(not item["requires_review"] for item in report["sources"]["nrma_map"]["regional_review_dependencies"])
    assert report["complete"] is True and len(fixture.requested) == 9
    assert_protected_unchanged(fixture)


def test_regional_pins_distinguish_unchanged_sources_from_same_bytes_at_a_new_operator_url(regional_candidate_fixture):
    fixture = regional_candidate_fixture
    report = json.loads(stage.stage_candidates("regional-unchanged", root=fixture.root).read_text())
    for name in ["tfnsw_csv", "abs_boundary", "nrma_page", "nrma_map"]:
        dependencies = report["sources"][name]["regional_review_dependencies"]
        assert len(dependencies) == 2
        assert all(item["snapshot_status"] == "unchanged_pinned_bytes_and_url" for item in dependencies)
        assert all(not item["requires_review"] and not item["bytes_changed"]
                   and not item["source_url_changed"] for item in dependencies)
    new_url = "https://www.google.com/maps/d/kml?mid=regional-new-map&forcekml=1"
    fixture.payloads[stage.NRMA_URL] = b'<iframe src="https://www.google.com/maps/d/embed?mid=regional-new-map"></iframe>'
    fixture.payloads[new_url] = fixture.payloads[MAP_URL]
    moved = json.loads(stage.stage_candidates("regional-republished", root=fixture.root).read_text())
    assert moved["sources"]["nrma_map"]["comparison"] == "identical"
    for item in moved["sources"]["nrma_map"]["regional_review_dependencies"]:
        assert item["pinned_url"] == MAP_URL
        assert item["bytes_changed"] is False and item["source_url_changed"] is True
        assert item["requires_review"] is True
        assert item["snapshot_status"] == "new_source_url_requires_review_before_adoption"
    assert all(item["bytes_changed"] and item["requires_review"]
               for item in moved["sources"]["nrma_page"]["regional_review_dependencies"])
    assert moved["complete"] is True and len(fixture.requested) == 18
    assert_protected_unchanged(fixture)


@pytest.mark.parametrize("csv_count", [0, 2])
def test_csv_resource_ambiguity_fails_with_report_without_choosing_a_version(candidate_fixture, csv_count):
    fixture = candidate_fixture
    resources = [fixture.catalogue["result"]["resources"][1]]
    resources.extend({"format": "CSV", "url": f"https://example.test/version-{i}.csv"} for i in range(csv_count))
    fixture.payloads[stage.TFNSW] = encoded({"success": True, "result": {"resources": resources}})
    with pytest.raises(ValueError, match="exactly one candidate CSV"):
        stage.stage_candidates("ambiguous", root=fixture.root)
    report = json.loads((fixture.root / ".runtime/source_candidates/ambiguous/candidate_report.json").read_text())
    assert report["complete"] is False and report["status"] == "failed"
    assert report["error"]["stage"] == "discover_tfnsw_csv"
    assert fixture.requested == [stage.TFNSW]
    assert_protected_unchanged(fixture)


@pytest.mark.parametrize("name,url", [("osm", stage.OSM_URL), ("nrma_map", MAP_URL)])
def test_interrupted_candidate_has_failure_report_and_only_complete_provenance_pairs(candidate_fixture, name, url):
    fixture = candidate_fixture
    fixture.payloads[url] = requests.ConnectionError("stream interrupted")
    with pytest.raises(requests.ConnectionError, match="interrupted"):
        stage.stage_candidates("interrupted", root=fixture.root)
    target = fixture.root / ".runtime/source_candidates/interrupted"
    report = json.loads((target / "candidate_report.json").read_text())
    assert report["complete"] is False and report["error"]["stage"] == name
    assert not (target / report["sources"][name]["candidate_file"]).exists()
    assert not list(target.rglob("*.part"))
    for path in (target / "data/raw").rglob("*"):
        if path.is_file() and not path.name.endswith(".meta.json"):
            assert path.with_name(path.name + ".meta.json").is_file()
    assert_protected_unchanged(fixture)


@pytest.mark.parametrize("label", ["", "../other", "nested/path", "nested\\path", "C:\\raw", "a" * 65, "CON"])
def test_invalid_candidate_labels_fail_before_any_download(candidate_fixture, label):
    with pytest.raises(ValueError, match="Label must"):
        stage.stage_candidates(label, root=candidate_fixture.root)
    assert candidate_fixture.requested == []
    assert not (candidate_fixture.root / ".runtime").exists()
    assert_protected_unchanged(candidate_fixture)


def test_existing_candidate_directory_is_never_overwritten_or_resumed(candidate_fixture):
    fixture = candidate_fixture
    target = fixture.root / ".runtime/source_candidates/existing"
    target.mkdir(parents=True)
    old_report = target / "candidate_report.json"
    old_report.write_bytes(b"prior complete or failed candidate")
    with pytest.raises(FileExistsError):
        stage.stage_candidates("existing", root=fixture.root)
    assert old_report.read_bytes() == b"prior complete or failed candidate"
    assert fixture.requested == []
    assert_protected_unchanged(fixture)


def test_new_csv_candidate_does_not_relax_default_assignment_version_selection(candidate_fixture):
    data = candidate_fixture.catalogue
    assert stage.tfnsw_csv_resource(data, assignment_version=False)["url"] == CSV_URL
    with pytest.raises(ValueError, match="December 2025 CSV"):
        acquire.tfnsw_csv_resource(data)


def test_partial_overpass_response_prevents_candidate_completion(candidate_fixture):
    fixture = candidate_fixture
    fixture.payloads[stage.OSM_URL] = encoded({"elements": [], "remark": "runtime error: query timed out"})
    with pytest.raises(ValueError, match="Overpass returned a partial/error"):
        stage.stage_candidates("overpass-error", root=fixture.root)
    report = json.loads((fixture.root / ".runtime/source_candidates/overpass-error/candidate_report.json").read_text())
    assert report["complete"] is False and report["error"]["stage"] == "check_osm_response"
    assert report["sources"]["osm"]["status"] == "downloaded"  # Preserve the source error response for inspection.
    assert report["sources"]["jolt"]["status"] == "not_downloaded"
    assert_protected_unchanged(fixture)


@pytest.fixture
def archived_catalogue():
    # Use the real supplied directory, which contains both current and old CSVs.
    return json.loads((stage.ROOT / "data/raw/tfnsw_catalog.json").read_text(encoding="utf-8"))


def serve_archived_catalogue(fixture, catalogue):
    fixture.payloads[stage.TFNSW] = encoded(catalogue)
    for resource in catalogue["result"]["resources"]:
        if resource["format"] == "CSV":
            fixture.payloads[resource["url"]] = (b"Archived station CSV for comparison\n"
                                                if resource["id"] == HISTORICAL_RESOURCE_ID else fixture.payloads[CSV_URL])
        elif resource["format"] == "PDF":
            fixture.payloads[resource["url"]] = fixture.payloads[PDF_URL]


def test_real_archived_catalogue_stages_the_unmarked_csv_without_the_explicit_historical_resource(candidate_fixture, archived_catalogue):
    fixture = candidate_fixture
    serve_archived_catalogue(fixture, archived_catalogue)
    report = json.loads(stage.stage_candidates("real-catalogue", root=fixture.root).read_text())
    assert report["complete"] is True
    assert report["tfnsw_selected_resource"]["id"] == CURRENT_RESOURCE_ID
    assert report["tfnsw_selection"]["method"] == "official_current_historical_labels"
    assert report["tfnsw_selection"]["official_label_status"] == "unmarked"
    historical = next(r for r in archived_catalogue["result"]["resources"] if r["id"] == HISTORICAL_RESOURCE_ID)
    assert historical["url"] not in fixture.requested
    assert acquire.tfnsw_csv_resource(archived_catalogue)["id"] == CURRENT_RESOURCE_ID
    assert_protected_unchanged(fixture)


def test_explicit_historical_resource_preserves_its_publisher_description_and_selection_reason(candidate_fixture, archived_catalogue):
    fixture = candidate_fixture
    serve_archived_catalogue(fixture, archived_catalogue)
    report = json.loads(stage.stage_candidates("historical-comparison", root=fixture.root,
                                              tfnsw_resource_id=HISTORICAL_RESOURCE_ID).read_text())
    assert report["complete"] is True
    assert report["tfnsw_requested_resource_id"] == HISTORICAL_RESOURCE_ID
    assert report["tfnsw_selected_resource"]["id"] == HISTORICAL_RESOURCE_ID
    assert "no longer current" in report["tfnsw_selected_resource"]["description"]
    assert report["tfnsw_selection"]["method"] == "explicit_resource_id"
    assert report["tfnsw_selection"]["official_label_status"] == "historical"
    assert "not a current or assignment-approved replacement" in report["tfnsw_selection"]["note"]
    assert "documentation is contextual" in report["tfnsw_selection"]["note"]
    assert_protected_unchanged(fixture)


@pytest.mark.parametrize("historical_pdf", [True, False])
def test_full_staging_applies_publisher_priority_to_multiple_metadata_pdfs(candidate_fixture, archived_catalogue, historical_pdf):
    fixture = candidate_fixture
    catalogue = deepcopy(archived_catalogue)
    original = next(r for r in catalogue["result"]["resources"] if r["format"] == "PDF")
    other = dict(original, id="another-document", url="https://example.test/other-metadata.pdf",
                 name="Historical documentation" if historical_pdf else "Another documentation resource",
                 description="Published for historic purposes only." if historical_pdf else "Effective 20 April 2026")
    catalogue["result"]["resources"].append(other)
    serve_archived_catalogue(fixture, catalogue)
    if historical_pdf:
        report = json.loads(stage.stage_candidates("pdf-priority", root=fixture.root).read_text())
        assert report["complete"] is True
        assert report["tfnsw_selected_metadata"]["id"] == original["id"]
        assert other["url"] not in fixture.requested
        assert len(fixture.requested) == 9
    else:
        with pytest.raises(ValueError, match="metadata PDF at the preferred nonhistorical priority"):
            stage.stage_candidates("pdf-priority", root=fixture.root)
        report = json.loads((fixture.root / ".runtime/source_candidates/pdf-priority/candidate_report.json").read_text())
        assert report["complete"] is False and report["error"]["stage"] == "discover_tfnsw_metadata"
        assert original["url"] not in fixture.requested and other["url"] not in fixture.requested
    assert_protected_unchanged(fixture)


@pytest.mark.parametrize("case,error", [("absent", "found 0"), ("duplicate", "found 2"), ("non-csv", "not a CSV")])
def test_invalid_explicit_ids_fail_without_falling_back_to_another_resource(candidate_fixture, archived_catalogue, case, error):
    fixture = candidate_fixture
    catalogue = deepcopy(archived_catalogue)
    if case == "absent":
        resource_id = "not-an-existing-resource"
    elif case == "duplicate":
        resource_id = CURRENT_RESOURCE_ID
        catalogue["result"]["resources"].append(deepcopy(next(r for r in catalogue["result"]["resources"] if r["id"] == resource_id)))
    else:
        resource_id = next(r["id"] for r in catalogue["result"]["resources"] if r["format"] == "PDF")
    serve_archived_catalogue(fixture, catalogue)
    with pytest.raises(ValueError, match=error):
        stage.stage_candidates("invalid-id", root=fixture.root, tfnsw_resource_id=resource_id)
    report = json.loads((fixture.root / ".runtime/source_candidates/invalid-id/candidate_report.json").read_text())
    assert report["complete"] is False
    assert report["tfnsw_requested_resource_id"] == resource_id
    assert report["error"]["stage"] == "discover_tfnsw_csv"
    assert fixture.requested == [stage.TFNSW]
    assert_protected_unchanged(fixture)


def test_publisher_current_label_precedes_an_unmarked_resource_regardless_of_filename_date():
    current = {"id": "official-current", "name": "EV Charging Locations - Current", "format": "CSV",
               "url": "https://example.test/ev_20200101.csv", "state": "active"}
    unmarked = {"id": "unmarked", "name": "EV data", "format": "CSV",
                "url": "https://example.test/ev_20991231.csv", "state": "active"}
    catalogue = {"success": True, "result": {"resources": [unmarked, current]}}
    assert acquire.tfnsw_csv_resource(catalogue, assignment_version=False)["id"] == "official-current"
    catalogue["result"]["resources"].append(dict(current, id="second-current"))
    with pytest.raises(ValueError, match="preferred nonhistorical priority"):
        acquire.tfnsw_csv_resource(catalogue, assignment_version=False)


def test_no_longer_current_marker_overrides_current_word_and_historical_only_requires_explicit_id():
    historical = {"id": "old", "name": "Current EV data", "description": "This dataset is no longer current.",
                  "format": "CSV", "url": CSV_URL, "state": "active"}
    catalogue = {"success": True, "result": {"resources": [historical]}}
    with pytest.raises(ValueError, match="exactly one candidate CSV"):
        acquire.tfnsw_csv_resource(catalogue, assignment_version=False)
    assert acquire.tfnsw_csv_resource(catalogue, assignment_version=False, resource_id="old") == historical


def test_explicit_id_cannot_override_frozen_assignment_selection(archived_catalogue):
    with pytest.raises(ValueError, match="only supported for candidate staging"):
        acquire.tfnsw_csv_resource(archived_catalogue, resource_id=HISTORICAL_RESOURCE_ID)


def test_candidate_cli_passes_the_explicit_resource_id(monkeypatch, tmp_path):
    received = []
    monkeypatch.setattr(stage.sys, "argv", ["stage_source_candidates.py", "--label", "named-version",
                                           "--tfnsw-resource-id", HISTORICAL_RESOURCE_ID])
    def staged(label, **kwargs):
        received.append((label, kwargs))
        return tmp_path / "candidate_report.json"
    monkeypatch.setattr(stage, "stage_candidates", staged)
    stage.main()
    assert received == [("named-version", {"tfnsw_resource_id": HISTORICAL_RESOURCE_ID})]
