"""Owner-requested e2e audit. Never submits forms. Usage: python e2e_audit.py [outdir] [axe.min.js]"""
import json, sys, os
from playwright.sync_api import sync_playwright
BASE = os.environ["SITE_URL"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "shots"
AXE = open(sys.argv[2]).read() if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
res = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, ctxargs in {"desktop": dict(viewport={"width": 1366, "height": 800}),
                          "mobile": p.devices["iPhone 13"]}.items():
        ctx = b.new_context(**ctxargs, locale=os.environ.get("LOCALE", "en-US"))
        pg = ctx.new_page(); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("requestfailed", lambda r: errs.append("REQFAIL " + r.url))
        pg.goto(BASE, wait_until="load", timeout=45000); pg.wait_for_timeout(2500)
        perf = pg.evaluate("""()=>{const n=performance.getEntriesByType('navigation')[0];
          const lcp=performance.getEntriesByType('largest-contentful-paint').pop();
          return {dcl:n.domContentLoadedEventEnd|0,load:n.loadEventEnd|0,lcp:lcp?lcp.startTime|0:null,
          resources:performance.getEntriesByType('resource').length,
          kb:Math.round(performance.getEntriesByType('resource').reduce((a,r)=>a+(r.transferSize||0),0)/1024)}}""")
        hscroll = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        pg.screenshot(path=f"{OUT}/{name}-fold.png")
        pg.screenshot(path=f"{OUT}/{name}-full.png", full_page=True)
        r = dict(perf=perf, horizontal_overflow=hscroll, console_errors=errs[:15])
        if AXE:
            pg.evaluate(AXE)
            ax = pg.evaluate("axe.run(document,{runOnly:['wcag2a','wcag2aa']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,help:v.help})))")
            r["axe"] = ax
        # nav links
        navs = pg.eval_on_selector_all("nav a[href], header a[href]", "e=>[...new Set(e.map(a=>a.href))]")
        bad = []
        for u in navs[:15]:
            if u.startswith(BASE) and "#" not in u:
                resp = pg.request.get(u)
                if resp.status >= 400: bad.append((u, resp.status))
        r["nav_links_checked"] = len(navs); r["nav_bad"] = bad
        # forms: validation without submit
        forms = pg.eval_on_selector_all("form", """fs=>fs.map(f=>({action:f.action,method:f.method,
          fields:[...f.querySelectorAll('input,textarea,select')].filter(i=>i.type!='hidden').map(i=>({n:i.name,t:i.type,req:i.required,label:!!(i.labels&&i.labels.length)||!!i.getAttribute('aria-label')||!!i.placeholder,vis:!!(i.offsetParent)})),
          submit:!!f.querySelector('[type=submit],button'),visible:!!f.offsetParent}))""")
        r["forms"] = forms
        # tap targets (mobile)
        r["small_tap_targets"] = pg.evaluate("""()=>[...document.querySelectorAll('a,button')].filter(e=>{const b=e.getBoundingClientRect();return b.width>0&&b.height>0&&(b.width<24||b.height<24)}).length""")
        res[name] = r; ctx.close()
    b.close()
json.dump(res, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
