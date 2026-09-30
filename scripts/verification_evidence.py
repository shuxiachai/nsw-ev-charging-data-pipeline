# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
"""Collect and verify full-suite evidence; also validate selected raw snapshots.

Loaded explicitly as a pytest plugin by verify_project. This file is covered by
the project fingerprint, as are the tests, pytest configuration and dependencies.
"""
from collections import Counter
from hashlib import sha256
import json
import re
import xml.etree.ElementTree as ET

import pytest

SCHEMA_VERSION = 2
REPORT_NAME = "test_report.json"
NODEID_PROPERTY = "release_nodeid"
IGNORED_SUFFIXES = {".pyc", ".part", ".wal", ".building"}
_report = None


def included_file(path):
    return "__pycache__" not in path.parts and path.suffix.lower() not in IGNORED_SUFFIXES


def verify_raw_pairs(root, paths=None):
    """Check both directions of the exact selected raw file set and its bytes."""
    raw = root / "data/raw"
    selected = set(paths if paths is not None else
                   (p for p in raw.rglob("*") if p.is_file() and included_file(p)))
    selected = {p for p in selected if p.is_relative_to(raw)}
    if not selected:
        raise ValueError("No raw source/manifest pairs selected")
    for path in sorted(selected):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or unsafe raw file: {path}")
        companion = path.with_name(path.name.removesuffix(".meta.json") if path.name.endswith(".meta.json")
                                   else path.name + ".meta.json")
        if companion not in selected:
            raise ValueError(f"Raw source/manifest pair missing: {companion}")
    for path in sorted(selected):
        if not path.name.endswith(".meta.json"):
            continue
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError(f"Invalid raw manifest: {path}")
        size = metadata.get("bytes")
        digest = metadata.get("sha256")
        if type(size) is not int or size < 0 or not is_digest(digest):
            raise ValueError(f"Invalid raw manifest bytes/sha256: {path}")
        body = path.with_name(path.name.removesuffix(".meta.json")).read_bytes()
        if len(body) != size or sha256(body).hexdigest() != digest.lower():
            raise ValueError(f"Raw snapshot content mismatch: {path}")


def is_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def strict_count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid non-negative integer evidence: {label}")
    return value


