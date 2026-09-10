"""Verification and packaging must fail closed without discarding the last ZIP."""
import json
import shutil
import subprocess
from types import SimpleNamespace
import zipfile
from datetime import datetime, timezone

import pytest
import duckdb

from scripts import check_reproducibility, package_submission, verify_project


def test_pipeline_connections_use_utc_for_exports():
    from ev_pipeline.pipeline import connect
    with connect(":memory:") as con:
        assert con.execute("SELECT current_setting('TimeZone')").fetchone()[0] == "UTC"


@pytest.mark.parametrize("zone", ["UTC", "Australia/Sydney", "America/New_York", "Asia/Kathmandu"])
def test_timestamp_hashes_are_independent_of_session_timezone(tmp_path, monkeypatch, zone):
    db = tmp_path / "timestamps.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE observations(captured TIMESTAMPTZ, local_clock TIMESTAMP)")
        con.execute("""INSERT INTO observations VALUES
            ('2026-01-06 00:51:14.637889+00', '2026-01-06 10:51:14.637889'),
            ('2026-09-06 00:51:14.637889+00', '2026-09-06 10:51:14.637889')""")

    def connection_for_zone(name):
        def connect(path):
            con = duckdb.connect(str(path))
            con.execute("SET TimeZone = ?", [name])
            return con
        return connect

    monkeypatch.setattr(check_reproducibility, "DB", db)
    monkeypatch.setattr(check_reproducibility, "connect", connection_for_zone("UTC"))
    baseline = check_reproducibility.table_hashes()
    monkeypatch.setattr(check_reproducibility, "connect", connection_for_zone(zone))
    assert check_reproducibility.table_hashes() == baseline
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE observations SET captured=captured+INTERVAL '1 microsecond'")
    assert check_reproducibility.table_hashes() != baseline


def test_timestamp_serialization_does_not_invent_timezone_for_naive_values():
    naive = datetime(2026, 9, 9, 10, 11, 12, 345678)
    assert check_reproducibility.canonical_value(naive) == "2026-09-09T10:11:12.345678"
    assert check_reproducibility.canonical_value(naive.replace(tzinfo=timezone.utc)).endswith("+00:00")


def verification_fixture(tmp_path, monkeypatch, failed_stage=None, fingerprints=None):
    monkeypatch.setattr(verify_project, "ROOT", tmp_path)
    monkeypatch.setattr(verify_project, "sys", SimpleNamespace(
        executable="test-python", stdout=SimpleNamespace(reconfigure=lambda **kwargs: None)))
    values = iter(fingerprints or ["same-inputs", "same-inputs"])
    monkeypatch.setattr(verify_project, "project_fingerprint", lambda: next(values))
    (tmp_path / "outputs").mkdir()
    evidence = tmp_path / "outputs/test_evidence.json"
    evidence.write_text(json.dumps({"passed": True, "project_fingerprint": "same-inputs"}))

    def run(command, **kwargs):
        if "pytest" in command:
            (tmp_path / "outputs/tests.xml").write_text(
                '<testsuites><testsuite tests="1" errors="0" failures="0"/></testsuites>')
        elif failed_stage is not None and failed_stage in command:
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verify_project.subprocess, "run", run)
    return evidence


@pytest.mark.parametrize("failed_stage", ["scripts/check_reproducibility.py", "validate"])
def test_later_verification_failure_revokes_prior_passing_evidence(tmp_path, monkeypatch, failed_stage):
    evidence = verification_fixture(tmp_path, monkeypatch, failed_stage=failed_stage)
    with pytest.raises(subprocess.CalledProcessError):
        verify_project.main()
    assert json.loads(evidence.read_text())["passed"] is False


def test_verification_rejects_code_or_manifest_changes_during_the_run(tmp_path, monkeypatch):
    evidence = verification_fixture(tmp_path, monkeypatch, fingerprints=["before", "after"])
    with pytest.raises(ValueError, match="changed during verification"):
        verify_project.main()
    assert json.loads(evidence.read_text())["passed"] is False


