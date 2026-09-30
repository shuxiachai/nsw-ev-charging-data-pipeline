# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to generate or revise this file.
# AI-generated or AI-revised material is included in this file.
"""Build a verified public code/data release without changing coursework archives."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.evidence import project_fingerprint
from ev_pipeline.pipeline import DB, connect, snapshots, validate
from scripts.check_reproducibility import table_hashes, file_hashes, schema_hashes, validation_hash

VERSION = "0.1.0"
ARCHIVE_NAME = f"nsw-ev-charging-data-pipeline-v{VERSION}.zip"
DIRECTORIES = ("ev_pipeline", "config", "sql", "scripts", "tests", "data/raw",
               "data/processed", "outputs", "docs", "examples", ".github")
ROOT_FILES = ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md",
              "CHANGELOG.md", "pyproject.toml", "requirements.txt", "pytest.ini",
              ".gitignore", ".gitattributes")


def release_files():
    files = [ROOT / name for name in ROOT_FILES]
    for directory in DIRECTORIES:
        files.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    result = []
    for path in sorted(set(files)):
        name = path.relative_to(ROOT).as_posix()
        if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".part", ".wal", ".building"}:
            continue
        if name.startswith("docs/releases/") or name == "outputs/clean_environment_verification.json":
            continue
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f"Missing or unsafe release file: {name}")
        result.append(path)
    required = {"data/processed/ev_chargers.duckdb", "sql/schema.sql", "LICENSE", "README.md"}
    names = {p.relative_to(ROOT).as_posix() for p in result}
    if not required.issubset(names):
        raise ValueError(f"Release files missing: {sorted(required - names)}")
    return result


def verified_evidence():
    current = project_fingerprint()
    tests = json.loads((ROOT / "outputs/test_evidence.json").read_text(encoding="utf-8"))
    repro = json.loads((ROOT / "outputs/reproducibility.json").read_text(encoding="utf-8"))
    if not tests.get("passed") or tests.get("project_fingerprint") != current or repro.get("project_fingerprint") != current:
        raise ValueError("Current code/input verification evidence is absent or stale")
    for key in ("table_content_identical", "csv_outputs_identical", "schema_identical", "validation_report_identical"):
        if repro.get(key) is not True:
            raise ValueError(f"Reproduction gate failed: {key}")
    snapshots()
    if table_hashes() != repro["tables"] or file_hashes() != repro["csv_outputs"]:
        raise ValueError("Database or CSV contents changed after verification")
    if schema_hashes() != repro["schema"] or validation_hash() != repro["validation_report_sha256"]:
        raise ValueError("Schema or validation evidence changed after verification")
    with connect(DB) as con:
        checks = validate(con)
    if not checks["integrity_passed"] or not checks["coverage"]["site_scope_target_met"]:
        raise ValueError("Database integrity or coverage gate failed")
    return current, tests, checks


def main():
    fingerprint, tests, checks = verified_evidence()
    paths = release_files()
    destination = ROOT / "submission"
    destination.mkdir(exist_ok=True)
    archive = destination / ARCHIVE_NAME
    partial = archive.with_suffix(".zip.part")
    hashes = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}
    try:
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in paths:
                bundle.write(path, path.relative_to(ROOT).as_posix())
        with zipfile.ZipFile(partial) as bundle:
            if bundle.testzip() is not None or set(bundle.namelist()) != set(hashes):
                raise ValueError("Release archive integrity check failed")
            for name, expected in hashes.items():
                if sha256(bundle.read(name)).hexdigest() != expected:
                    raise ValueError(f"Release member hash mismatch: {name}")
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    digest = sha256(archive.read_bytes()).hexdigest()
    record = {
        "version": VERSION,
        "archive_name": ARCHIVE_NAME,
        "archive_sha256": digest,
        "archive_bytes": archive.stat().st_size,
        "archive_file_count": len(hashes),
        "download_url": f"https://github.com/shuxiachai/nsw-ev-charging-data-pipeline/releases/download/v{VERSION}/{ARCHIVE_NAME}",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_fingerprint": fingerprint,
        "test_count": tests["tests"],
        "integrity_checks": len(checks["integrity_checks"]),
        "member_sha256": hashes,
        "descriptor_note": "docs/releases descriptors are outside the archive to avoid a self-referential archive checksum",
    }
    (destination / "release_manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8", newline="\n")
    (destination / "SHA256.txt").write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="utf-8", newline="\n")
    descriptor = ROOT / "docs/releases" / f"v{VERSION}.json"
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    descriptor.write_text(json.dumps({k: v for k, v in record.items() if k != "member_sha256"}, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in record.items() if k != "member_sha256"}, indent=2))


if __name__ == "__main__":
    main()
