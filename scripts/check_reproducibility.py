# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Rebuild offline and compare logical data, schema and deterministic outputs."""
from hashlib import sha256
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.acquire import acquire
from ev_pipeline.pipeline import build, connect, DB, OUT, QA
from ev_pipeline.evidence import project_fingerprint


def canonical_value(value):
    """Serialize timestamps by instant, including an explicitly changed session zone."""
    if isinstance(value, datetime):
        if value.tzinfo is not None and value.utcoffset() is not None:
            value = value.astimezone(timezone.utc)
        return value.isoformat(timespec="microseconds")
    return str(value)


def table_hashes():
    result = {}
    with connect(DB) as con:
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()
        for (name,) in tables:
            # WKB geometry representation and sorted row JSON are deterministic;
            # physical DuckDB bytes can differ between equivalent rebuilds.
            rows = con.execute(f'SELECT * FROM "{name}" ORDER BY ALL').fetchall()
            result[name] = sha256(json.dumps(rows, default=canonical_value, ensure_ascii=False).encode()).hexdigest()
    return result


def file_hashes():
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
            for folder in [OUT, QA] for p in sorted(folder.glob("*.csv"))}


def schema_hashes():
    """Hash persisted definitions, excluding physical catalog IDs and file names."""
    result = {}
    with connect(DB) as con:
        for kind, name_column in [("tables", "table_name"), ("views", "view_name"), ("indexes", "index_name")]:
            filters = "database_name=current_database()"
            if kind != "indexes":
                filters += " AND NOT internal AND NOT temporary"
            rows = con.execute(
                f"SELECT schema_name, {name_column}, sql FROM duckdb_{kind}() "
                f"WHERE {filters} ORDER BY schema_name, {name_column}"
            ).fetchall()
            result[kind] = sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()
    return result


def validation_hash():
    # This report is deterministic; run_manifest.json contains a run timestamp.
    return sha256((QA / "validation.json").read_bytes()).hexdigest()


def main():
    fingerprint = project_fingerprint()
    evidence = QA / "reproducibility.json"
    QA.mkdir(parents=True, exist_ok=True)
    # Revoke prior success even when reading the baseline or rebuilding fails.
    evidence.write_text(json.dumps({"table_content_identical": False, "csv_outputs_identical": False,
                                    "schema_identical": False, "validation_report_identical": False,
                                    "project_fingerprint": fingerprint}), encoding="utf-8", newline="\n")
    before_tables, before_files = table_hashes(), file_hashes()
    before_schema, before_validation = schema_hashes(), validation_hash()
    acquire(offline=True)
    build(offline=True)
    after_tables, after_files = table_hashes(), file_hashes()
    after_schema, after_validation = schema_hashes(), validation_hash()
    if project_fingerprint() != fingerprint:
        raise ValueError("Project changed during reproducibility check; rerun with unchanged inputs and code")
    result = {"table_content_identical": before_tables == after_tables, "csv_outputs_identical": before_files == after_files,
              "schema_identical": before_schema == after_schema, "validation_report_identical": before_validation == after_validation,
              "project_fingerprint": fingerprint,
              "tables": after_tables, "csv_outputs": after_files,
              "schema": after_schema, "validation_report_sha256": after_validation,
              "excluded": "Database physical bytes and run timestamps are not reproducibility criteria."}
    evidence.write_text(json.dumps(result, indent=2), encoding="utf-8", newline="\n")
    gates = ["table_content_identical", "csv_outputs_identical", "schema_identical", "validation_report_identical"]
    print(json.dumps({key: result[key] for key in gates}, indent=2))
    if not all(result[key] for key in gates):
        raise AssertionError("Offline rebuild changed logical results")


if __name__ == "__main__":
    main()
