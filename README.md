# website-e2e-checks

A reusable, non-intrusive test suite for any website you own or have permission to test.
Point it at a site through configuration and it runs the whole suite. Nothing about the target is stored in this repo.

## What it checks

- `tests/` (HTTP level): availability, HTTP to HTTPS redirect, response time, HTML weight, compression, title and description, single h1, canonical and viewport, image alt text, security headers, TLS expiry, robots.txt and sitemap, internal links (first 40, throttled), presence of forms (never submitted).
- `e2e/` (browser, Playwright + axe): desktop and mobile load, performance timings, WCAG A/AA audit, horizontal overflow, navigation links, small tap targets, form validation with empty submit (every POST is aborted).

## Configuration

| Variable | Required | Meaning |
| --- | --- | --- |
| `SITE_URL` | yes | Target, for example `https://example.com`. In CI it comes from the `SITE_URL` Actions secret. |
| `EXPECT_LANG` | no | Expected `lang` prefix on the html element (for example `en`). Test is skipped when unset. |
| `EXPECT_DIR` | no | Expected `dir` (`ltr` or `rtl`). Skipped when unset. |
| `LOCALE` | no | Browser locale for e2e, default `en-US`. |

## Run

    pip install -e .
    SITE_URL=https://example.com pytest -q
    pip install playwright && playwright install chromium
    SITE_URL=https://example.com python e2e/e2e_audit.py shots path/to/axe.min.js
    SITE_URL=https://example.com python e2e/form_validation.py shots

Results (`shots/`, `reports/`) are git-ignored on purpose: they describe a specific site.
Some checks can fail for a given site, and that is the point.

## CI

`.github/workflows/ci.yml` runs weekly and on demand with `SITE_URL` from a secret.

## Scope and rules

Single-user traffic only. No login, no real form submission, no vulnerability scanning, no load testing.
Deeper testing needs written permission from the site owner.

## Process

Issue per change, PR per change with a full description, squash merge, tests run before merge.
