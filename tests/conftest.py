import os, re, ssl, sys, pytest, requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for e2e.budgets

BASE = os.environ["SITE_URL"].rstrip("/")  # required; supplied via env or Actions secret, never stored in the repo
HEADERS = {"User-Agent": "website-e2e-checks/0.1 (owner-requested, single-user checks)"}


@pytest.fixture(scope="session")
def home():
    r = requests.get(BASE + "/", headers=HEADERS, timeout=20)
    r.elapsed_s = r.elapsed.total_seconds()
    return r


def tls_context() -> ssl.SSLContext:
    """TLS client context for the passive checks: TLS 1.2+ only."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def find(pattern, text, flags=re.I | re.S):
    return re.findall(pattern, text, flags)
