"""Runtime Python-version guards on the CI-invoked scripts.

Executes ONLY the extracted guard blocks - never the scripts' top-level
code (e2e_audit.py launches Chromium against the live site; importing or
execing it in a test is forbidden). Root-level placement keeps it clear
of tests/conftest.py, which requires SITE_URL.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ("e2e/e2e_audit.py", "report/build_report.py")


def guard_block(path: str) -> str:
    src = (ROOT / path).read_text()
    start = src.index("MIN_PYTHON")
    end = src.rindex("_check_python_version()") + len("_check_python_version()")
    return src[start:end]


def test_both_scripts_have_the_guard_before_any_side_effects():
    for script in SCRIPTS:
        src = (ROOT / script).read_text()
        assert "MIN_PYTHON" in src, script
        # The guard call precedes every other statement after the docstring
        # imports: no env access or heavy import may run before it.
        call = src.rindex("_check_python_version()")
        assert "SITE_URL" not in src or src.index('os.environ["SITE_URL"]') > call
        if script.startswith("e2e/"):
            assert src.index("playwright") > call, script


def test_guards_accept_current():
    for script in SCRIPTS:
        exec(guard_block(script), {"sys": sys})  # no SystemExit on a supported interpreter


def test_guard_rejects_old(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 10, 9))
    for script in SCRIPTS:
        try:
            exec(guard_block(script), {"sys": sys})
        except SystemExit as exc:
            assert "requires Python 3.11+" in str(exc)
        else:  # pragma: no cover
            raise AssertionError(f"guard did not exit on Python 3.10: {script}")
