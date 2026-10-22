import os, re, time, pytest, requests
from conftest import BASE, HEADERS, find


def test_home_ok(home):
    assert home.status_code == 200


def test_http_redirects_to_https():
    r = requests.get(BASE.replace("https://", "http://") + "/", headers=HEADERS, allow_redirects=False, timeout=15)
    assert r.status_code in (301, 308) and r.headers["location"].startswith("https://")


def test_response_time(home):
    assert home.elapsed_s < 3.0, f"home took {home.elapsed_s:.2f}s"


def test_html_weight_under_budget():
    r = requests.get(BASE + "/", headers={**HEADERS, "Accept-Encoding": "identity"}, timeout=30)
    assert len(r.content) < 500_000, f"uncompressed HTML is {len(r.content)//1024} KB"


def test_gzip_enabled():
    r = requests.get(BASE + "/", headers={**HEADERS, "Accept-Encoding": "gzip"}, stream=True, timeout=20)
    assert r.headers.get("content-encoding") in ("gzip", "br")


def test_title_and_description(home):
    assert find(r"<title[^>]*>(.+?)</title>", home.text)
    assert find(r'<meta name="description" content="([^"]{50,})', home.text)


def test_lang_and_dir(home):
    lang, direction = os.environ.get("EXPECT_LANG"), os.environ.get("EXPECT_DIR")
    if not (lang or direction):
        pytest.skip("EXPECT_LANG / EXPECT_DIR not set")
    if lang:
        assert f'lang="{lang}' in home.text
    if direction:
        assert f'dir="{direction}"' in home.text


def test_single_h1(home):
    assert len(find(r"<h1[\s>]", home.text)) == 1


def test_viewport_canonical(home):
    assert 'name="viewport"' in home.text and 'rel="canonical"' in home.text


def test_images_have_alt(home):
    assert not find(r"<img(?![^>]*\balt=)[^>]*>", home.text)


@pytest.mark.parametrize("h", ["strict-transport-security", "x-content-type-options", "referrer-policy", "x-frame-options"])
def test_security_headers_present(home, h):
    assert h in home.headers


def test_csp_present(home):
    assert "content-security-policy" in home.headers, "no Content-Security-Policy (hardening, not a bug)"


def test_tls_cert_not_expiring_soon():
    import ssl, socket, datetime
    host = BASE.split("//")[1]
    with socket.create_connection((host, 443), timeout=10) as s:
        cert = ssl.create_default_context().wrap_socket(s, server_hostname=host).getpeercert()
    days = (datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z") - datetime.datetime.utcnow()).days
    assert days > 14, f"cert expires in {days} days"


def test_robots_and_sitemap():
    assert requests.get(BASE + "/robots.txt", headers=HEADERS, timeout=15).status_code == 200
    assert requests.get(BASE + "/sitemap.xml", headers=HEADERS, timeout=15, allow_redirects=True).status_code == 200


def test_forms_exist_not_submitted(home):
    assert find(r"<form[\s>]", home.text)  # presence only, never submitted


@pytest.mark.slow
def test_internal_links_ok(home):
    links = sorted({l.split("#")[0] for l in find(r'href="(' + re.escape(BASE) + r'[^"]*)"', home.text)})[:40]
    bad = []
    for u in links:
        r = requests.head(u, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code >= 400:
            bad.append((u, r.status_code))
        time.sleep(0.5)
    assert not bad, bad
