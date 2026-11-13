import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-ios-signing.py"
BUNDLE_ID = "com.example.fieldnotes"
TEAM_ID = "ABCDE12345"
PASSWORD = "synthetic-fixture-password"


@unittest.skipUnless(shutil.which("openssl"), "Requires OpenSSL")
class SigningCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(scratch.cleanup)
        cls.root = Path(scratch.name)
        cls.environment = {**os.environ, "P12_PASSWORD": PASSWORD}
        cls.openssl(
            "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
            "-subj", f"/CN=Apple Distribution: Example/OU={TEAM_ID}",
            "-keyout", "key.pem", "-out", "cert.pem",
        )
        cls.openssl(
            "pkcs12", "-export", "-inkey", "key.pem", "-in", "cert.pem",
            "-out", "identity.p12", "-passout", "env:P12_PASSWORD",
        )
        cls.openssl(
            "pkcs12", "-export", "-nokeys", "-in", "cert.pem",
            "-out", "certificate-only.p12", "-passout", "env:P12_PASSWORD",
        )
        cls.certificate = cls.openssl("x509", "-in", "cert.pem", "-outform", "DER")

    @classmethod
    def openssl(cls, *args):
        return subprocess.run(
            ["openssl", *args], cwd=cls.root, env=cls.environment, check=True, capture_output=True,
        ).stdout

    def check(self, *, bundle=BUNDLE_ID, team=TEAM_ID, identity="identity.p12",
              profile_path="profile.mobileprovision", password=PASSWORD, expected=None,
              missing_entitlement=None, **profile_fields):
        entitlements = {
            "application-identifier": f"{TEAM_ID}.{BUNDLE_ID}",
            "get-task-allow": False,
            "aps-environment": "production",
            "com.apple.developer.applesignin": ["Default"],
        }
        if missing_entitlement:
            entitlements.pop(missing_entitlement)
        profile = {
            "TeamIdentifier": [TEAM_ID],
            "ExpirationDate": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
            "DeveloperCertificates": [self.certificate],
            "Entitlements": entitlements,
            **profile_fields,
        }
        (self.root / "profile.plist").write_bytes(plistlib.dumps(profile))
        self.openssl(
            "smime", "-sign", "-binary", "-nodetach", "-outform", "DER", "-in", "profile.plist",
            "-signer", "cert.pem", "-inkey", "key.pem", "-out", "profile.mobileprovision",
        )
        before = {file.name: file.read_bytes() for file in self.root.iterdir()}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bundle-id", bundle, "--team-id", team,
             "--p12", identity, "--profile", profile_path, "--password-env", "P12_PASSWORD",
             "--require-push", "--require-apple-sign-in"],
            cwd=self.root, env={**self.environment, "P12_PASSWORD": password},
            capture_output=True, text=True,
        )
        self.assertNotIn(password, result.stdout + result.stderr)
        self.assertEqual(before, {file.name: file.read_bytes() for file in self.root.iterdir()})
        if expected is None:
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Local signing inputs match", result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected, result.stderr)

    def test_matching_inputs_and_historical_app_id_prefix(self):
        self.check()
        self.check(
            ApplicationIdentifierPrefix=["OLDPREFIX1"],
            Entitlements={
                "application-identifier": f"OLDPREFIX1.{BUNDLE_ID}",
                "com.apple.developer.team-identifier": TEAM_ID,
                "get-task-allow": False,
                "aps-environment": "production",
                "com.apple.developer.applesignin": ["Default"],
            },
        )

    def test_rejects_wrong_bundle_and_team(self):
        self.check(bundle="com.example.other", expected="Bundle ID")
        self.check(team="ABCDE12346", expected="target team")

    def test_rejects_adhoc_and_expired_profiles(self):
        self.check(ProvisionedDevices=["synthetic-device"], expected="App Store distribution")
        self.check(ExpirationDate=datetime(2000, 1, 1), expected="expired")

    def test_rejects_missing_capabilities(self):
        self.check(missing_entitlement="aps-environment", expected="production push")
        self.check(missing_entitlement="com.apple.developer.applesignin", expected="Sign in with Apple")

    def test_rejects_unusable_identity_or_missing_profile(self):
        self.check(identity="certificate-only.p12", expected="one private key")
        self.check(password="synthetic-wrong-password", expected="Cannot open the P12")
        self.check(DeveloperCertificates=[], expected="does not authorize")
        self.check(profile_path="missing.mobileprovision", expected="readable files")


if __name__ == "__main__":
    unittest.main()
