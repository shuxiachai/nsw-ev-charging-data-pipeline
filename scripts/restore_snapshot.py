# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to create this file.
# AI-generated material is included in this file.

"""Restore only missing raw snapshot bodies from a checksum-pinned ZIP archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RUNTIME = ROOT / ".runtime"
DEFAULT_DESCRIPTOR = ROOT / "docs" / "releases" / "v0.1.0.json"


class RestoreError(ValueError):
    """Raised before a restore would alter project data."""


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> tuple[str, int]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        digest, size = value["sha256"], value["bytes"]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RestoreError(f"invalid manifest {display_path(path)}: {exc}") from exc
    if not isinstance(digest, str) or len(digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in digest):
        raise RestoreError(f"invalid manifest {display_path(path)}: sha256 must be hexadecimal")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise RestoreError(f"invalid manifest {display_path(path)}: bytes must be a non-negative integer")
    return digest.lower(), size


def safe_member_name(info: zipfile.ZipInfo) -> PurePosixPath:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    mode = info.external_attr >> 16
    if name.startswith("/") or (len(name) >= 2 and name[1] == ":") or ".." in path.parts:
        raise RestoreError(f"unsafe ZIP member: {info.filename}")
    if mode and (mode & 0o170000) == 0o120000:
        raise RestoreError(f"symlink ZIP member: {info.filename}")
    return path


def archive_members(archive: Path) -> dict[str, zipfile.ZipInfo]:
    try:
        with zipfile.ZipFile(archive) as bundle:
            members: dict[str, zipfile.ZipInfo] = {}
            for info in bundle.infolist():
                path = safe_member_name(info)
                key = path.as_posix()
                if key in members:
                    raise RestoreError(f"duplicate ZIP member: {key}")
                members[key] = info
                if info.is_dir():
                    continue
            return members
    except zipfile.BadZipFile as exc:
        raise RestoreError(f"invalid ZIP archive: {archive}") from exc


def validate_archive_checksum(archive: Path, expected: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64 or not all(c in "0123456789abcdefABCDEF" for c in expected):
        raise RestoreError("archive SHA256 must be a 64-character hexadecimal value")
    actual = file_sha256(archive)
    if actual.lower() != expected.lower():
        raise RestoreError(f"archive SHA256 mismatch: expected {expected.lower()}, found {actual}")


def plan_restore(archive: Path, raw: Path = RAW) -> list[tuple[Path, str, zipfile.ZipInfo]]:
    """Validate the whole restore before returning any missing body write plans."""
    if not raw.is_dir():
        raise RestoreError(f"raw snapshot directory is missing: {display_path(raw)}")
    manifests = sorted(path for path in raw.rglob("*.meta.json") if path.is_file())
    if not manifests:
        raise RestoreError(f"no raw snapshot manifests found: {display_path(raw)}")
    members = archive_members(archive)
    plans: list[tuple[Path, str, zipfile.ZipInfo]] = []
    problems: list[str] = []
    expected_members = {
        manifest.with_name(manifest.name.removesuffix(".meta.json")).relative_to(raw.parents[1]).as_posix()
        for manifest in manifests
    }
    for member, info in members.items():
        if info.is_dir():
            continue
        if member.startswith("data/raw/") and not member.endswith(".meta.json") and member not in expected_members:
            problems.append(f"archive contains raw body without a current manifest: {member}")
    for manifest in manifests:
        body = manifest.with_name(manifest.name.removesuffix(".meta.json"))
        try:
            expected_hash, expected_size = read_manifest(manifest)
        except RestoreError as exc:
            problems.append(str(exc))
            continue
        relative = body.relative_to(raw.parents[1]).as_posix()
        if body.exists():
            if not body.is_file() or body.stat().st_size != expected_size or file_sha256(body) != expected_hash:
                problems.append(f"existing body is corrupt and will not be overwritten: {relative}")
            continue
        info = members.get(relative)
        if info is None:
            problems.append(f"archive is missing required raw body: {relative}")
            continue
        if info.is_dir():
            problems.append(f"archive contains a directory instead of required raw body: {relative}")
            continue
        if info.file_size != expected_size:
            problems.append(f"archive size mismatch for {relative}: expected {expected_size}, found {info.file_size}")
            continue
        with zipfile.ZipFile(archive) as bundle, bundle.open(info) as source:
            digest = hashlib.sha256()
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected_hash:
            problems.append(f"archive hash mismatch for {relative}")
            continue
        plans.append((body, relative, info))
    if problems:
        raise RestoreError("restore preflight failed:\n" + "\n".join(problems))
    return plans


def restore(archive: Path, expected_sha256: str, raw: Path = RAW) -> int:
    validate_archive_checksum(archive, expected_sha256)
    plans = plan_restore(archive, raw)
    with zipfile.ZipFile(archive) as bundle:
        for target, label, info in plans:
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".part", dir=target.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as destination, bundle.open(info) as source:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                # link() is atomic and refuses to replace a body created after planning.
                os.link(temporary, target)
                print(f"RESTORED {label}")
            except FileExistsError as exc:
                raise RestoreError(f"refusing to overwrite existing body: {label}") from exc
            finally:
                temporary.unlink(missing_ok=True)
    print(f"Restored {len(plans)} missing raw snapshot bodies.")
    return len(plans)


def descriptor_values(path: Path) -> tuple[str, str, str]:
    try:
        descriptor = json.loads(path.read_text(encoding="utf-8"))
        return descriptor["archive_name"], descriptor["download_url"], descriptor["archive_sha256"]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RestoreError(f"invalid release descriptor {path}: {exc}") from exc


def download(url: str, archive_name: str, expected_sha256: str) -> Path:
    if Path(archive_name).name != archive_name:
        raise RestoreError("release descriptor archive_name must be a filename")
    RUNTIME.mkdir(exist_ok=True)
    target = RUNTIME / archive_name
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(url) as response, temporary.open("wb") as destination:
            shutil.copyfileobj(response, destination, length=1024 * 1024)
        validate_archive_checksum(temporary, expected_sha256)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="local snapshot ZIP")
    parser.add_argument("--sha256", help="required SHA256 for --archive")
    parser.add_argument("--descriptor", type=Path, default=DEFAULT_DESCRIPTOR, help="pinned public release descriptor")
    args = parser.parse_args(argv)
    try:
        if args.archive:
            if not args.sha256:
                raise RestoreError("--sha256 is required with --archive")
            archive, expected = args.archive, args.sha256
        else:
            name, url, expected = descriptor_values(args.descriptor)
            archive = download(url, name, expected)
        restore(archive, expected)
        return 0
    except RestoreError as exc:
        print(f"Snapshot restore failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
