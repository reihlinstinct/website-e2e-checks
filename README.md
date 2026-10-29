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

Every workflow ends with a `Run summary` job that writes a summary to the top of the run page: which jobs ran, their result and duration, what was skipped and why, the commits and files the run changed, and which checks cover those changes (`.github/ci-coverage-map.json` declares the coverage; files matching no mapping are flagged). The script is `scripts/ci/run_summary.py`.

### Site-specific form tests (private profile)

`SITE_PROFILE_JSON` (a secret, never committed) can describe forms: CSS selector, field selectors and values,
submit selector, expected text and `allow_submit`. See `e2e/site_profile.py`. Without `allow_submit: true` every POST
is aborted, so forms are validated but never submitted. Real submissions need test data and an OK from the site owner.

## Run

    pip install -e .
    SITE_URL=https://example.com pytest -q
    pip install playwright && playwright install chromium
    SITE_URL=https://example.com python e2e/e2e_audit.py shots path/to/axe.min.js
    SITE_URL=https://example.com python e2e/form_validation.py shots

Results (`shots/`, `reports/`) are git-ignored on purpose: they describe a specific site.
Some checks can fail for a given site, and that is the point.

## Private report from CI

This repo is public, so CI never prints findings. The workflow runs everything with output silenced, builds
`report.md` (failures, generic improvement suggestions, passive security results, detected software versions to compare
with public advisories), encrypts it to the certificate in `certs/report-recipient.pem` (CMS, only the holder of the
private key can read it) and uploads only the encrypted `report.p7m`. The public log and step summary show pass/fail counts only.
Passive security checks use normal GET requests and TLS metadata. No scanning, fuzzing, login attempts or load.
`EXPOSED_PATHS` (comma list) overrides which default files are probed.

## CI

`.github/workflows/ci.yml` runs weekly and on demand with `SITE_URL` from a secret.

## Scope and rules

Single-user traffic only. No login, no real form submission, no vulnerability scanning, no load testing.
Deeper testing needs written permission from the site owner.

## Process

Issue per change, PR per change with a full description, squash merge, tests run before merge.
