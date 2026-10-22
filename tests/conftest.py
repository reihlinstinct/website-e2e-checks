import os, re, pytest, requests

BASE = os.environ["SITE_URL"].rstrip("/")  # required; supplied via env or Actions secret, never stored in the repo
HEADERS = {"User-Agent": "website-e2e-checks/0.1 (owner-requested, single-user checks)"}


@pytest.fixture(scope="session")
def home():
    r = requests.get(BASE + "/", headers=HEADERS, timeout=20)
    r.elapsed_s = r.elapsed.total_seconds()
    return r


def find(pattern, text, flags=re.I | re.S):
    return re.findall(pattern, text, flags)
