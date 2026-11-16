"""Offline unit tests for e2e/site_profile.py (#22).

The page object is a fake recording calls; no browser is launched.
"""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

P = Path(__file__).resolve().parents[1] / "e2e/site_profile.py"
spec = importlib.util.spec_from_file_location("site_profile", P)
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


class FakeLocator:
    def __init__(self, recorder, name):
        self.recorder = recorder
        self.name = name
        self.first = self

    def scroll_into_view_if_needed(self):
        self.recorder.append(("scroll", self.name))

    def fill(self, value):
        self.recorder.append(("fill", self.name, value))

    def click(self):
        self.recorder.append(("click", self.name))

    def screenshot(self, path):
        self.recorder.append(("shot", path))

    def locator(self, selector):
        return FakeLocator(self.recorder, selector)


class FakePage:
    def __init__(self, expect_hits=1):
        self.calls = []
        self.expect_hits = expect_hits

    def locator(self, selector):
        return FakeLocator(self.calls, selector)

    def wait_for_timeout(self, ms):
        self.calls.append(("wait", ms))

    def get_by_text(self, text):
        return type("T", (), {"count": lambda _self: self.expect_hits})()


PROFILE = '{"forms": [{"selector": "form#a", "fields": {"#n": "x"}, ' \
          '"submit": "#go", "expect": "thanks", "allow_submit": false}]}'


class LoadTests(unittest.TestCase):
    def test_default_empty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sp.load(), {"forms": []})

    def test_parses_env_json(self):
        with mock.patch.dict(os.environ, {"SITE_PROFILE_JSON": PROFILE}):
            data = sp.load()
        self.assertEqual(len(data["forms"]), 1)
        self.assertEqual(data["forms"][0]["selector"], "form#a")


class RunFormsTests(unittest.TestCase):
    def run_with(self, page):
        sent = ["https://example.invalid/post"]
        with mock.patch.dict(os.environ, {"SITE_PROFILE_JSON": PROFILE}):
            return sp.run_forms(page, sent)

    def test_expect_found(self):
        page = FakePage(expect_hits=1)
        out = self.run_with(page)
        self.assertEqual(out, [{"form": "profile", "expect_found": True,
                                "submit_allowed": False,
                                "blocked_posts": 1}])
        self.assertIn(("fill", "#n", "x"), page.calls)
        self.assertIn(("click", "#go"), page.calls)

    def test_expect_missing(self):
        page = FakePage(expect_hits=0)
        out = self.run_with(page)
        self.assertFalse(out[0]["expect_found"])

    def test_no_profile_forms(self):
        page = FakePage()
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(sp.run_forms(page, []), [])


if __name__ == "__main__":
    unittest.main()
