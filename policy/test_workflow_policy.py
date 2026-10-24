"""Policy checks for multi-target secrecy. Run on every pull request, no target needed.

They guard the rules of this public repo: a target is only ever read from an Actions secret,
nothing about it reaches logs or artifacts in clear text, and each target's detailed report is
encrypted to its own recipient certificate (never shared across targets).
"""
import os, re, subprocess, sys, tempfile, pathlib
import pytest, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
ALLOWED_HOSTS = {"cdnjs.cloudflare.com", "github.com", "docs.github.com", "example.com", "127.0.0.1"}
# job -> (secret holding its target, the only recipient certificate it may use)
TARGETS = {
    "checks": ("SITE_URL", "certs/report-recipient.pem"),
    "checks-b": ("SITE_URL_B", "certs/private-report-recipient.pem"),
}


def site_jobs():
    out = {}
    for wf in WORKFLOWS:
        for name, job in (yaml.safe_load(wf.read_text()).get("jobs") or {}).items():
            if "SITE_URL" in (job.get("env") or {}):
                out[name] = (wf, job)
    return out


def steps_text(job):
    return "\n".join(str(s.get("run", "")) + " " + str(s.get("uses", "")) + " " + str(s.get("with", "")) for s in job["steps"])


def test_workflows_parse_and_define_expected_jobs():
    assert WORKFLOWS, "no workflows found"
    assert set(TARGETS) <= set(site_jobs())


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_target_comes_only_from_its_own_secret(name):
    _, job = site_jobs()[name]
    secret = TARGETS[name][0]
    assert job["env"]["SITE_URL"].replace(" ", "") == "${{secrets.%s}}" % secret


def test_no_literal_hosts_in_repo_files_except_allowlist():
    bad = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or {".git", "__pycache__", ".pytest_cache"} & set(p.parts) or p.suffix in {".pem", ".png", ".jpg", ".pyc"}:
            continue
        if p.name == "test_workflow_policy.py":
            continue
        for host in re.findall(r"https?://([A-Za-z0-9.-]+)", p.read_text(errors="ignore")):
            if host not in ALLOWED_HOSTS and "{" not in host and not host.endswith(".invalid"):
                bad.append((str(p.relative_to(ROOT)), host))
    assert not bad, bad


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_each_target_uses_only_its_own_recipient_certificate(name):
    _, job = site_jobs()[name]
    text = steps_text(job)
    own = TARGETS[name][1]
    others = {c for n, (_, c) in TARGETS.items() if n != name}
    assert own in text, "report must be encrypted to this target's own certificate"
    assert not any(o in text for o in others), "certificate shared across targets"


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_artifacts_are_encrypted_only(name):
    _, job = site_jobs()[name]
    steps = job["steps"]
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads, "private detailed report must be retained as an encrypted artifact"
    for i in uploads:
        assert str(steps[i]["with"]["path"]).strip().endswith(".p7m")
        before = "\n".join(str(s.get("run", "")) for s in steps[:i])
        assert "openssl cms -encrypt" in before


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_nothing_prints_the_target_or_raw_results(name):
    _, job = site_jobs()[name]
    text = steps_text(job)
    assert "set -x" not in text and "printenv" not in text and not re.search(r"\benv\b\s*(\||$)", text, re.M)
    assert not re.search(r"(echo|printf|cat)[^\n]*SITE_URL", text)
    for line in text.splitlines():
        if re.search(r"\b(pytest|playwright install|e2e_audit\.py)\b", line):
            assert ">/dev/null 2>&1" in line, line
    summaries = [l for l in text.splitlines() if "GITHUB_STEP_SUMMARY" in l]
    assert summaries and all("reports/counts.txt" in l for l in summaries)
    assert "reports/report.md" not in " ".join(summaries)


def test_certificates_are_valid_public_and_distinct():
    certs = [ROOT / c for _, c in TARGETS.values()]
    for c in certs:
        text = c.read_text()
        assert "BEGIN CERTIFICATE" in text and "PRIVATE KEY" not in text
        subprocess.run(["openssl", "x509", "-in", str(c), "-noout"], check=True)
    assert len({c.read_text() for c in certs}) == len(certs)


def test_no_private_keys_committed():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix not in {".pyc"} and not ({".git", "__pycache__", ".pytest_cache"} & set(p.parts)) and p.name != "test_workflow_policy.py":
            assert "PRIVATE KEY" not in p.read_text(errors="ignore"), p


def test_counts_output_contains_only_numbers():
    junit = ('<testsuite><testcase name="test_a[x]"/>'
             '<testcase name="test_b"><failure message="boom https://leak.invalid/secret"/></testcase></testsuite>')
    with tempfile.TemporaryDirectory() as d:
        j = pathlib.Path(d) / "junit.xml"
        j.write_text(junit)
        r = subprocess.run([sys.executable, str(ROOT / "report" / "build_report.py"), str(j)],
                           env={**os.environ, "SITE_URL": "http://127.0.0.1:9"}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    assert re.fullmatch(r"passed=\d+ failed=\d+ skipped=\d+\s*", r.stderr), r.stderr
