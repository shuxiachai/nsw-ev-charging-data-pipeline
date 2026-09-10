"""Failure-path checks for immutable source downloads; no network calls."""
from hashlib import sha256
import json
from pathlib import Path

import pytest
import requests

from ev_pipeline import acquire


URL = "https://example.test/reviewed-source.pdf"


class Response:
    url = URL
    headers = {"ETag": '"source-version"'}

    def __init__(self, chunks):
        self.chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


class Session:
    def __init__(self, chunks):
        self.chunks = chunks
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, **kwargs):
        assert url == URL
        return Response(self.chunks)


def serve(monkeypatch, chunks):
    monkeypatch.setattr(acquire, "session", lambda: Session(chunks))


def test_interrupted_stream_does_not_leave_a_cached_or_partial_input(tmp_path, monkeypatch):
    serve(monkeypatch, [b"first chunk", requests.ConnectionError("stream interrupted")])
    path = tmp_path / "source.pdf"
    with pytest.raises(requests.ConnectionError, match="interrupted"):
        acquire.fetch(URL, path)
    assert list(tmp_path.iterdir()) == []


def test_expected_review_hash_rejects_changed_download_before_installation(tmp_path, monkeypatch):
    serve(monkeypatch, [b"new upstream revision"])
    path = tmp_path / "source.pdf"
    with pytest.raises(ValueError, match="Reviewed source SHA-256 mismatch"):
        acquire.fetch(URL, path, expected_sha256=sha256(b"reviewed bytes").hexdigest())
    assert list(tmp_path.iterdir()) == []


def test_expected_review_hash_also_checks_existing_cache(tmp_path, monkeypatch):
    serve(monkeypatch, [b"cached bytes"])
    path = tmp_path / "source.pdf"
    acquire.fetch(URL, path)
    with pytest.raises(ValueError, match="Reviewed source SHA-256 mismatch"):
        acquire.fetch(URL, path, offline=True, expected_sha256=sha256(b"different review").hexdigest())
    assert path.read_bytes() == b"cached bytes"


def test_missing_cached_bytes_are_restored_only_from_the_original_snapshot(tmp_path, monkeypatch):
    serve(monkeypatch, [b"original bytes"])
    path = tmp_path / "source.pdf"
    acquire.fetch(URL, path)
    meta = path.with_name(path.name + ".meta.json")
    original_manifest = meta.read_bytes()
    path.unlink()
    serve(monkeypatch, [b"changed upstream bytes"])
    with pytest.raises(ValueError, match="Cache source/hash mismatch"):
        acquire.fetch(URL, path)
    assert not path.exists() and meta.read_bytes() == original_manifest
    assert not list(tmp_path.glob("*.part"))
    serve(monkeypatch, [b"original bytes"])
    acquire.fetch(URL, path)
    assert path.read_bytes() == b"original bytes"
    assert meta.read_bytes() == original_manifest


def test_metadata_failure_never_installs_untracked_source_bytes(tmp_path, monkeypatch):
    serve(monkeypatch, [b"original bytes"])
    path = tmp_path / "source.pdf"
    original_write = Path.write_text

    def fail_metadata(self, *args, **kwargs):
        if self.name.endswith(".meta.json.part"):
            raise OSError("manifest storage failed")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_metadata)
    with pytest.raises(OSError, match="manifest storage"):
        acquire.fetch(URL, path)
    assert list(tmp_path.iterdir()) == []


def test_failed_final_rename_leaves_recoverable_pinned_manifest(tmp_path, monkeypatch):
    serve(monkeypatch, [b"original bytes"])
    path = tmp_path / "source.pdf"
    original_replace = Path.replace

    def fail_data_install(self, target):
        if self == path.with_name(path.name + ".part"):
            raise OSError("data install failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_data_install)
    with pytest.raises(OSError, match="data install"):
        acquire.fetch(URL, path)
    assert not path.exists() and not list(tmp_path.glob("*.part"))
    meta = path.with_name(path.name + ".meta.json")
    assert json.loads(meta.read_text())["sha256"] == sha256(b"original bytes").hexdigest()
    original_manifest = meta.read_bytes()
    monkeypatch.setattr(Path, "replace", original_replace)
    acquire.fetch(URL, path)
    assert path.read_bytes() == b"original bytes" and meta.read_bytes() == original_manifest


def test_cache_manifest_byte_count_is_verified(tmp_path, monkeypatch):
    serve(monkeypatch, [b"original bytes"])
    path = tmp_path / "source.pdf"
    acquire.fetch(URL, path)
    meta = path.with_name(path.name + ".meta.json")
    metadata = json.loads(meta.read_text())
    metadata["bytes"] += 1
    meta.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Cache source/hash mismatch"):
        acquire.fetch(URL, path, offline=True)
