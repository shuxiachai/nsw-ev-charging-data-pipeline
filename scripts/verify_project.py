"""Run tests and bind their evidence to this code/input version before packaging."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.evidence import project_fingerprint


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    evidence = ROOT / "outputs/test_evidence.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    fingerprint = project_fingerprint()
    # A failed verification must not leave an old 'pass' usable by the packager.
    evidence.write_text(json.dumps({"passed": False, "project_fingerprint": fingerprint}), encoding="utf-8")
    runtime = (ROOT / ".runtime").resolve()
    if not runtime.is_relative_to(ROOT.resolve()):
        raise ValueError("Test temporary directory must remain in the project")
    runtime.mkdir(exist_ok=True)
    # A fresh project-owned directory avoids shared system-temp ACL conflicts.
    basetemp = Path(tempfile.mkdtemp(prefix="pytest-", dir=runtime)).resolve()
    if not basetemp.is_relative_to(runtime):
        raise ValueError("Unsafe test temporary path")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--junitxml=outputs/tests.xml", "--basetemp=" + str(basetemp),
                             "-o", "cache_dir=" + str(basetemp / "cache")],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    (ROOT / "outputs/test_run.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    print(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Tests failed; full output saved in outputs/test_run.log")
    suites = ET.parse(ROOT / "outputs/tests.xml").getroot().findall("testsuite")
    failures = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    count = sum(int(s.get("tests", 0)) for s in suites)
    if not count or failures:
        raise ValueError("JUnit evidence is empty or contains failures")
    subprocess.run([sys.executable, "scripts/check_reproducibility.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "ev_pipeline", "validate"], cwd=ROOT, check=True)
    if project_fingerprint() != fingerprint:
        raise ValueError("Project changed during verification; rerun against unchanged inputs and code")
    # Publish success only after every stage passes for the same project version.
    evidence.write_text(json.dumps({"passed": True, "tests": count, "project_fingerprint": fingerprint}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
