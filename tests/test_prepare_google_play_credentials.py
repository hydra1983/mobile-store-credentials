import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare-google-play-credentials.sh"
BASH = shutil.which("bash")
PROJECT = "example-mobile"
ACCOUNT = "play-publisher"
EMAIL = f"{ACCOUNT}@{PROJECT}.iam.gserviceaccount.com"
KEY_ID = "a" * 40
MOCK_GCLOUD = """\
import json
import os
from pathlib import Path
import sys

state = Path(os.environ["MOCK_STATE"])
args = sys.argv[1:]
assert args[:3] == ["--quiet", "--project", "example-mobile"]
args = args[3:]
email = "play-publisher@example-mobile.iam.gserviceaccount.com"
failure = os.environ.get("MOCK_FAILURE")
with (state / "calls").open("a") as log:
    log.write(" ".join(args[:3]) + "\\n")

if args[:2] == ["services", "list"]:
    if failure == "api-denied":
        sys.exit("PERMISSION_DENIED")
    assert "--filter=config.name=androidpublisher.googleapis.com" in args
    if (state / "api").exists():
        print("androidpublisher.googleapis.com")
elif args[:3] == ["iam", "service-accounts", "list"]:
    if failure == "account-denied":
        sys.exit("PERMISSION_DENIED")
    assert f"--filter=email={email}" in args
    accounts = [{"email": email, "disabled": failure == "disabled"}]
    print(json.dumps(accounts if (state / "account").exists() else []))
elif args == ["services", "enable", "androidpublisher.googleapis.com"]:
    (state / "api").touch()
elif args[:4] == ["iam", "service-accounts", "create", "play-publisher"]:
    (state / "account").touch()
elif args[:4] == ["iam", "service-accounts", "keys", "create"]:
    if failure == "key-denied":
        sys.exit("PERMISSION_DENIED")
    assert args[5:] == [f"--iam-account={email}", "--key-file-type=json"]
    key = {
        "type": "service_account",
        "client_email": email,
        "client_id": "123456",
        "private_key_id": "a" * 40,
        "private_key": "-----BEGIN PRIVATE KEY-----\\nsynthetic-test-value\\n-----END PRIVATE KEY-----\\n",
        "token_uri": "https://oauth2.example.invalid/token",
    }
    if failure == "invalid-key":
        key["client_email"] = "other@example.invalid"
    Path(args[4]).write_text(json.dumps(key))
    if failure == "collision":
        Path(os.environ["MOCK_DESTINATION"]).write_text("competing file")
    print(key["private_key"])
else:
    sys.exit(f"unexpected command: {args}")
"""


class PrepareGooglePlayCredentialsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = self.root / "standalone app"
        self.app.mkdir()
        self.state = self.root / "state"
        self.state.mkdir()
        self.mock_bin = self.root / "bin"
        self.mock_bin.mkdir()
        mock = self.mock_bin / "gcloud"
        mock.write_text(
            "#!/bin/sh\nexec "
            + shlex.quote(sys.executable)
            + " - \"$@\" <<'PY'\n"
            + MOCK_GCLOUD
            + "PY\n"
        )
        mock.chmod(0o700)
        self.output = self.app / "private credentials" / "play.json"

    def run_script(self, *flags, failure="", isolated=False):
        env = {
            "PATH": str(self.root / "empty") if isolated else f"{self.mock_bin}{os.pathsep}{os.defpath}{os.pathsep}{Path(sys.executable).parent}",
            "MOCK_STATE": str(self.state),
            "MOCK_FAILURE": failure,
            "MOCK_DESTINATION": str(self.output),
        }
        return subprocess.run(
            [BASH, str(SCRIPT), "--project", PROJECT, "--service-account", ACCOUNT,
             "--key-path", str(self.output.relative_to(self.app)), *flags],
            cwd=self.app,
            env=env,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def calls(self):
        log = self.state / "calls"
        return log.read_text().splitlines() if log.exists() else []

    def test_default_and_explicit_preview_work_without_dependencies(self):
        default = self.run_script(isolated=True)
        explicit = self.run_script("--dry-run", isolated=True)
        with_mock = self.run_script()
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(with_mock.returncode, 0, with_mock.stderr)
        self.assertEqual(default.stdout, explicit.stdout)
        self.assertIn("cloud status pending", default.stdout)
        self.assertEqual(list(self.app.iterdir()), [])
        self.assertEqual(self.calls(), [])

    def test_conflicting_flags_fail_without_calling_cloud(self):
        result = self.run_script("--dry-run", "--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])
        self.assertEqual(list(self.app.iterdir()), [])

    def test_apply_creates_once_then_reuses(self):
        first = self.run_script("--apply")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotIn("synthetic-test-value", first.stdout + first.stderr)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        self.assertEqual(json.loads(self.output.read_text())["client_email"], EMAIL)
        self.assertEqual(self.calls(), [
            "services list --enabled", "iam service-accounts list", "services enable androidpublisher.googleapis.com",
            "iam service-accounts create", "iam service-accounts keys",
        ])
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])
        previous = self.output.read_bytes()
        second = self.run_script("--apply")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("Reused existing", second.stdout)
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(self.calls()[5:], ["services list --enabled", "iam service-accounts list"])

    def test_mismatched_file_and_symlink_are_preserved(self):
        self.output.parent.mkdir()
        data = '{"type":"service_account","client_email":"another@example.invalid"}'
        self.output.write_text(data)
        result = self.run_script("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), data)
        self.output.unlink()
        missing = self.output.with_suffix(".missing")
        self.output.symlink_to(missing)
        result = self.run_script("--apply")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(missing.exists())
        self.assertEqual(self.calls(), [])

    def test_failed_lookup_and_disabled_account_stop_before_mutations(self):
        for failure in ("api-denied", "account-denied", "disabled"):
            with self.subTest(failure=failure):
                log = self.state / "calls"
                if log.exists():
                    log.unlink()
                if failure == "disabled":
                    (self.state / "account").touch()
                result = self.run_script("--apply", failure=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.parent.exists())
                expected = ["services list --enabled"]
                if failure != "api-denied":
                    expected.append("iam service-accounts list")
                self.assertEqual(self.calls(), expected)

    def test_failed_install_preserves_destination_and_reports_key_id(self):
        result = self.run_script("--apply", failure="collision")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not install", result.stderr)
        self.assertIn(f"Key ID: {KEY_ID}", result.stderr)
        self.assertEqual(self.output.read_text(), "competing file")
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])
        self.assertNotIn("synthetic-test-value", result.stdout + result.stderr)

    def test_wrong_account_in_generated_json_is_rejected(self):
        result = self.run_script("--apply", failure="invalid-key")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not pass local validation", result.stderr)
        self.assertIn(f"Key ID: {KEY_ID}", result.stderr)
        self.assertEqual(list(self.output.parent.iterdir()), [])
        self.assertNotIn("synthetic-test-value", result.stdout + result.stderr)

    def test_failed_key_creation_cleans_staging_and_reuses_cloud_setup(self):
        failed = self.run_script("--apply", failure="key-denied")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("A key may have been created", failed.stderr)
        self.assertEqual(list(self.output.parent.iterdir()), [])
        retry = self.run_script("--apply")
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertEqual(self.calls().count("services enable androidpublisher.googleapis.com"), 1)
        self.assertEqual(self.calls().count("iam service-accounts create"), 1)
        self.assertEqual(self.calls().count("iam service-accounts keys"), 2)


if __name__ == "__main__":
    unittest.main()
