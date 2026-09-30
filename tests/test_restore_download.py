# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to create this file.
# AI-generated material is included in this file.

"""Download boundaries, owned temporary files and offline restore preflight."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import http.client
import io
import json
from pathlib import Path
import threading
import urllib.error
import zipfile

import pytest

from scripts import restore_snapshot


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    directory = tmp_path / ".runtime"
    monkeypatch.setattr(restore_snapshot, "RUNTIME", directory)
    return directory


def cache_path(runtime: Path, value: bytes, name: str = "snapshot.zip") -> Path:
    return runtime / "snapshots" / digest(value) / name


def write_cache(runtime: Path, expected: bytes, actual: bytes) -> Path:
    path = cache_path(runtime, expected)
    path.parent.mkdir(parents=True)
    path.write_bytes(actual)
    return path


def write_descriptor(tmp_path: Path, **overrides) -> Path:
    values = {
        "archive_name": "snapshot.zip",
        "download_url": "https://example.com/snapshot.zip",
        "archive_sha256": digest(b"snapshot"),
    }
    values.update(overrides)
    path = tmp_path / "release.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def raw_project(tmp_path: Path, monkeypatch, existing: bytes | None = None):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    body = raw / "source.txt"
    body.with_name("source.txt.meta.json").write_text(
        json.dumps({"sha256": digest(b"frozen source"), "bytes": len(b"frozen source")}),
        encoding="utf-8",
    )
    if existing is not None:
        body.write_bytes(existing)
    monkeypatch.setattr(restore_snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(restore_snapshot, "RAW", raw)
    return raw, body


@pytest.mark.parametrize("name", [
    None, 7, [], "", ".", "..", "../snapshot.zip", "a/b.zip", "a\\b.zip",
    "/snapshot.zip", "C:snapshot.zip", "C:\\snapshot.zip", "snapshot.zip:stream",
    "snapshot.zip.", "snapshot.zip ", "NUL.zip", "CON", "a?b.zip", "a\x00b.zip",
])
def test_descriptor_rejects_unsafe_archive_names_before_any_io(tmp_path, runtime, monkeypatch, name):
    path = write_descriptor(tmp_path, archive_name=name)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    with pytest.raises(restore_snapshot.RestoreError, match="archive_name"):
        restore_snapshot.descriptor_values(path)
    with pytest.raises(restore_snapshot.RestoreError, match="archive_name"):
        restore_snapshot.download("https://example.com/a.zip", name, digest(b"snapshot"))
    assert not runtime.exists()


@pytest.mark.parametrize("checksum", [None, 0, [], "", "a" * 63, "a" * 65, "g" * 64, "a" * 63 + " "])
def test_descriptor_rejects_bad_checksum_before_any_io(tmp_path, runtime, monkeypatch, checksum):
    path = write_descriptor(tmp_path, archive_sha256=checksum)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    with pytest.raises(restore_snapshot.RestoreError, match="SHA256"):
        restore_snapshot.descriptor_values(path)
    with pytest.raises(restore_snapshot.RestoreError, match="SHA256"):
        restore_snapshot.download("https://example.com/a.zip", "snapshot.zip", checksum)
    assert not runtime.exists()


@pytest.mark.parametrize("url", [
    None, 8, [], "", "snapshot.zip", "//example.com/a.zip", "file:///snapshot.zip",
    "ftp://example.com/a.zip", "https:///snapshot.zip", "https://", "https://[bad/a.zip",
    "https://example.com:bad/a.zip", "https://example.com:99999/a.zip",
    "https://example.com/with space.zip", "https://example.com/a\n.zip",
    "https://example.com\\evil/a.zip", "https://user:password@example.com/a.zip",
    "https://example.com/档案.zip",
])
def test_descriptor_rejects_invalid_urls_before_any_io(tmp_path, runtime, monkeypatch, url):
    path = write_descriptor(tmp_path, download_url=url)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    with pytest.raises(restore_snapshot.RestoreError, match=r"HTTP\(S\)"):
        restore_snapshot.descriptor_values(path)
    with pytest.raises(restore_snapshot.RestoreError, match=r"HTTP\(S\)"):
        restore_snapshot.download(url, "snapshot.zip", digest(b"snapshot"))
    assert not runtime.exists()


@pytest.mark.parametrize("value", [None, [], {}, {"archive_name": "snapshot.zip"}])
def test_descriptor_rejects_missing_fields_and_wrong_object_type(tmp_path, value):
    path = tmp_path / "release.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(restore_snapshot.RestoreError, match="invalid release descriptor"):
        restore_snapshot.descriptor_values(path)


@pytest.mark.parametrize("value", ["", "{malformed", "\ufeff{}"])
def test_descriptor_rejects_malformed_json(tmp_path, value):
    path = tmp_path / "release.json"
    path.write_text(value, encoding="utf-8")
    with pytest.raises(restore_snapshot.RestoreError, match="invalid release descriptor"):
        restore_snapshot.descriptor_values(path)


def test_verified_cache_reuse_never_opens_network(runtime, monkeypatch):
    expected = b"verified archive"
    target = write_cache(runtime, expected, expected)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    result = restore_snapshot.download("https://example.com/snapshot.zip", "snapshot.zip", digest(expected).upper())
    assert result == target
    assert result.read_bytes() == expected
    assert list(runtime.rglob("*.part")) == []


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_corrupt_cache_is_refreshed_only_after_download_verification(runtime, monkeypatch, scheme):
    expected = b"verified archive"
    target = write_cache(runtime, expected, b"corrupt previous archive")
    calls = []

    def open_response(url, *, timeout):
        calls.append((url, timeout))
        assert target.read_bytes() == b"corrupt previous archive"
        return io.BytesIO(expected)

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", open_response)
    url = f"{scheme}://example.com/snapshot.zip"
    result = restore_snapshot.download(url, "snapshot.zip", digest(expected))
    assert calls == [(url, restore_snapshot.HTTP_TIMEOUT_SECONDS)]
    assert 0 < restore_snapshot.HTTP_TIMEOUT_SECONDS <= 120
    assert result == target
    assert target.read_bytes() == expected
    assert list(runtime.rglob("*.part")) == []


@pytest.mark.parametrize("interrupt", [False, True])
def test_partial_download_preserves_old_cache_and_cleans_owned_file(runtime, monkeypatch, interrupt):
    expected = b"complete verified archive"
    target = write_cache(runtime, expected, b"old cache")

    class PartialResponse(io.BytesIO):
        def read(self, size=-1):
            block = super().read(size)
            if not block and interrupt:
                raise http.client.IncompleteRead(b"partial", len(expected))
            return block

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: PartialResponse(b"partial"))
    with pytest.raises(restore_snapshot.RestoreError, match="cannot download|SHA256 mismatch"):
        restore_snapshot.download("https://example.com/snapshot.zip", "snapshot.zip", digest(expected))
    assert target.read_bytes() == b"old cache"
    assert list(runtime.rglob("*.part")) == []


def test_failed_parallel_download_cannot_remove_another_calls_active_temp(runtime, monkeypatch):
    expected = b"verified concurrent archive"
    target = write_cache(runtime, expected, b"old cache")
    active = threading.Event()
    finish = threading.Event()
    observed = []

    class BlockingResponse(io.BytesIO):
        def read(self, size=-1):
            active.set()
            assert finish.wait(timeout=10), "test did not release active download"
            return super().read(size)

    def open_response(url, *, timeout):
        if url.endswith("active.zip"):
            return BlockingResponse(expected)
        assert active.wait(timeout=10), "active download did not start"
        observed.extend(target.parent.glob("*.part"))
        assert len(observed) == 2
        assert observed[0] != observed[1]
        raise urllib.error.URLError("second transfer failed")

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", open_response)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(restore_snapshot.download, "https://example.com/active.zip", "snapshot.zip", digest(expected))
        second = pool.submit(restore_snapshot.download, "https://example.com/failing.zip", "snapshot.zip", digest(expected))
        try:
            with pytest.raises(restore_snapshot.RestoreError, match="second transfer failed"):
                second.result(timeout=10)
            remaining = list(target.parent.glob("*.part"))
            assert len(remaining) == 1
            assert remaining[0] in observed
            assert target.read_bytes() == b"old cache"
        finally:
            finish.set()
        assert first.result(timeout=10).read_bytes() == expected
    assert target.read_bytes() == expected
    assert list(runtime.rglob("*.part")) == []


def test_concurrent_distinct_checksums_keep_both_returned_archives_valid(runtime, monkeypatch):
    barrier = threading.Barrier(2)
    payloads = {"https://example.com/one.zip": b"first archive", "https://example.com/two.zip": b"second archive"}

    def open_response(url, *, timeout):
        barrier.wait(timeout=10)
        return io.BytesIO(payloads[url])

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", open_response)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [(value, pool.submit(restore_snapshot.download, url, "snapshot.zip", digest(value)))
                   for url, value in payloads.items()]
        results = [(value, future.result(timeout=10)) for value, future in futures]
    assert results[0][1] != results[1][1]
    for value, path in results:
        assert path.read_bytes() == value
        restore_snapshot.validate_archive_checksum(path, digest(value))
    assert list(runtime.rglob("*.part")) == []


@pytest.mark.parametrize("error", [
    TimeoutError("timed out"),
    urllib.error.URLError("offline"),
    urllib.error.HTTPError("https://example.com/snapshot.zip", 503, "Unavailable", {}, None),
    OSError("disk unavailable"),
    http.client.IncompleteRead(b"partial", 10),
])
def test_download_errors_return_exit_one_without_traceback(tmp_path, runtime, monkeypatch, capsys, error):
    raw_project(tmp_path, monkeypatch)
    descriptor = write_descriptor(tmp_path)

    def fail_open(*args, **kwargs):
        raise error

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", fail_open)
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 1
    captured = capsys.readouterr()
    assert "Snapshot restore failed: cannot download snapshot snapshot.zip:" in captured.out
    assert "Traceback" not in captured.out
    assert captured.err == ""
    assert list(runtime.rglob("*.part")) == []


def test_atomic_publish_failure_preserves_old_cache_and_cleans_temp(tmp_path, runtime, monkeypatch, capsys):
    raw_project(tmp_path, monkeypatch)
    expected = b"snapshot"
    target = write_cache(runtime, expected, b"old cache")
    descriptor = write_descriptor(tmp_path)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(expected))

    def fail_replace(source, destination):
        assert Path(source).read_bytes() == expected
        assert destination == target
        raise OSError("cannot publish cache")

    monkeypatch.setattr(restore_snapshot.os, "replace", fail_replace)
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 1
    captured = capsys.readouterr()
    assert "cannot publish cache" in captured.out
    assert "Traceback" not in captured.out
    assert captured.err == ""
    assert target.read_bytes() == b"old cache"
    assert list(runtime.rglob("*.part")) == []


def test_local_archive_file_error_returns_exit_one(tmp_path, monkeypatch, capsys):
    raw_project(tmp_path, monkeypatch)
    assert restore_snapshot.main(["--archive", str(tmp_path / "missing.zip"), "--sha256", "0" * 64]) == 1
    captured = capsys.readouterr()
    assert "Snapshot restore failed:" in captured.out
    assert "Traceback" not in captured.out
    assert captured.err == ""


def test_complete_raw_preflight_skips_network_and_cache_creation(tmp_path, runtime, monkeypatch, capsys):
    _, body = raw_project(tmp_path, monkeypatch, existing=b"frozen source")
    descriptor = write_descriptor(tmp_path)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 0
    assert "no bodies need restoring" in capsys.readouterr().out
    assert body.read_bytes() == b"frozen source"
    assert not runtime.exists()


def test_complete_raw_still_rejects_malformed_release_descriptor(tmp_path, runtime, monkeypatch, capsys):
    raw_project(tmp_path, monkeypatch, existing=b"frozen source")
    descriptor = write_descriptor(tmp_path, archive_sha256=None)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 1
    assert "invalid release descriptor" in capsys.readouterr().out
    assert not runtime.exists()


@pytest.mark.parametrize("problem", ["corrupt", "bad manifest", "orphan", "directory"])
def test_raw_preflight_rejects_existing_problems_before_network(tmp_path, runtime, monkeypatch, capsys, problem):
    raw, body = raw_project(tmp_path, monkeypatch, existing=b"frozen source")
    if problem == "corrupt":
        body.write_bytes(b"corrupt body")
    elif problem == "bad manifest":
        body.with_name("source.txt.meta.json").write_text("{}", encoding="utf-8")
    elif problem == "orphan":
        (raw / "orphan.txt").write_bytes(b"untracked")
    else:
        body.unlink()
        body.mkdir()
    descriptor = write_descriptor(tmp_path)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 1
    assert "restore preflight failed" in capsys.readouterr().out
    assert not runtime.exists()
    if problem == "corrupt":
        assert body.read_bytes() == b"corrupt body"


@pytest.mark.parametrize("exists", [False, True])
def test_missing_or_empty_raw_cannot_take_offline_shortcut(tmp_path, runtime, monkeypatch, capsys, exists):
    raw = tmp_path / "data" / "raw"
    if exists:
        raw.mkdir(parents=True)
    monkeypatch.setattr(restore_snapshot, "RAW", raw)
    descriptor = write_descriptor(tmp_path)
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 1
    assert "Snapshot restore failed:" in capsys.readouterr().out
    assert not runtime.exists()


def test_missing_body_downloads_then_restores_only_that_body(tmp_path, runtime, monkeypatch, capsys):
    raw, missing = raw_project(tmp_path, monkeypatch)
    existing = raw / "existing.txt"
    existing.write_bytes(b"existing body")
    existing.with_name("existing.txt.meta.json").write_text(
        json.dumps({"sha256": digest(existing.read_bytes()), "bytes": existing.stat().st_size}), encoding="utf-8",
    )
    code = tmp_path / "README.md"
    code.write_bytes(b"code preserved")
    database = tmp_path / "data" / "processed" / "ev_chargers.duckdb"
    database.parent.mkdir()
    database.write_bytes(b"database preserved")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("data/raw/source.txt", b"frozen source")
        archive.writestr("README.md", b"do not restore")
        archive.writestr("data/processed/ev_chargers.duckdb", b"do not restore")
    payload = buffer.getvalue()
    descriptor = write_descriptor(tmp_path, archive_sha256=digest(payload))
    calls = []

    def open_response(url, *, timeout):
        calls.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", open_response)
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 0
    assert len(calls) == 1
    assert "Restored 1 missing raw snapshot bodies." in capsys.readouterr().out
    assert missing.read_bytes() == b"frozen source"
    assert existing.read_bytes() == b"existing body"
    assert code.read_bytes() == b"code preserved"
    assert database.read_bytes() == b"database preserved"
    assert list(runtime.rglob("*.part")) == []
    assert list(raw.rglob("*.part")) == []


def test_verified_cache_restores_missing_body_without_network(tmp_path, runtime, monkeypatch):
    _, missing = raw_project(tmp_path, monkeypatch)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("data/raw/source.txt", b"frozen source")
    payload = buffer.getvalue()
    write_cache(runtime, payload, payload)
    descriptor = write_descriptor(tmp_path, archive_sha256=digest(payload))
    monkeypatch.setattr(restore_snapshot.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network reached"))
    assert restore_snapshot.main(["--descriptor", str(descriptor)]) == 0
    assert missing.read_bytes() == b"frozen source"
