"""Passive security checks: normal GET requests and TLS metadata only. No probing, no fuzzing, no login."""
import os, re, ssl, socket, pytest, requests
from conftest import BASE, HEADERS, tls_context

PATHS = [p for p in os.environ.get("EXPOSED_PATHS", "/readme.html,/license.txt,/xmlrpc.php").split(",") if p]


def test_tls_modern_version():
    host = BASE.split("//")[1].split("/")[0]
    with socket.create_connection((host, 443), timeout=10) as s:
        v = tls_context().wrap_socket(s, server_hostname=host).version()
    assert v in ("TLSv1.2", "TLSv1.3"), v


def test_hsts_max_age(home):
    m = re.search(r"max-age=(\d+)", home.headers.get("strict-transport-security", ""))
    assert m and int(m.group(1)) >= 15552000


def test_no_version_disclosure_headers(home):
    leaks = [h for h in ("x-powered-by", "x-aspnet-version", "x-generator") if h in home.headers]
    server = home.headers.get("server", "")
    assert not leaks and not re.search(r"\d+\.\d+", server), (leaks, server)


def test_cookie_flags(home):
    raw = home.raw.headers.getlist("Set-Cookie") if hasattr(home.raw.headers, "getlist") else []
    bad = [c.split("=")[0] for c in raw if "secure" not in c.lower() or "samesite" not in c.lower()]
    assert not bad, bad


@pytest.mark.parametrize("path", PATHS)
def test_common_file_not_exposed(path):
    r = requests.get(BASE + path, headers=HEADERS, timeout=15, allow_redirects=False)
    assert r.status_code in (301, 302, 401, 403, 404, 405), f"{path} -> {r.status_code}"


def test_security_txt():
    r = requests.get(BASE + "/.well-known/security.txt", headers=HEADERS, timeout=15)
    assert r.status_code == 200 and "Contact:" in r.text


def test_mixed_content_absent(home):
    assert not re.findall(r'(?:src|href)="http://(?!www\.w3\.org)[^"]+', home.text)
