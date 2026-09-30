# USYD CODE CITATION ACKNOWLEDGEMENT
# I declare that OpenAI Codex was used to review and revise this file.
# AI-generated or AI-revised material is included in this file.
# See the separate Generative AI and Automated Writing Tools Usage Report
# for the tools, purposes, extent of use and representative prompts.

"""Run tests and bind their evidence to this code/input version before packaging."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev_pipeline.evidence import project_fingerprint
from scripts.verification_evidence import (REPORT_NAME, SCHEMA_VERSION, successful_evidence,
                                           validate_test_evidence, verify_raw_pairs)


def run_tests(root, fingerprint):
    """Run the explicit suite once, with a fresh reporter and isolated selection."""
    for name in ("tests.xml", REPORT_NAME, "test_run.log"):
        (root / "outputs" / name).unlink(missing_ok=True)
    runtime = (root / ".runtime").resolve()
    if not runtime.is_relative_to(root.resolve()):
        raise ValueError("Test temporary directory must remain in the project")
    runtime.mkdir(exist_ok=True)
    basetemp = Path(tempfile.mkdtemp(prefix="pytest-", dir=runtime)).resolve()
    if not basetemp.is_relative_to(runtime):
        raise ValueError("Unsafe test temporary path")
    run_id = uuid.uuid4().hex
    # Do not inherit -k/-m/--lf, injected plugins, or plugin autoload from callers.
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYTEST_")}
    env.update(PYTHONIOENCODING="utf-8", PYTHONPATH=str(root), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    command = [sys.executable, "-m", "pytest", "-q", "-c", str(root / "pytest.ini"),
               "--rootdir=" + str(root), "--confcutdir=" + str(root / "tests"),
               str(root / "tests"), "-o", "addopts=",
               "-o", "junit_family=xunit2", "-p", "scripts.verification_evidence",
               "--junitxml=" + str(root / "outputs/tests.xml"),
               "--verification-report=" + str(root / "outputs" / REPORT_NAME),
               "--verification-run-id=" + run_id, "--verification-fingerprint=" + fingerprint,
               "--basetemp=" + str(basetemp), "-o", "cache_dir=" + str(basetemp / "cache")]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", env=env)
    (root / "outputs/test_run.log").write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    print(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Tests failed; full output saved in outputs/test_run.log")
    return successful_evidence(root, fingerprint, run_id)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    evidence = ROOT / "outputs/test_evidence.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    # A failed verification must not leave an old 'pass' usable by the packager.
    evidence.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "passed": False}), encoding="utf-8", newline="\n")
    for name in ("tests.xml", REPORT_NAME):
        (ROOT / "outputs" / name).unlink(missing_ok=True)
    fingerprint = project_fingerprint()
    verify_raw_pairs(ROOT)
    tests = run_tests(ROOT, fingerprint)
    subprocess.run([sys.executable, "scripts/check_reproducibility.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "ev_pipeline", "validate"], cwd=ROOT, check=True)
    verify_raw_pairs(ROOT)
    if project_fingerprint() != fingerprint:
        raise ValueError("Project changed during verification; rerun against unchanged inputs and code")
    validate_test_evidence(ROOT, tests, fingerprint)
    # Publish success only after every stage passes for the same project version.
    evidence.write_text(json.dumps(tests, indent=2), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
