# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
"""Exercise release gates against real small pytest runs and isolated raw files."""
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from scripts import package_release, verification_evidence as ve, verify_project

FINGERPRINT = "fixture-fingerprint"
MINI_TESTS = '''import pytest

@pytest.mark.parametrize("value", [1, 2], ids=["a::<tag>", "b & [bracket]"])
def test_values(value):
    assert value > 0

def test_always():
    assert True
'''


def mini_project(root, source=MINI_TESTS, conftest=None):
    for name in ("scripts", "tests", "outputs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "scripts/verification_evidence.py").write_bytes(Path(ve.__file__).read_bytes())
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (root / "tests/test_small.py").write_text(source, encoding="utf-8")
    if conftest is not None:
        (root / "tests/conftest.py").write_text(conftest, encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def recorded_suite(tmp_path_factory):
    root = mini_project(tmp_path_factory.mktemp("real-suite"))
    evidence = verify_project.run_tests(root, FINGERPRINT)
    return root, evidence


@pytest.fixture
def recorded_copy(tmp_path, recorded_suite):
    source, evidence = recorded_suite
    shutil.copytree(source / "outputs", tmp_path / "outputs")
    return tmp_path, deepcopy(evidence)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_real_suite_ignores_inherited_selection_and_plugins(tmp_path, monkeypatch):
    source = MINI_TESTS.replace("def test_always():\n    assert True",
                               "def test_always(project_fixture):\n    assert project_fixture == 42")
    conftest = "import pytest\n@pytest.fixture\ndef project_fixture():\n    return 42\n"
    root = mini_project(tmp_path, source, conftest)
    (root / "pytest.ini").write_text("[pytest]\naddopts = -k test_always\n", encoding="utf-8")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k test_always --lf --noconftest")
    monkeypatch.setenv("PYTEST_PLUGINS", "missing_external_plugin")
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "0")
    evidence = verify_project.run_tests(root, FINGERPRINT)
    assert evidence["tests"] == 3
    assert evidence["full_suite"]["collected"] == evidence["full_suite"]["executed"] == 3
    ve.validate_test_evidence(root, evidence, FINGERPRINT)
    report = json.loads((root / "outputs/test_report.json").read_text())
    assert len(report["collected_nodeids"]) == len(report["selected_nodeids"]) == 3
    assert report["deselected_nodeids"] == []


@pytest.mark.parametrize("root_conftest", [
    "collect_ignore = ['tests/test_omitted.py']\n",
    "raise RuntimeError('untracked root conftest must not load')\n",
])
def test_root_conftest_cannot_hide_tests_or_change_execution(tmp_path, root_conftest):
    root = mini_project(tmp_path, "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n")
    (root / "tests/test_omitted.py").write_text("def test_three():\n    assert True\n", encoding="utf-8")
    (root / "conftest.py").write_text(root_conftest, encoding="utf-8")
    evidence = verify_project.run_tests(root, FINGERPRINT)
    assert evidence["tests"] == evidence["full_suite"]["collected"] == 3
    ve.validate_test_evidence(root, evidence, FINGERPRINT)


def test_legitimate_added_test_is_counted_without_fixed_baseline(tmp_path):
    root = mini_project(tmp_path, MINI_TESTS + "\ndef test_added():\n    assert 2 + 2 == 4\n")
    assert verify_project.run_tests(root, FINGERPRINT)["tests"] == 4


@pytest.mark.parametrize("source,conftest", [
    (MINI_TESTS + "\ndef test_skip():\n    pytest.skip('not acceptable for release')\n", None),
    (MINI_TESTS + "\n@pytest.mark.xfail(reason='known failure')\ndef test_xfail():\n    assert False\n", None),
    (MINI_TESTS + "\n@pytest.mark.xfail(reason='unexpected pass')\ndef test_xpass():\n    assert True\n", None),
    (MINI_TESTS, "def pytest_collection_modifyitems(config, items):\n"
     "    removed = items.pop()\n    config.hook.pytest_deselected(items=[removed])\n"),
    (MINI_TESTS, "def pytest_collection_modifyitems(items):\n    items.pop()\n"),
    ("import pytest\npytest.skip('module skip', allow_module_level=True)\n", None),
    ("", None),
])
def test_real_partial_or_nonpassing_suite_is_rejected(tmp_path, source, conftest):
    root = mini_project(tmp_path, source, conftest)
    with pytest.raises((ValueError, RuntimeError)):
        verify_project.run_tests(root, FINGERPRINT)


def test_collection_skip_is_rejected_even_when_other_tests_pass(tmp_path):
    root = mini_project(tmp_path)
    (root / "tests/test_skipped_module.py").write_text(
        "import pytest\npytest.skip('module skipped', allow_module_level=True)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="collection_skipped"):
        verify_project.run_tests(root, FINGERPRINT)


def test_fingerprint_failure_revokes_success_and_removes_old_xml(tmp_path, monkeypatch):
    (tmp_path / "outputs").mkdir()
    evidence = tmp_path / "outputs/test_evidence.json"
    evidence.write_text('{"passed": true}', encoding="utf-8")
    (tmp_path / "outputs/tests.xml").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(verify_project, "ROOT", tmp_path)
    monkeypatch.setattr(verify_project, "sys", SimpleNamespace(stdout=SimpleNamespace(reconfigure=lambda **_: None)))

    def unavailable_inputs():
        raise OSError("missing fingerprint input")

    monkeypatch.setattr(verify_project, "project_fingerprint", unavailable_inputs)
    with pytest.raises(OSError, match="fingerprint"):
        verify_project.main()
    assert json.loads(evidence.read_text())["passed"] is False
    assert not (tmp_path / "outputs/tests.xml").exists()


def test_successful_process_cannot_reuse_stale_artifacts(recorded_copy, monkeypatch):
    root, _ = recorded_copy
    monkeypatch.setattr(verify_project.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""))
    with pytest.raises(FileNotFoundError):
        verify_project.run_tests(root, FINGERPRINT)
    assert not (root / "outputs/tests.xml").exists()
    assert not (root / "outputs/test_report.json").exists()


@pytest.mark.parametrize("attribute,value", [("tests", "-1"), ("tests", "true"), ("tests", "4"),
                                               ("errors", "1"), ("skipped", "1")])
def test_junit_counts_must_match_actual_passing_cases(recorded_copy, attribute, value):
    root, evidence = recorded_copy
    path = root / "outputs/tests.xml"
    xml = ET.parse(path)
    xml.getroot().find("testsuite").set(attribute, value)
    xml.write(path, encoding="utf-8")
    with pytest.raises(ValueError, match="JUnit"):
        ve.validate_test_evidence(root, evidence, FINGERPRINT)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown", "missing-id", "malformed", "empty"])
def test_junit_requires_exactly_one_case_per_reported_node(recorded_copy, mutation):
    root, evidence = recorded_copy
    path = root / "outputs/tests.xml"
    xml = ET.parse(path)
    suite = xml.getroot().find("testsuite")
    cases = suite.findall("testcase")
    if mutation == "missing":
        suite.remove(cases[0])
        suite.set("tests", "2")
    elif mutation == "duplicate":
        suite.append(deepcopy(cases[0]))
        suite.set("tests", "4")
    elif mutation == "unknown":
        cases[0].find("properties/property").set("value", "tests/test_missing.py::test_missing")
    elif mutation == "missing-id":
        cases[0].remove(cases[0].find("properties"))
    xml.write(path, encoding="utf-8")
    if mutation == "malformed":
        path.write_text("<invalid", encoding="utf-8")
    elif mutation == "empty":
        path.write_text("<testsuites/>", encoding="utf-8")
    with pytest.raises(ValueError, match="JUnit"):
        ve.validate_test_evidence(root, evidence, FINGERPRINT)


@pytest.mark.parametrize("mutation", ["missing-phase", "duplicate-phase", "unknown-phase", "skip",
                                      "xfail", "missing-selected", "duplicate-collected", "bad-count",
                                      "bool-count", "run-id", "fingerprint"])
def test_report_must_prove_complete_collection_and_execution(recorded_copy, mutation):
    root, evidence = recorded_copy
    path = root / "outputs/test_report.json"
    report = json.loads(path.read_text())
    if mutation == "missing-phase":
        report["reports"].pop()
    elif mutation == "duplicate-phase":
        report["reports"].append(report["reports"][0])
    elif mutation == "unknown-phase":
        report["reports"][0]["nodeid"] = "unmatched"
    elif mutation == "skip":
        report["reports"][0]["outcome"] = "skipped"
    elif mutation == "xfail":
        report["reports"][0]["wasxfail"] = True
    elif mutation == "missing-selected":
        report["selected_nodeids"].pop()
    elif mutation == "duplicate-collected":
        report["collected_nodeids"].append(report["collected_nodeids"][0])
    elif mutation == "bad-count":
        report["collection_errors"] = -1
    elif mutation == "bool-count":
        report["collection_errors"] = False
    elif mutation == "run-id":
        report["run_id"] = "different-run"
    elif mutation == "fingerprint":
        report["project_fingerprint"] = "different-inputs"
    write_json(path, report)
    with pytest.raises(ValueError):
        ve.validate_test_evidence(root, evidence, FINGERPRINT)


@pytest.mark.parametrize("mutation", ["legacy", "false", "truthy", "bool-tests", "negative-tests",
                                      "bool-summary", "missing-summary", "hash"])
def test_packager_rejects_incomplete_or_malformed_test_evidence(recorded_copy, mutation):
    root, evidence = recorded_copy
    if mutation == "legacy":
        evidence = {"passed": True, "tests": 1, "project_fingerprint": FINGERPRINT}
    elif mutation == "false":
        evidence["passed"] = False
    elif mutation == "truthy":
        evidence["passed"] = 1
    elif mutation == "bool-tests":
        evidence["tests"] = True
    elif mutation == "negative-tests":
        evidence["tests"] = -1
    elif mutation == "bool-summary":
        evidence["full_suite"]["skipped"] = False
    elif mutation == "missing-summary":
        del evidence["full_suite"]
    elif mutation == "hash":
        evidence["test_run"]["junit_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        ve.validate_test_evidence(root, evidence, FINGERPRINT)


def release_project(root, monkeypatch):
    monkeypatch.setattr(package_release, "ROOT", root)
    for name in (*package_release.ROOT_FILES, "sql/schema.sql", "data/processed/ev_chargers.duckdb"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    body = root / "data/raw/nested/source.json"
    body.parent.mkdir(parents=True)
    body.write_bytes(b"{}")
    manifest = body.with_name(body.name + ".meta.json")
    write_json(manifest, {"sha256": sha256(b"{}").hexdigest(), "bytes": 2,
                          "url": "https://example.test/source", "retrieved_at_utc": "2026-09-30T00:00:00+00:00"})
    return body, manifest


@pytest.mark.parametrize("missing", ["body", "manifest"])
def test_release_requires_raw_pairs_in_both_directions(tmp_path, monkeypatch, missing):
    body, manifest = release_project(tmp_path, monkeypatch)
    (body if missing == "body" else manifest).unlink()
    with pytest.raises(ValueError, match="source/manifest pair missing"):
        package_release.release_files()


def test_release_validates_content_and_safely_excludes_partial_file(tmp_path, monkeypatch):
    body, manifest = release_project(tmp_path, monkeypatch)
    partial = body.with_name("unpaired.part")
    partial.write_bytes(b"incomplete download")
    selected = package_release.release_files()
    assert body in selected and manifest in selected and partial not in selected
    body.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="snapshot content mismatch"):
        package_release.release_files()


@pytest.mark.parametrize("key,value", [("bytes", True), ("bytes", -1), ("sha256", "x" * 64)])
def test_release_rejects_malformed_manifest_metadata(tmp_path, monkeypatch, key, value):
    _, manifest = release_project(tmp_path, monkeypatch)
    metadata = json.loads(manifest.read_text())
    metadata[key] = value
    write_json(manifest, metadata)
    with pytest.raises(ValueError, match="Invalid raw manifest"):
        package_release.release_files()


def test_orphan_added_after_success_blocks_current_evidence(recorded_copy, monkeypatch):
    root, evidence = recorded_copy
    body, _ = release_project(root, monkeypatch)
    write_json(root / "outputs/test_evidence.json", evidence)
    repro = {"project_fingerprint": FINGERPRINT, "tables": {}, "csv_outputs": {}, "schema": {},
             "validation_report_sha256": "report", "table_content_identical": True,
             "csv_outputs_identical": True, "schema_identical": True, "validation_report_identical": True}
    write_json(root / "outputs/reproducibility.json", repro)
    monkeypatch.setattr(package_release, "project_fingerprint", lambda: FINGERPRINT)
    monkeypatch.setattr(package_release, "snapshots", lambda: None)
    for name in ("table_hashes", "file_hashes", "schema_hashes"):
        monkeypatch.setattr(package_release, name, lambda: {})
    monkeypatch.setattr(package_release, "validation_hash", lambda: "report")
    monkeypatch.setattr(package_release, "connect", lambda _: nullcontext(None))
    monkeypatch.setattr(package_release, "validate", lambda _: {
        "integrity_passed": True, "coverage": {"site_scope_target_met": True}})
    assert package_release.verified_evidence()[1] == evidence
    body.with_name("late-orphan.json").write_bytes(b"not in the manifest fingerprint")
    with pytest.raises(ValueError, match="source/manifest pair missing"):
        package_release.verified_evidence()