def test_success_is_published_after_all_verification_stages(tmp_path, monkeypatch):
    evidence = verification_fixture(tmp_path, monkeypatch)
    verify_project.main()
    assert json.loads(evidence.read_text()) == {
        "passed": True, "tests": 1, "project_fingerprint": "same-inputs"}


def test_rebuild_exception_revokes_old_reproducibility_success(tmp_path, monkeypatch):
    monkeypatch.setattr(check_reproducibility, "QA", tmp_path)
    monkeypatch.setattr(check_reproducibility, "project_fingerprint", lambda: "same-inputs")
    monkeypatch.setattr(check_reproducibility, "table_hashes", lambda: {"location": "content"})
    monkeypatch.setattr(check_reproducibility, "file_hashes", lambda: {})
    monkeypatch.setattr(check_reproducibility, "schema_hashes", lambda: {"views": "definition"})
    monkeypatch.setattr(check_reproducibility, "validation_hash", lambda: "report")
    monkeypatch.setattr(check_reproducibility, "acquire", lambda **kwargs: None)

    def fail_build(**kwargs):
        raise RuntimeError("rebuild failed")

    monkeypatch.setattr(check_reproducibility, "build", fail_build)
    evidence = tmp_path / "reproducibility.json"
    evidence.write_text(json.dumps({"table_content_identical": True, "csv_outputs_identical": True}))
    with pytest.raises(RuntimeError, match="rebuild failed"):
        check_reproducibility.main()
    result = json.loads(evidence.read_text())
    assert result["table_content_identical"] is False and result["csv_outputs_identical"] is False


