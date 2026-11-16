"""Regression test for issue #31: the shared TLS client context must not allow TLSv1/TLSv1.1."""
import ssl
from conftest import tls_context


def test_tls_context_requires_tls12_or_newer():
    ctx = tls_context()
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2, ctx.minimum_version
