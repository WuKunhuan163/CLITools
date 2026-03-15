EXPECTED_CPU_LIMIT = 60.0
EXPECTED_TIMEOUT = 300
import unittest
import subprocess
import sys
import re
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _has_service_account_key():
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    return key_path.exists()


@unittest.skipUnless(_has_service_account_key(), "Service account key not configured")
class TestDriveAPIAccess(unittest.TestCase):
    """Test Google Drive API access via the configured service account."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_utils",
            str(project_root / "tool" / "GOOGLE.GCS" / "logic" / "utils.py")
        )
        cls.utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.utils)

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_gcs(self, args, timeout=90):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_token_generation(self):
        """Service account should generate a valid access token."""
        creds = self.utils.get_service_account_creds(project_root)
        self.assertIsInstance(creds, dict, "Failed to load service account credentials")
        self.assertIn("client_email", creds)
        token = self.utils.get_gdrive_access_token(creds)
        self.assertIsNotNone(token, "Failed to generate access token")
        self.assertTrue(len(token) > 20, "Token seems too short")

    def test_02_ls_root(self):
        """GCS ls ~ should list files in the remote root."""
        res = self._run_gcs(["ls", "~"])
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertEqual(res.returncode, 0,
                         f"ls ~ failed (code {res.returncode}): {output}")
        lines = [l for l in output.strip().splitlines() if l.strip()]
        self.assertTrue(len(lines) > 0, "ls ~ should list at least one item")

    def test_03_ls_long_format(self):
        """GCS ls -l ~ should show IDs and folder types."""
        res = self._run_gcs(["ls", "-l", "~"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0, f"ls -l failed: {res.stderr}")
        # Long format includes folder IDs (long alphanumeric strings)
        lines = [l for l in output.strip().splitlines() if l.strip()]
        if lines:
            # Skip header line if present
            data_lines = [l for l in lines if not l.startswith("~")]
            if data_lines:
                self.assertTrue(len(data_lines[0].split()) >= 2,
                                "Long format should have at least ID and name columns")

    def test_04_ls_invalid_path(self):
        """GCS ls with an invalid path should return non-zero and print bash-like error."""
        res = self._run_gcs(["ls", "~/nonexistent_path_xyz_99999"])
        self.assertNotEqual(res.returncode, 0, "ls on invalid path should return non-zero")
        error_output = self._strip_ansi(res.stderr)
        self.assertIn("No such file or directory", error_output,
                       f"Expected bash-like error, got: {error_output}")

    def test_05_cd_root(self):
        """GCS cd ~ should succeed silently (like bash cd)."""
        res = self._run_gcs(["cd", "~"])
        self.assertEqual(res.returncode, 0, f"cd ~ failed: {res.stderr}")

    def test_06_run_drive_api_script(self):
        """run_drive_api_script should execute a simple API query."""
        script = '''    r = api_get("https://www.googleapis.com/drive/v3/about",
                  headers, params={"fields": "user"}, timeout=20)
    if r.status_code == 200:
        result = r.json()
    else:
        result = {"error": f"API error {r.status_code}"}'''
        ok, data = self.utils.run_drive_api_script(project_root, script, timeout=90)
        self.assertTrue(ok, f"run_drive_api_script failed: {data}")
        self.assertIn("user", data, f"Expected 'user' in about response, got: {data}")


if __name__ == "__main__":
    unittest.main()
