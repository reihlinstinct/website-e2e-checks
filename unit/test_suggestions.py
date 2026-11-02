"""Offline checks for the suggestions data module (#22)."""
import importlib.util
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "report/suggestions.py"
spec = importlib.util.spec_from_file_location("suggestions", P)
sug = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sug)


class SuggestionsTests(unittest.TestCase):
    def test_keys_are_test_names(self):
        for key in sug.SUGGESTIONS:
            self.assertTrue(key.startswith("test_"), key)

    def test_values_are_nonempty_strings(self):
        for key, value in sug.SUGGESTIONS.items():
            self.assertIsInstance(value, str)
            self.assertGreater(len(value), 20, key)

    def test_core_checks_have_suggestions(self):
        for key in ("test_home_ok", "test_http_redirects_to_https",
                    "test_security_headers_present", "test_csp_present"):
            self.assertIn(key, sug.SUGGESTIONS)


if __name__ == "__main__":
    unittest.main()
