"""Configurable performance budgets for the live site checks (#4).

`RESPONSE_BUDGET_SECONDS` and `HTML_BUDGET_BYTES` (plain env vars, never
secrets) override the response-time and uncompressed-HTML-size budgets used
by `tests/test_site.py`. Unset or empty keeps the defaults, which match the
previously hard-coded values (3.0 seconds, 500_000 bytes).
"""
import math, os

DEFAULT_RESPONSE_SECONDS = 3.0
DEFAULT_HTML_BYTES = 500_000


def _positive(raw, name, default, cast):
    if raw is None or raw.strip() == "":
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {raw!r}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {raw!r}")
    return value


def response_seconds() -> float:
    """Response-time budget in seconds (`RESPONSE_BUDGET_SECONDS`)."""
    return _positive(os.environ.get("RESPONSE_BUDGET_SECONDS"),
                     "RESPONSE_BUDGET_SECONDS", DEFAULT_RESPONSE_SECONDS, float)


def html_bytes() -> int:
    """Uncompressed HTML size budget in bytes (`HTML_BUDGET_BYTES`)."""
    return _positive(os.environ.get("HTML_BUDGET_BYTES"),
                     "HTML_BUDGET_BYTES", DEFAULT_HTML_BYTES, int)
