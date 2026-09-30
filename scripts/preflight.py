# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to create this file.
# AI-generated material is included in this file.

"""Check that every frozen raw snapshot agrees with its local manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "processed" / "ev_chargers.duckdb"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_issues(raw: Path = RAW) -> list[str]:
    """Return every missing, malformed, or inconsistent raw snapshot issue."""
    if not raw.is_dir():
        return [f"MISSING RAW DIRECTORY {raw}"]
    issues: list[str] = []
    manifests = sorted(path for path in raw.rglob("*.meta.json") if path.is_file())
    if not manifests:
        issues.append(f"NO RAW MANIFESTS {raw}")
    expected_bodies = {path.with_name(path.name.removesuffix(".meta.json")) for path in manifests}
    for body in sorted(path for path in raw.rglob("*") if path.is_file()):
        if not body.name.endswith(".meta.json") and body not in expected_bodies:
            issues.append(f"UNMANIFESTED BODY {body.relative_to(raw).as_posix()}")
    for manifest_path in manifests:
        body = manifest_path.with_name(manifest_path.name.removesuffix(".meta.json"))
        label = body.relative_to(raw).as_posix()
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_hash = manifest["sha256"]
            expected_size = manifest["bytes"]
            if (not isinstance(expected_hash, str) or len(expected_hash) != 64
                    or not all(c in "0123456789abcdefABCDEF" for c in expected_hash)):
                raise ValueError("sha256 must be a 64-character hexadecimal value")
            expected_hash = expected_hash.lower()
            if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
                raise ValueError("bytes must be a non-negative integer")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            issues.append(f"INVALID MANIFEST {label}: {exc}")
            continue
        if not body.is_file():
            issues.append(f"MISSING {label}")
            continue
        actual_size = body.stat().st_size
        if actual_size != expected_size:
            issues.append(f"SIZE MISMATCH {label}: expected {expected_size}, found {actual_size}")
        actual_hash = sha256_file(body)
        if actual_hash != expected_hash:
            issues.append(f"HASH MISMATCH {label}: expected {expected_hash}, found {actual_hash}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-db", action="store_true", help="also require the built DuckDB database")
    args = parser.parse_args(argv)
    issues = raw_issues(RAW)
    if args.require_db and not DB.is_file():
        issues.append(f"MISSING DATABASE {DB.relative_to(ROOT).as_posix()}")
    if issues:
        print("Snapshot preflight failed:")
        print("\n".join(issues))
        return 1
    print("Snapshot preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
