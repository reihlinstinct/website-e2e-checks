# Accessibility statement

We want website-e2e-checks to be usable by everyone. Our target is WCAG 2.2 level AA for
user-facing content and interfaces.

## What we do

- This repository is a reusable test suite for websites; it ships no end-user web UI of its own, so this statement covers its documentation and outputs.
- The suite itself helps accessibility: its browser audit runs automated WCAG A/AA checks (axe-core via Playwright) against the configured target site.
- In CI the browser audit runs in Chromium today; WebKit coverage is not set up.

## Known limitations

Accessibility work is ongoing. If something blocks you, we want to know.

## Feedback

Report an accessibility problem by opening an issue:
https://github.com/reihlinstinct/website-e2e-checks/issues/new/choose
If the report is sensitive, use a private security advisory instead:
https://github.com/reihlinstinct/website-e2e-checks/security/advisories/new