def test_submission_excludes_internal_reviews_but_keeps_current_technical_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(package_submission, "ROOT", tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    names = ["design.md", "schema.md", "sources.md", "source_version_review_20260908.md",
             "reviewed_resolution_design.md", "matching_changes_20260909.md", "code_review_20260909.md",
             "edge_case_review_20260909.md",
             "codex_handoff.md", "rubric_review.md", "unresolved_review_20260908.csv",
             "matching_review_20260908.md", "priority_changes_20260908.md"]
    for name in names:
        (docs / name).write_text("documentation")
    included = {p.relative_to(tmp_path).as_posix() for p in package_submission.submission_files()}
    assert "docs/reviewed_resolution_design.md" in included
    assert "docs/code_review_20260909.md" in included
    assert "docs/edge_case_review_20260909.md" in included
    assert "docs/source_version_review_20260908.md" in included
    assert all("docs/" + name not in included for name in names[8:])
    assert (docs / "codex_handoff.md").exists()  # Packaging does not delete working notes.


def test_submission_omits_historical_verification_without_deleting_it(tmp_path, monkeypatch):
    monkeypatch.setattr(package_submission, "ROOT", tmp_path)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    historical = outputs / "clean_environment_verification.json"
    historical.write_text('{"scope":"historical checkpoint"}')
    for name in ["test_evidence.json", "reproducibility.json", "validation.json"]:
        (outputs / name).write_text("{}")
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ["standalone_sql.md", "fresh_environment_20260910.md"]:
        (docs / name).write_text("documentation")
    included = {p.relative_to(tmp_path).as_posix() for p in package_submission.submission_files()}
    assert "outputs/clean_environment_verification.json" not in included
    assert historical.read_text() == '{"scope":"historical checkpoint"}'
    assert {"outputs/test_evidence.json", "outputs/reproducibility.json",
            "outputs/validation.json", "docs/standalone_sql.md",
            "docs/fresh_environment_20260910.md"} <= included


@pytest.mark.parametrize("orphan", ["source.pdf", "source.pdf.meta.json"])
def test_submission_rejects_raw_files_without_their_provenance_pair(tmp_path, monkeypatch, orphan):
    monkeypatch.setattr(package_submission, "ROOT", tmp_path)
    raw = tmp_path / "data/raw/reviewed"
    raw.mkdir(parents=True)
    (raw / orphan).write_bytes(b"source or metadata")
    with pytest.raises(ValueError, match="source/manifest pair missing"):
        package_submission.submission_files()


@pytest.mark.parametrize("failure", ["write", "missing-required"])
def test_failed_archive_creation_preserves_the_previous_zip(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(package_submission, "ROOT", tmp_path)
    files = []
    for name in package_submission.REQUIRED:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test deliverable")
        files.append(path)
    archive = tmp_path / "submission.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("previous.txt", "previous complete submission")
    previous = archive.read_bytes()
    if failure == "write":
        def fail_write(*args, **kwargs):
            raise OSError("archive write interrupted")
        monkeypatch.setattr(zipfile.ZipFile, "write", fail_write)
        expected_error = OSError
    else:
        files = files[:1]
        expected_error = ValueError
    with pytest.raises(expected_error):
        package_submission.write_archive(files, archive)
    assert archive.read_bytes() == previous
    assert not archive.with_name(archive.name + ".part").exists()


@pytest.fixture
def logical_results(tmp_path, monkeypatch):
    """A real, small database and exports; production inputs/outputs stay untouched."""
    db = tmp_path / "data/processed/ev_chargers.duckdb"
    db.parent.mkdir(parents=True)
    qa = tmp_path / "outputs"
    qa.mkdir()
    ddl = """
        CREATE TABLE location (location_id INTEGER);
        INSERT INTO location VALUES (1);
        CREATE VIEW analysis_ready_locations AS SELECT * FROM location;
    """
    with duckdb.connect(str(db)) as con:
        con.execute(ddl)
    (db.parent / "locations.csv").write_text("location_id\n1\n", encoding="utf-8")
    checks = {"integrity_passed": True, "coverage": {"site_scope_target_met": True},
              "input_rows": 1, "locations": 1, "quality_issue_counts": {}}
    report = qa / "validation.json"
    report.write_text(json.dumps(checks), encoding="utf-8")
    for module in [check_reproducibility, package_submission]:
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "DB", db)
        monkeypatch.setattr(module, "connect", lambda path: duckdb.connect(str(path)))
        monkeypatch.setattr(module, "project_fingerprint", lambda: "fixture-inputs")
    monkeypatch.setattr(check_reproducibility, "OUT", db.parent)
    monkeypatch.setattr(check_reproducibility, "QA", qa)
    monkeypatch.setattr(check_reproducibility, "acquire", lambda **kwargs: None)

    def rebuild(**kwargs):
        # Recreate logical contents in another physical catalog, as the real build does.
        rebuilt = db.with_name("rebuilt.duckdb")
        with duckdb.connect(str(rebuilt)) as con:
            con.execute(ddl)
        rebuilt.replace(db)

    monkeypatch.setattr(check_reproducibility, "build", rebuild)
    return SimpleNamespace(root=tmp_path, db=db, qa=qa, report=report, checks=checks)


@pytest.mark.parametrize("sql,changed_kind", [
    ("CREATE OR REPLACE VIEW analysis_ready_locations AS SELECT * FROM location WHERE FALSE", "views"),
    ("ALTER TABLE location ALTER COLUMN location_id SET NOT NULL", "tables"),
    ("CREATE INDEX location_id_idx ON location(location_id)", "indexes"),
])
def test_definition_changes_are_detected_when_all_stored_rows_are_unchanged(logical_results, sql, changed_kind):
    rows = check_reproducibility.table_hashes()
    schema = check_reproducibility.schema_hashes()
    with duckdb.connect(str(logical_results.db)) as con:
        con.execute(sql)
    assert check_reproducibility.table_hashes() == rows
    assert check_reproducibility.schema_hashes()[changed_kind] != schema[changed_kind]


def test_schema_signature_is_independent_of_database_filename(logical_results, monkeypatch):
    original = check_reproducibility.schema_hashes()
    copy = logical_results.db.with_name("different_catalog_name.duckdb")
    shutil.copy2(logical_results.db, copy)
    monkeypatch.setattr(check_reproducibility, "DB", copy)
    assert check_reproducibility.schema_hashes() == original


@pytest.mark.parametrize("change", ["none", "view", "report"])
def test_offline_reproduction_covers_schema_and_full_validation_report(logical_results, monkeypatch, change):
    rebuild = check_reproducibility.build

    def changed_rebuild(**kwargs):
        rebuild(**kwargs)
        if change == "view":
            with duckdb.connect(str(logical_results.db)) as con:
                con.execute("CREATE OR REPLACE VIEW analysis_ready_locations AS SELECT * FROM location WHERE FALSE")
        elif change == "report":
            altered = dict(logical_results.checks, input_rows=0, locations=-7, quality_issue_counts={"wrong": 123})
            logical_results.report.write_text(json.dumps(altered), encoding="utf-8")

    monkeypatch.setattr(check_reproducibility, "build", changed_rebuild)
    if change == "none":
        check_reproducibility.main()
    else:
        with pytest.raises(AssertionError, match="changed logical results"):
            check_reproducibility.main()
    result = json.loads((logical_results.qa / "reproducibility.json").read_text())
    assert result["table_content_identical"] is True
    assert result["csv_outputs_identical"] is True
    assert result["schema_identical"] is (change != "view")
    assert result["validation_report_identical"] is (change != "report")


@pytest.mark.parametrize("change,error", [
    ("view", "Database schema changed"),
    ("report", "Validation report changed"),
    ("old-evidence", "Reproducibility gate not met"),
    ("none", None),
])
def test_packaging_checks_verified_schema_and_entire_report(logical_results, monkeypatch, change, error):
    check_reproducibility.main()
    (logical_results.qa / "test_evidence.json").write_text(
        json.dumps({"passed": True, "project_fingerprint": "fixture-inputs"}), encoding="utf-8")
    monkeypatch.setattr(package_submission, "snapshots", lambda: [])
    monkeypatch.setattr(package_submission, "validate", lambda con: {
        "integrity_passed": con.execute("SELECT count(*) FROM location").fetchone()[0] == 1,
        "coverage": {"site_scope_target_met": True}})
    for name in set(package_submission.REQUIRED + package_submission.FILES):
        path = logical_results.root / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test deliverable", encoding="utf-8")
    destination = logical_results.root / "submission"
    destination.mkdir()
    archive = destination / "COMP5339_A1_Code_and_Database.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("previous.txt", "previous complete submission")
    previous = archive.read_bytes()
    if change == "view":
        with duckdb.connect(str(logical_results.db)) as con:
            con.execute("CREATE OR REPLACE VIEW analysis_ready_locations AS SELECT * FROM location WHERE FALSE")
    elif change == "report":
        altered = dict(logical_results.checks, input_rows=0, locations=-7, quality_issue_counts={"wrong": 123})
        logical_results.report.write_text(json.dumps(altered), encoding="utf-8")
    elif change == "old-evidence":
        evidence = logical_results.qa / "reproducibility.json"
        old = json.loads(evidence.read_text())
        for key in ["schema_identical", "validation_report_identical", "schema", "validation_report_sha256"]:
            old.pop(key)
        evidence.write_text(json.dumps(old), encoding="utf-8")
    if error:
        with pytest.raises(ValueError, match=error):
            package_submission.main()
        assert archive.read_bytes() == previous
        assert not archive.with_name(archive.name + ".part").exists()
    else:
        package_submission.main()
        with zipfile.ZipFile(archive) as z:
            assert json.loads(z.read("outputs/validation.json")) == logical_results.checks
            assert "data/processed/ev_chargers.duckdb" in z.namelist()
        assert (destination / "SHA256.txt").exists()
