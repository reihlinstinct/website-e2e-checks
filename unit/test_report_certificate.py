"""Offline certificate storage checks, without recipient private-key access."""
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATE = ROOT / 'certs/report-recipient.pem'


class ReportCertificateTests(unittest.TestCase):
    def test_public_recipient_is_certificate_only(self):
        text = CERTIFICATE.read_text(encoding='ascii')
        self.assertIsNotNone(re.fullmatch(
            r'-----BEGIN CERTIFICATE-----\n(?:[A-Za-z0-9+/=]+\n)+'
            r'-----END CERTIFICATE-----\n', text))
        subprocess.run(['openssl', 'x509', '-in', str(CERTIFICATE), '-noout'],
                       check=True, capture_output=True)

    def test_unchanged_ci_cms_command_accepts_recipient(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'report.txt'
            source.write_text('Synthetic offline report', encoding='utf-8')
            subprocess.run([
                'openssl', 'cms', '-encrypt', '-aes-256-cbc', '-in', str(source),
                '-out', str(root / 'report.p7m'), '-outform', 'DER',
                str(CERTIFICATE),
            ], check=True, capture_output=True)
            self.assertTrue((root / 'report.p7m').stat().st_size)

    def test_synthetic_cms_roundtrip_needs_no_recipient_private_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key, cert = root / 'ephemeral-key.pem', root / 'certificate.pem'
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(key), '-out', str(cert), '-days', '1',
                '-subj', '/CN=Synthetic offline fixture',
            ], check=True, capture_output=True)
            source, encrypted, output = (root / n for n in ('in', 'cms', 'out'))
            source.write_bytes(b'Synthetic offline CMS fixture')
            subprocess.run([
                'openssl', 'cms', '-encrypt', '-aes-256-cbc', '-in', str(source),
                '-out', str(encrypted), '-outform', 'DER', str(cert),
            ], check=True, capture_output=True)
            subprocess.run([
                'openssl', 'cms', '-decrypt', '-inform', 'DER', '-in', str(encrypted),
                '-recip', str(cert), '-inkey', str(key), '-out', str(output),
            ], check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), source.read_bytes())
