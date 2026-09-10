"""Package only project deliverables; exclude environments, secrets and scratch."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.evidence import project_fingerprint
from ev_pipeline.pipeline import connect, DB, validate, snapshots
from scripts.check_reproducibility import table_hashes, file_hashes, schema_hashes, validation_hash
FOLDERS = ["ev_pipeline", "config", "sql", "scripts", "tests", "data/raw", "data/processed", "outputs"]
FILES = ["README.md", "requirements.txt", "pytest.ini", ".gitignore"]
DOCUMENTS = ["design.md", "schema.md", "sources.md", "source_version_review_20260908.md",
             "reviewed_resolution_design.md", "matching_changes_20260909.md", "code_review_20260909.md",
             "edge_case_review_20260909.md", "external_review_actions_20260909.md",
             "continuation_review_actions_20260909.md", "jolt_details_evidence_20260909.md",
             "matching_evidence_improvement_20260909.md", "improvement_self_check_20260909.md",
             "regional_sa4_review_20260909.md", "third_review_actions_20260909.md",
             "final_optimization_20260910.md", "final_matching_review_20260910.md",
             "final_matching_review_20260910.csv", "fresh_environment_20260910.md",
             "identity_evie_council_20260910.md", "external_review_followup_20260910.md"]
REQUIRED = ["README.md", "requirements.txt", "sql/schema.sql", "data/processed/ev_chargers.duckdb",
            "docs/design.md", "docs/schema.md", "docs/sources.md"]


def submission_files():
    """Include technical documentation, excluding internal handoffs and old reviews."""
    files = [ROOT / name for name in FILES]
    files.extend(ROOT / "docs" / name for name in DOCUMENTS if (ROOT / "docs" / name).is_file())
    for folder in FOLDERS:
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                     and p.suffix.lower() not in {".pyc", ".part", ".building", ".wal"})
    files = set(files)
    for path in files:
        if not path.is_relative_to(ROOT / "data/raw"):
            continue
        companion = (path.with_name(path.name.removesuffix(".meta.json")) if path.name.endswith(".meta.json")
                     else path.with_name(path.name + ".meta.json"))
        if companion not in files or not companion.is_file():
            raise ValueError(f"Raw source/manifest pair missing: {companion}")
    return sorted(files)


def write_archive(files, archive):
    """Keep the previous complete ZIP if constructing or checking the new ZIP fails."""
    partial = archive.with_name(archive.name + ".part")
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in files:
                z.write(p, p.relative_to(ROOT).as_posix())
        with zipfile.ZipFile(partial) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f"Archive CRC check failed: {bad}")
            names = set(z.namelist())
            for required in REQUIRED:
                if required not in names:
                    raise ValueError(f"Archive missing required deliverable: {required}")
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return names


def main():
    checks = json.loads((ROOT / "outputs/validation.json").read_text(encoding="utf-8"))
    repro = json.loads((ROOT / "outputs/reproducibility.json").read_text(encoding="utf-8"))
    tests = json.loads((ROOT / "outputs/test_evidence.json").read_text(encoding="utf-8"))
    current = project_fingerprint()
    if not tests.get("passed") or tests.get("project_fingerprint") != current or repro.get("project_fingerprint") != current:
        raise ValueError("Verification evidence is absent/stale; run scripts/verify_project.py")
    if not all(repro.get(key) for key in ["table_content_identical", "csv_outputs_identical",
                                         "schema_identical", "validation_report_identical"]):
        raise ValueError("Reproducibility gate not met")
    snapshots()  # Check raw bytes, not only the manifest signatures.
    if table_hashes() != repro["tables"] or file_hashes() != repro["csv_outputs"]:
        raise ValueError("Database or CSV outputs changed after verification")
    if schema_hashes() != repro.get("schema"):
        raise ValueError("Database schema changed after verification")
    if validation_hash() != repro.get("validation_report_sha256"):
        raise ValueError("Validation report changed after verification")
    with connect(DB) as con:
        current_checks = validate(con)
    if not current_checks["integrity_passed"] or not current_checks["coverage"]["site_scope_target_met"]:
        raise ValueError("Current database fails verification")
    if not checks["integrity_passed"] or not checks["coverage"]["site_scope_target_met"]:
        raise ValueError("Integrity/site coverage gate not met; inspect validation.json")
    if any(checks.get(key) != value for key, value in current_checks.items()):
        raise ValueError("Validation report disagrees with the current database; rebuild before packaging")
    files = submission_files()
    destination = ROOT / "submission"
    destination.mkdir(exist_ok=True)
    archive = destination / "COMP5339_A1_Code_and_Database.zip"
    names = write_archive(files, archive)
    (destination / "SHA256.txt").write_text(sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="utf-8")
    print(f"Created {archive.name}: {archive.stat().st_size:,} bytes, {len(names)} files; CRC verified")


if __name__ == "__main__":
    main()
