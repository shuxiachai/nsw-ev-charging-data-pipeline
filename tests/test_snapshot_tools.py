# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to create this file.
# AI-generated material is included in this file.

"""Focused safety and recovery checks for frozen raw snapshots."""
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts import preflight, restore_snapshot


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_fixture(tmp_path: Path, body: bytes = b"frozen source") -> tuple[Path, Path, Path]:
    root = tmp_path / "project"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    target = raw / "source.txt"
    target.with_name("source.txt.meta.json").write_text(json.dumps({"sha256": digest(body), "bytes": len(body)}))
    return root, raw, target


def make_archive(path: Path, contents: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as bundle:
        for name, value in contents.items():
            bundle.writestr(name, value)
    return path


def test_preflight_reports_every_missing_and_corrupt_companion(tmp_path):
    _, raw, first = raw_fixture(tmp_path, b"one")
    second = raw / "second.txt"
    second.with_name("second.txt.meta.json").write_text(json.dumps({"sha256": digest(b"two"), "bytes": 3}))
    first.write_bytes(b"wrong")
    issues = preflight.raw_issues(raw)
    assert any(issue.startswith("SIZE MISMATCH source.txt") for issue in issues)
    assert any(issue.startswith("HASH MISMATCH source.txt") for issue in issues)
    assert "MISSING second.txt" in issues


def test_preflight_only_requires_database_when_requested(tmp_path, monkeypatch):
    root, raw, target = raw_fixture(tmp_path)
    target.write_bytes(b"frozen source")
    monkeypatch.setattr(preflight, "RAW", raw)
    monkeypatch.setattr(preflight, "DB", root / "data/processed/ev_chargers.duckdb")
    assert preflight.main([]) == 0
    assert preflight.main(["--require-db"]) == 1


@pytest.mark.parametrize("exists", [False, True])
def test_preflight_rejects_missing_or_empty_raw_directory(tmp_path, monkeypatch, capsys, exists):
    raw = tmp_path / "data/raw"
    if exists:
        raw.mkdir(parents=True)
    monkeypatch.setattr(preflight, "RAW", raw)
    assert preflight.main([]) == 1
    message = "NO RAW MANIFESTS" if exists else "MISSING RAW DIRECTORY"
    assert message in capsys.readouterr().out


def test_preflight_rejects_body_without_manifest_even_with_other_valid_sources(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    target.write_bytes(b"frozen source")
    orphan = raw / "nested/orphan.txt"
    orphan.parent.mkdir()
    orphan.write_bytes(b"untracked source")
    assert preflight.raw_issues(raw) == ["UNMANIFESTED BODY nested/orphan.txt"]


def test_preflight_rejects_nonhexadecimal_manifest_hash_and_accepts_uppercase_hex(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    target.write_bytes(b"frozen source")
    manifest = target.with_name(target.name + ".meta.json")
    value = json.loads(manifest.read_text())
    value["sha256"] = "x" * 64
    manifest.write_text(json.dumps(value))
    assert preflight.raw_issues(raw)[0].startswith("INVALID MANIFEST source.txt: sha256")
    value["sha256"] = digest(target.read_bytes()).upper()
    manifest.write_text(json.dumps(value))
    assert preflight.raw_issues(raw) == []


def test_restore_requires_checksum_for_caller_supplied_archive(tmp_path, capsys):
    archive = make_archive(tmp_path / "snapshot.zip", {})
    assert restore_snapshot.main(["--archive", str(archive)]) == 1
    assert "--sha256 is required" in capsys.readouterr().out


def test_restore_rejects_bad_archive_checksum_before_writing(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    archive = make_archive(tmp_path / "snapshot.zip", {"data/raw/source.txt": b"frozen source"})
    with pytest.raises(restore_snapshot.RestoreError, match="SHA256 mismatch"):
        restore_snapshot.restore(archive, "0" * 64, raw)
    assert not target.exists()


def test_restore_rejects_path_traversal_and_preserves_project_files(tmp_path):
    root, raw, target = raw_fixture(tmp_path)
    code = root / "README.md"
    code.write_text("keep this code")
    archive = make_archive(tmp_path / "snapshot.zip", {
        "../README.md": b"overwrite attempt", "data/raw/source.txt": b"frozen source",
    })
    with pytest.raises(restore_snapshot.RestoreError, match="unsafe ZIP member"):
        restore_snapshot.plan_restore(archive, raw)
    assert code.read_text() == "keep this code"
    assert not target.exists()


def test_restore_rejects_duplicate_members_and_symlinks(tmp_path):
    _, raw, _ = raw_fixture(tmp_path)
    duplicate = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(duplicate, "w") as bundle:
        bundle.writestr("data/raw/source.txt", b"frozen source")
        bundle.writestr("data/raw/source.txt", b"frozen source")
    with pytest.raises(restore_snapshot.RestoreError, match="duplicate ZIP member"):
        restore_snapshot.plan_restore(duplicate, raw)
    symlink = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("data/raw/link")
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(symlink, "w") as bundle:
        bundle.writestr(info, b"target")
        bundle.writestr("data/raw/source.txt", b"frozen source")
    with pytest.raises(restore_snapshot.RestoreError, match="symlink ZIP member"):
        restore_snapshot.plan_restore(symlink, raw)


def test_restore_rejects_manifest_mismatch_and_existing_corrupt_body(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    archive = make_archive(tmp_path / "snapshot.zip", {"data/raw/source.txt": b"different"})
    with pytest.raises(restore_snapshot.RestoreError, match="archive size mismatch"):
        restore_snapshot.plan_restore(archive, raw)
    target.write_bytes(b"corrupt")
    archive = make_archive(tmp_path / "correct.zip", {"data/raw/source.txt": b"frozen source"})
    with pytest.raises(restore_snapshot.RestoreError, match="existing body is corrupt"):
        restore_snapshot.plan_restore(archive, raw)
    assert target.read_bytes() == b"corrupt"


def test_restore_writes_only_missing_raw_body_and_is_idempotent(tmp_path):
    root, raw, target = raw_fixture(tmp_path)
    code = root / "README.md"
    code.write_text("unchanged")
    archive = make_archive(tmp_path / "snapshot.zip", {
        "README.md": b"replacement forbidden by scope",
        "data/raw/source.txt": b"frozen source",
        "data/raw/source.txt.meta.json": b"replacement manifest",
        "data/processed/ev_chargers.duckdb": b"ignored database",
    })
    checksum = digest(archive.read_bytes())
    assert restore_snapshot.restore(archive, checksum, raw) == 1
    assert target.read_bytes() == b"frozen source"
    assert code.read_text() == "unchanged"
    assert restore_snapshot.restore(archive, checksum, raw) == 0


@pytest.mark.parametrize("exists", [False, True])
def test_restore_rejects_missing_or_empty_manifest_configuration(tmp_path, exists):
    raw = tmp_path / "project/data/raw"
    if exists:
        raw.mkdir(parents=True)
    archive = make_archive(tmp_path / "snapshot.zip", {})
    message = "no raw snapshot manifests found" if exists else "raw snapshot directory is missing"
    with pytest.raises(restore_snapshot.RestoreError, match=message):
        restore_snapshot.restore(archive, digest(archive.read_bytes()), raw)


def test_restore_accepts_explicit_zip_directory_members(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    archive = make_archive(tmp_path / "snapshot.zip", {
        "data/": b"", "data/raw/": b"", "data/raw/nested/": b"",
        "data/raw/source.txt": b"frozen source",
    })
    assert restore_snapshot.restore(archive, digest(archive.read_bytes()), raw) == 1
    assert target.read_bytes() == b"frozen source"
    assert preflight.raw_issues(raw) == []


def test_restore_still_rejects_unmanifested_body_in_directory_members(tmp_path):
    _, raw, target = raw_fixture(tmp_path)
    archive = make_archive(tmp_path / "snapshot.zip", {
        "data/raw/nested/": b"", "data/raw/nested/orphan.txt": b"untracked source",
        "data/raw/source.txt": b"frozen source",
    })
    with pytest.raises(restore_snapshot.RestoreError, match="raw body without a current manifest"):
        restore_snapshot.plan_restore(archive, raw)
    assert not target.exists()


def test_restore_directory_cannot_supply_even_an_empty_snapshot_body(tmp_path):
    _, raw, target = raw_fixture(tmp_path, b"")
    archive = make_archive(tmp_path / "snapshot.zip", {"data/raw/source.txt/": b""})
    with pytest.raises(restore_snapshot.RestoreError, match="directory instead of required raw body"):
        restore_snapshot.plan_restore(archive, raw)
    assert not target.exists()
