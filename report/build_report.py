"""Build a private Markdown report from junit XML (+ optional e2e JSON). Never print the report to logs.
Usage: python report/build_report.py junit.xml [e2e_report.json] > report.md ; prints counts to stderr."""
import json, os, re, sys, xml.etree.ElementTree as ET, requests
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from suggestions import SUGGESTIONS

def main():
    root = ET.parse(sys.argv[1]).getroot()
    rows, p, f, s = [], 0, 0, 0
    for tc in root.iter("testcase"):
        name = re.sub(r"\[.*\]$", "", tc.get("name"))
        if tc.find("skipped") is not None: s += 1; status = "skipped"
        elif tc.find("failure") is not None or tc.find("error") is not None:
            f += 1; status = "FAIL"
        else: p += 1; status = "pass"
        node = tc.find("failure")
        rows.append((tc.get("name"), status, SUGGESTIONS.get(name, "") if status == "FAIL" else "", (node.get("message") or "")[:200] if node is not None else ""))
    out = [f"# Site check report\n\nPassed {p}, failed {f}, skipped {s}.\n", "## Failures and suggestions\n"]
    out += [f"- **{n}**: {sug}\n  - detail: {d}" for n, st, sug, d in rows if st == "FAIL"] or ["- none"]
    if len(sys.argv) > 2:
        e = json.load(open(sys.argv[2]))
        out.append("\n## Browser audit\n")
        for dev, r in e.items():
            out.append(f"- {dev}: load {r['perf']['load']} ms, {r['perf']['resources']} requests, {r['perf']['kb']} KB, overflow={r['horizontal_overflow']}, small tap targets={r['small_tap_targets']}")
            for v in r.get("axe", []):
                out.append(f"  - a11y {v['impact']}: {v['help']} ({v['n']} elements). Fix per WCAG guidance.")
    try:
        html = requests.get(os.environ["SITE_URL"], headers={"User-Agent": "website-e2e-checks/0.1"}, timeout=20).text
        gen = set(re.findall(r'<meta name="generator" content="([^"]+)"', html, re.I))
        libs = sorted(set(re.findall(r"/(?:plugins|themes)/([a-z0-9_-]+)/[^\"' ]*?\?ver=([0-9][0-9a-z.\-]*)", html, re.I)))
        out.append("\n## Detected software (passive, from public page source)\n")
        out += [f"- generator: {g}" for g in sorted(gen)] + [f"- {n} {v}" for n, v in libs]
        out.append("Compare these versions with public security advisories for each component; no exploitation was attempted.")
    except Exception as exc:
        out.append(f"\n(software detection skipped: {type(exc).__name__})")
    out.append("\n## All checks\n")
    out += [f"- {st}: {n}" for n, st, _, _ in rows]
    print("\n".join(out))
    print(f"passed={p} failed={f} skipped={s}", file=sys.stderr)

main()
