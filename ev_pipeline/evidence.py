"""Bind validation evidence to exact project inputs and executable source files."""
from hashlib import sha256
from .acquire import ROOT, RAW


def project_fingerprint():
    paths = [ROOT / "requirements.txt", ROOT / "pytest.ini"]
    for directory, suffix in [("ev_pipeline", ".py"), ("scripts", ".py"), ("tests", ".py"), ("sql", ".sql"), ("config", ".json")]:
        paths.extend((ROOT / directory).rglob("*" + suffix))
    paths.extend(RAW.rglob("*.meta.json"))
    hashes = {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    digest = sha256()
    for name, value in sorted(hashes.items()):
        digest.update((name + "\0" + value + "\n").encode())
    return digest.hexdigest()
