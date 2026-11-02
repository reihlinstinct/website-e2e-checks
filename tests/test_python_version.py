"""Runtime Python-version guards on the CI-invoked scripts."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # runs the guard; no exit on a supported interpreter
    return mod


def test_guards_accept_current():
    _load("report/build_report.py", "build_report")
    _load("e2e/e2e_audit.py", "e2e_audit")


def test_guard_rejects_old(monkeypatch):
    src = (ROOT / "report" / "build_report.py").read_text()
    start = src.index("MIN_PYTHON")
    end = src.index("_check_python_version()") + len("_check_python_version()")
    monkeypatch.setattr(sys, "version_info", (3, 10, 9))
    try:
        exec(src[start:end], {"sys": sys})
    except SystemExit as exc:
        assert "requires Python 3.11+" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("guard did not exit on Python 3.10")
