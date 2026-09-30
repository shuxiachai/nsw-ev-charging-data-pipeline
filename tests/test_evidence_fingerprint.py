# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Verification evidence must cover released executable examples and fixtures."""
import pytest

from ev_pipeline import evidence


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("duckdb==1.5.5\n", encoding="utf-8")
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    monkeypatch.setattr(evidence, "RAW", tmp_path / "data/raw")
    return tmp_path


@pytest.mark.parametrize("relative", [
    "pyproject.toml", "examples/demo.py", "examples/records.csv", "examples/attributes.csv",
    "examples/nested/query.sql", "examples/nested/fixture.json",
])
def test_release_configuration_and_example_changes_invalidate_evidence(project, relative):
    without_file = evidence.project_fingerprint()
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("original fixture\n", encoding="utf-8")
    original = evidence.project_fingerprint()
    assert original != without_file
    path.write_text("changed fixture\n", encoding="utf-8")
    assert evidence.project_fingerprint() != original
    path.unlink()
    assert evidence.project_fingerprint() == without_file


def test_readme_changes_do_not_invalidate_executable_evidence(project):
    readme = project / "examples/README.md"
    readme.parent.mkdir()
    baseline = evidence.project_fingerprint()
    readme.write_text("Example documentation\n", encoding="utf-8")
    assert evidence.project_fingerprint() == baseline
    readme.write_text("Clarified documentation\n", encoding="utf-8")
    assert evidence.project_fingerprint() == baseline


def test_legacy_project_without_optional_release_files_still_has_a_stable_fingerprint(project):
    assert not (project / "pyproject.toml").exists()
    assert not (project / "examples").exists()
    fingerprint = evidence.project_fingerprint()
    assert len(fingerprint) == 64
    assert evidence.project_fingerprint() == fingerprint
