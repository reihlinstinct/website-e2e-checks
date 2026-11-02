"""Offline unit tests for report/build_report.py (#22).

The module runs main() at import, so every test loads a fresh copy with
patched argv and captures stdout. requests.get is faked (loopback-style
payloads or a raising stub): no live site is ever contacted. A missing
SITE_URL also exercises the built-in degradation branch.

Sandbox note: the module carries the repo-standard Python 3.11+ import
guard; the loader patches sys.version_info only when the interpreter is
older, which is a no-op in CI (3.13).
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

P = Path(__file__).resolve().parents[1] / "report/build_report.py"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuite>
  <testcase name="test_home_ok" classname="tests.test_site"/>
  <testcase name="test_csp_present" classname="tests.test_security_passive">
    <failure message="missing header">details</failure>
  </testcase>
  <testcase name="test_html_weight_under_budget[desktop]" classname="tests.test_site">
    <failure message="1234 &gt; budget"/>
  </testcase>
  <testcase name="test_internal_links_ok" classname="tests.test_site">
    <skipped message="slow"/>
  </testcase>
  <testcase name="test_broken" classname="tests.test_site">
    <error message="boom"/>
  </testcase>
</testsuite>
"""

E2E_JSON = {"desktop": {
    "perf": {"load": 900, "resources": 42, "kb": 512},
    "horizontal_overflow": False,
    "small_tap_targets": 3,
    "axe": [{"impact": "serious", "help": "Images must have alt", "n": 2}],
}}

HTML = ('<html><head><meta name="generator" content="WordPress 6.7">'
        '<script src="/plugins/akismet/x.js?ver=5.3"></script>'
        '<script src="/themes/twenty/style.css?ver=2.0"></script>'
        '</head></html>')


class FakeResp:
    text = HTML


def load_report(argv, env=None, get=None):
    """Fresh module load; main() runs once. Returns (stdout, stderr)."""
    env = env or {}
    spec = importlib.util.spec_from_file_location(
        "build_report_fresh_" + str(len(sys.modules)), P)
    m = importlib.util.module_from_spec(spec)
    out, err = io.StringIO(), io.StringIO()
    guard = (mock.patch.object(sys, "version_info", (3, 11, 0, "final", 0))
             if sys.version_info < (3, 11) else contextlib.nullcontext())
    env_patches = {k: v for k, v in env.items()}
    getters = (mock.patch("requests.get", side_effect=get)
               if get is not None else contextlib.nullcontext())
    with guard, mock.patch.object(sys, "argv", argv), \
            mock.patch.dict(os.environ, env_patches, clear=False), \
            getters, \
            contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err):
        spec.loader.exec_module(m)
    return out.getvalue(), err.getvalue()


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.junit = Path(self.tmp.name) / "junit.xml"
        self.junit.write_text(JUNIT, encoding="utf-8")
        self.e2e = Path(self.tmp.name) / "e2e.json"
        self.e2e.write_text(json.dumps(E2E_JSON), encoding="utf-8")

    def test_counts_and_statuses(self):
        out, err = load_report(["build_report.py", str(self.junit)],
                               env={"SITE_URL": "https://x.example.invalid"},
                               get=lambda *a, **k: FakeResp())
        self.assertIn("Passed 1, failed 3, skipped 1.", out)
        self.assertIn("passed=1 failed=3 skipped=1", err)
        self.assertIn("- pass: test_home_ok", out)
        self.assertIn("- FAIL: test_csp_present", out)
        self.assertIn("- FAIL: test_html_weight_under_budget[desktop]", out)
        self.assertIn("- skipped: test_internal_links_ok", out)
        self.assertIn("- FAIL: test_broken", out)

    def test_suggestions_keyed_on_unparametrized_name(self):
        out, _ = load_report(["build_report.py", str(self.junit)],
                             env={"SITE_URL": "https://x.example.invalid"},
                             get=lambda *a, **k: FakeResp())
        # the [desktop] suffix is stripped before the suggestions lookup
        self.assertIn("Cut HTML size", out)
        self.assertIn("Add a Content-Security-Policy", out)
        # an unknown failing test gets an empty suggestion; an error-only
        # testcase (no <failure> node) gets an empty detail
        self.assertIn("- **test_broken**: \n  - detail: \n", out)

    def test_no_failures_lists_none(self):
        passing = self.junit.parent / "passing.xml"
        passing.write_text(
            '<?xml version="1.0"?><testsuite>'
            '<testcase name="test_home_ok"/></testsuite>',
            encoding="utf-8")
        out, err = load_report(["build_report.py", str(passing)],
                               env={"SITE_URL": "https://x.example.invalid"},
                               get=lambda *a, **k: FakeResp())
        self.assertIn("Passed 1, failed 0, skipped 0.", out)
        self.assertIn("- none", out)

    def test_e2e_section(self):
        out, _ = load_report(
            ["build_report.py", str(self.junit), str(self.e2e)],
            env={"SITE_URL": "https://x.example.invalid"},
            get=lambda *a, **k: FakeResp())
        self.assertIn("## Browser audit", out)
        self.assertIn("desktop: load 900 ms, 42 requests, 512 KB, "
                      "overflow=False, small tap targets=3", out)
        self.assertIn("a11y serious: Images must have alt (2 elements)", out)

    def test_software_detection_from_page_source(self):
        out, _ = load_report(["build_report.py", str(self.junit)],
                             env={"SITE_URL": "https://x.example.invalid"},
                             get=lambda *a, **k: FakeResp())
        self.assertIn("## Detected software", out)
        self.assertIn("- generator: WordPress 6.7", out)
        self.assertIn("- akismet 5.3", out)
        self.assertIn("- twenty 2.0", out)
        self.assertIn("no exploitation was attempted", out)

    def test_detection_degrades_without_site_url(self):
        env = dict(os.environ)
        env.pop("SITE_URL", None)
        with mock.patch.dict(os.environ, env, clear=True):
            out, _ = load_report(["build_report.py", str(self.junit)])
        self.assertIn("(software detection skipped: KeyError)", out)

    def test_detection_degrades_on_request_failure(self):
        out, _ = load_report(["build_report.py", str(self.junit)],
                             env={"SITE_URL": "https://x.example.invalid"},
                             get=ConnectionError("down"))
        self.assertIn("(software detection skipped: ConnectionError)", out)


if __name__ == "__main__":
    unittest.main()
