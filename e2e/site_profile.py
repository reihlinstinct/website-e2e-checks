"""Optional private site profile for site-specific form tests.

SITE_PROFILE_JSON (an env var / Actions secret, never committed) holds JSON like:
{"forms": [{"selector": "<css>", "fields": {"<css>": "<value>"}, "submit": "<css>",
            "expect": "<text>", "allow_submit": false}]}
Submission happens only when allow_submit is true; otherwise every POST is aborted.
"""
import json, os


def load():
    raw = os.environ.get("SITE_PROFILE_JSON")
    return json.loads(raw) if raw else {"forms": []}


def run_forms(page, sent):
    out = []
    for spec in load()["forms"]:
        form = page.locator(spec["selector"]).first
        form.scroll_into_view_if_needed()
        for sel, val in spec.get("fields", {}).items():
            form.locator(sel).fill(val)
        form.locator(spec["submit"]).click()
        page.wait_for_timeout(1500)
        ok = spec.get("expect") is None or page.get_by_text(spec["expect"]).count() > 0
        out.append({"form": "profile", "expect_found": ok, "submit_allowed": bool(spec.get("allow_submit")), "blocked_posts": len(sent)})
    return out