def nodeids(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError(f"Invalid node IDs: {label}")
    if len(set(value)) != len(value):
        raise ValueError(f"Duplicate node IDs: {label}")
    return value


def validate_run_report(report_path, junit_path, fingerprint, run_id):
    """Accept only one successful setup/call/teardown and JUnit case per item."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (not isinstance(report, dict) or type(report.get("schema_version")) is not int
            or report["schema_version"] != SCHEMA_VERSION or report.get("project_fingerprint") != fingerprint
            or report.get("run_id") != run_id or report.get("scope") != "tests"
            or report.get("config") != "pytest.ini"):
        raise ValueError("Test report schema, run, scope or fingerprint mismatch")
    collected = nodeids(report.get("collected_nodeids"), "collected")
    selected = nodeids(report.get("selected_nodeids"), "selected")
    selected_set = set(selected)
    deselected = nodeids(report.get("deselected_nodeids"), "deselected")
    if not collected or set(collected) != selected_set or deselected:
        raise ValueError("Full-suite selection required; empty, missing or deselected tests")
    for key in ("exitstatus", "collection_errors", "collection_skipped"):
        if strict_count(report.get(key), key) != 0:
            raise ValueError(f"Test collection or execution did not pass: {key}")
    phases = report.get("reports")
    if not isinstance(phases, list):
        raise ValueError("Missing test execution reports")
    actual = Counter()
    for phase in phases:
        if (not isinstance(phase, dict) or not isinstance(phase.get("nodeid"), str)
                or phase["nodeid"] not in selected_set
                or phase.get("when") not in ("setup", "call", "teardown")
                or phase.get("outcome") != "passed" or phase.get("wasxfail") is not False):
            raise ValueError("Unmatched, failed, skipped or xfail test execution report")
        actual[(phase["nodeid"], phase["when"])] += 1
    expected = Counter((item, phase) for item in selected for phase in ("setup", "call", "teardown"))
    if actual != expected:
        raise ValueError("Missing or duplicate test execution reports")
    try:
        xml = ET.parse(junit_path).getroot()
    except ET.ParseError as exc:
        raise ValueError("Malformed JUnit evidence") from exc
    suites = list(xml) if xml.tag == "testsuites" else [xml]
    if not suites or any(suite.tag != "testsuite" for suite in suites):
        raise ValueError("Invalid JUnit suite structure")
    xml_ids = []
    for suite in suites:
        cases = suite.findall("testcase")
        for key in ("tests", "errors", "failures", "skipped"):
            value = suite.get(key, "")
            if re.fullmatch(r"[0-9]+", value) is None:
                raise ValueError(f"Invalid JUnit count: {key}")
            if int(value) != (len(cases) if key == "tests" else 0):
                raise ValueError(f"JUnit count mismatch or non-passing tests: {key}")
        if any(child.tag not in ("testcase", "properties", "system-out", "system-err") for child in suite):
            raise ValueError("Unexpected JUnit suite evidence")
        for case in cases:
            if any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
                raise ValueError("JUnit contains failed or skipped tests")
            if any(child.tag not in ("properties", "system-out", "system-err") for child in case):
                raise ValueError("Unexpected JUnit testcase evidence")
            identities = [prop.get("value") for prop in case.findall("properties/property")
                          if prop.get("name") == NODEID_PROPERTY]
            if len(identities) != 1 or identities[0] not in selected_set:
                raise ValueError("Missing or unmatched JUnit node ID")
            xml_ids.append(identities[0])
    if Counter(xml_ids) != Counter(selected):
        raise ValueError("Missing or duplicate JUnit test evidence")
    count = len(selected)
    return {"collected": count, "selected": count, "executed": count, "passed": count,
            "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0,
            "deselected": 0, "collection_errors": 0, "collection_skipped": 0}


def successful_evidence(root, fingerprint, run_id):
    report, junit = root / "outputs" / REPORT_NAME, root / "outputs/tests.xml"
    summary = validate_run_report(report, junit, fingerprint, run_id)
    return {"schema_version": SCHEMA_VERSION, "passed": True, "tests": summary["passed"],
            "project_fingerprint": fingerprint, "full_suite": summary,
            "test_run": {"run_id": run_id, "report_sha256": sha256(report.read_bytes()).hexdigest(),
                         "junit_sha256": sha256(junit.read_bytes()).hexdigest()}}


def validate_test_evidence(root, evidence, fingerprint):
    if (not isinstance(evidence, dict) or evidence.get("passed") is not True
            or type(evidence.get("schema_version")) is not int
            or evidence["schema_version"] != SCHEMA_VERSION
            or evidence.get("project_fingerprint") != fingerprint):
        raise ValueError("Current full-suite verification evidence is absent or stale")
    run = evidence.get("test_run")
    if (not isinstance(run, dict) or not isinstance(run.get("run_id"), str) or not run["run_id"]
            or not is_digest(run.get("report_sha256")) or not is_digest(run.get("junit_sha256"))):
        raise ValueError("Missing full-suite artifact evidence")
    expected = successful_evidence(root, fingerprint, run["run_id"])
    summary = evidence.get("full_suite")
    if not isinstance(summary, dict) or set(summary) != set(expected["full_suite"]):
        raise ValueError("Missing full-suite counts")
    for key, value in summary.items():
        strict_count(value, key)
    strict_count(evidence.get("tests"), "tests")
    if evidence != expected:
        raise ValueError("Full-suite evidence counts or artifact hashes disagree")


def pytest_addoption(parser):
    group = parser.getgroup("release verification")
    group.addoption("--verification-report")
    group.addoption("--verification-run-id")
    group.addoption("--verification-fingerprint")


def pytest_configure(config):
    global _report
    _report = {"schema_version": SCHEMA_VERSION,
               "run_id": config.getoption("--verification-run-id"),
               "project_fingerprint": config.getoption("--verification-fingerprint"),
               "scope": "tests", "config": "pytest.ini", "collected_nodeids": [],
               "selected_nodeids": [], "deselected_nodeids": [], "reports": [],
               "collection_errors": 0, "collection_skipped": 0}


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    _report["collected_nodeids"] = [item.nodeid for item in items]
    for item in items:
        item.user_properties.append((NODEID_PROPERTY, item.nodeid))
    yield


def pytest_collection_finish(session):
    _report["selected_nodeids"] = [item.nodeid for item in session.items]


def pytest_deselected(items):
    _report["deselected_nodeids"].extend(item.nodeid for item in items)


def pytest_collectreport(report):
    _report["collection_errors"] += int(report.failed)
    _report["collection_skipped"] += int(report.skipped)


def pytest_runtest_logreport(report):
    _report["reports"].append({"nodeid": report.nodeid, "when": report.when,
                               "outcome": report.outcome, "wasxfail": hasattr(report, "wasxfail")})


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    from pathlib import Path
    _report["exitstatus"] = int(exitstatus)
    Path(session.config.getoption("--verification-report")).write_text(
        json.dumps(_report, indent=2), encoding="utf-8", newline="\n")
