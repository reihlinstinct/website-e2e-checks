"""Offline unit tests for e2e/budgets.py (#4): env-configurable budgets."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

P = Path(__file__).resolve().parents[1] / "e2e/budgets.py"
spec = importlib.util.spec_from_file_location("budgets", P)
budgets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budgets)

SECONDS = "RESPONSE_BUDGET_SECONDS"
BYTES = "HTML_BUDGET_BYTES"


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self._patcher = mock.patch.dict(os.environ)
        self._patcher.start()
        os.environ.pop(SECONDS, None)
        os.environ.pop(BYTES, None)

    def tearDown(self):
        self._patcher.stop()

    def test_defaults_when_unset(self):
        self.assertEqual(budgets.response_seconds(), 3.0)
        self.assertEqual(budgets.html_bytes(), 500_000)

    def test_empty_string_keeps_default(self):
        os.environ[SECONDS] = ""
        os.environ[BYTES] = ""
        self.assertEqual(budgets.response_seconds(), 3.0)
        self.assertEqual(budgets.html_bytes(), 500_000)

    def test_whitespace_only_keeps_default(self):
        os.environ[SECONDS] = "   "
        self.assertEqual(budgets.response_seconds(), 3.0)

    def test_valid_response_override(self):
        os.environ[SECONDS] = "1.5"
        self.assertEqual(budgets.response_seconds(), 1.5)

    def test_valid_response_override_int_form(self):
        os.environ[SECONDS] = "5"
        self.assertEqual(budgets.response_seconds(), 5.0)

    def test_valid_html_override(self):
        os.environ[BYTES] = "250000"
        self.assertEqual(budgets.html_bytes(), 250_000)

    def test_invalid_response_raises_with_var_name(self):
        os.environ[SECONDS] = "fast"
        with self.assertRaisesRegex(ValueError, SECONDS):
            budgets.response_seconds()

    def test_invalid_html_raises_with_var_name(self):
        os.environ[BYTES] = "half a meg"
        with self.assertRaisesRegex(ValueError, BYTES):
            budgets.html_bytes()

    def test_html_rejects_float_form(self):
        os.environ[BYTES] = "12.5"
        with self.assertRaisesRegex(ValueError, BYTES):
            budgets.html_bytes()

    def test_zero_and_negative_rejected(self):
        for name, fn in ((SECONDS, budgets.response_seconds), (BYTES, budgets.html_bytes)):
            for bad in ("0", "-1"):
                os.environ[name] = bad
                with self.assertRaisesRegex(ValueError, "positive"):
                    fn()


class BudgetRegressionTests(unittest.TestCase):
    """The live checks must keep passing when the override relaxes a budget
    a hard-coded value would have blown through (#4)."""

    def setUp(self):
        self._patcher = mock.patch.dict(os.environ)
        self._patcher.start()
        os.environ.pop(SECONDS, None)

    def tearDown(self):
        self._patcher.stop()

    def test_relaxed_budget_accepts_slow_response(self):
        os.environ[SECONDS] = "10"
        elapsed_s = 4.2  # over the old hard-coded 3.0
        self.assertLess(elapsed_s, budgets.response_seconds())


if __name__ == "__main__":
    unittest.main()
