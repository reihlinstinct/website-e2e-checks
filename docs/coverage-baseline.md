# Coverage baseline (#22)

Recorded 2026-11-02 against default-branch SHA
`c6779110cec454ad074b7d7776db6846fa48aa0b` (pre-PR `main`). Measured
offline only: no live website probes were run as coverage measurement.

## Test command

```sh
coverage run --branch --source=e2e,report,scripts \
  -m pytest --noconftest unit tests/security -q
coverage report --include=e2e/budgets.py --fail-under=80
coverage report --include=e2e/site_profile.py --fail-under=80
coverage report --include=report/suggestions.py --fail-under=80
coverage report --include=report/build_report.py --fail-under=80
coverage report --include=scripts/ci/run_summary.py --fail-under=80
coverage report --include=scripts/security/scorecard_guard.py --fail-under=80
```

The `coverage` job in `validate.yml` runs exactly this on every pull
request, then a combined informational report over the same directories.
`--noconftest` keeps the live-site `tests/conftest.py` (which requires
`SITE_URL`) out of the offline run; `--source` means unimported files
cannot hide from the report.

## Production-only denominator

Measured production code (branch coverage, 103 tests + 21 subtests):

| Module | Stmts | Branch | Cover | Floor |
|---|---|---|---|---|
| `e2e/budgets.py` | 19 | 6 | 100% | >=80% (enforced) |
| `e2e/site_profile.py` | 16 | 4 | 100% | >=80% (enforced) |
| `report/suggestions.py` | 1 | 0 | 100% | >=80% (enforced) |
| `report/build_report.py` | 43 | 14 | 96% | >=80% (enforced) |
| `scripts/ci/run_summary.py` | 373 | 130 | 98% | >=80% (enforced) |
| `scripts/security/scorecard_guard.py` | 214 | 140 | 87% | >=80% (enforced) |
| `e2e/e2e_audit.py` | 43 | 10 | 0% | N/A (see below) |
| `e2e/form_validation.py` | 20 | 2 | 0% | N/A (see below) |

`e2e_audit.py` and `form_validation.py` are top-level Playwright browser
scripts that only run against the live target with a browser installed;
they cannot be imported offline, so they stay in the denominator at an
honest 0% in the combined report (not excluded) and are exercised live by
the weekly `ci.yml` checks. Bringing them under test would need a
loopback browser harness, which is future work outside this issue's
scope. Uncovered lines elsewhere (mostly `->exit` defensive paths, the
`__main__` guard and the 3.11 import-guard raise) are visible in the CI
report with `-m`.

`e2e/budgets.py` was added with #4's PR, so it has no pre-PR baseline;
its row was measured on that PR's head with the same command.

## Suites

- `unit/test_budgets.py` (12 tests): default, empty, override, invalid,
  non-finite and non-positive handling for the two budget env vars.
- `unit/test_site_profile.py` (5 tests): env-JSON loading and
  `run_forms` against a fake recording page object; no browser.
- `unit/test_build_report.py` (7 tests): the module runs `main()` at
  import, so each case loads a fresh copy with patched argv;
  `requests.get` is faked (payload or raising stub), never live.
- `unit/test_suggestions.py` (3 tests): suggestion-table shape.
- `unit/test_run_summary.py` (30 tests): ported from
  parking-report-intake#42; GitHub jobs API mocked, git calls faked.
- `tests/security/test_scorecard_guard.py` (46 tests + 21 subtests):
  pre-existing.

## Excluded from the production denominator (justified)

- `tests/` (live probes and guard suite), `unit/`, `policy/`,
  `test_python_version.py`: test code. `tests/test_site.py` and
  `tests/test_security_passive.py` hit the live target and are never
  part of the coverage measurement per this issue.
- `certs/`, workflows: not Python production code.

Sandbox note: `unit/test_build_report.py` patches `sys.version_info`
only when the interpreter is below 3.11 (the module carries the repo
Python 3.11+ import guard); in CI on 3.13 the shim is a no-op. No live
submissions, credentials, paid runs or remote website sweeps involved.
