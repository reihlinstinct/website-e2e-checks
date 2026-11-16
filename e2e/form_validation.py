"""Empty-submit validation on the visible lead form. All POSTs are aborted: nothing is ever sent."""
import sys, os
from site_profile import run_forms, load
from playwright.sync_api import sync_playwright
BASE = os.environ["SITE_URL"]; OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"
ALLOW = any(f.get("allow_submit") for f in load()["forms"])
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 844}, locale=os.environ.get("LOCALE", "en-US"))
    sent = []
    def guard(route):
        if route.request.method == "POST" and not ALLOW: sent.append(route.request.url); route.abort()
        else: route.continue_()
    pg.route("**/*", guard)
    pg.goto(BASE, wait_until="load", timeout=45000); pg.wait_for_timeout(2000)
    f = pg.locator("form:visible").first; f.scroll_into_view_if_needed()
    f.locator("[type=submit],button").first.click(); pg.wait_for_timeout(1500)
    inv = pg.evaluate("[...document.querySelectorAll('form input:invalid')].filter(i=>i.offsetParent).map(i=>i.name)")
    msgs = f.locator("[role=alert], .error, .error-message, .form-message").all_inner_texts()
    print("invalid visible fields:", inv, "| messages:", msgs, "| POST attempts blocked:", sent)
    if load()["forms"]: print("profile forms:", run_forms(pg, sent))
    f.screenshot(path=f"{OUT}/form-empty-submit.png"); b.close()
