"""
GCS Remote ls Test

Tests ls command with both API and --force modes.
Requires active Colab connection and user interaction.
"""
EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 60.0

import unittest
import subprocess
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime

project_root = Path("/Applications/AITerminalTools")


def _has_service_account_key():
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    return key_path.exists()


@unittest.skipUnless(_has_service_account_key(), "Service account key not configured")
class TestRemoteLs(unittest.TestCase):
    """Test ls command in both API and shell bypass modes."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_ls_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}/subdir"])
        cls._run(cls, [f'echo "ls test" > {cls.test_dir}/ls_file.txt'])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_ls_api_root(self):
        """ls ~ via API should list remote root."""
        res = self._run(["ls", "~"])
        self.assertEqual(res.returncode, 0, f"ls ~ failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertTrue(len(output.strip()) > 0, "ls ~ should produce output")

    def test_02_ls_api_test_dir(self):
        """ls on test dir via API should show created files."""
        res = self._run(["ls", self.test_dir])
        self.assertEqual(res.returncode, 0, f"ls test_dir failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("ls_file.txt", output)
        self.assertIn("subdir", output)

    def test_03_ls_force(self):
        """ls --force should bypass API cache and list via shell."""
        res = self._run(["ls", self.test_dir, "--force"])
        self.assertEqual(res.returncode, 0, f"ls --force failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("ls_file.txt", output)

    def test_04_ls_nonexistent(self):
        """ls on nonexistent path should return error."""
        res = self._run(["ls", "~/nonexistent_xyz_999"])
        self.assertNotEqual(res.returncode, 0)

    def test_05_ls_long_format(self):
        """ls -l should show detailed listing."""
        res = self._run(["ls", "-l", "~"])
        self.assertEqual(res.returncode, 0, f"ls -l failed: {res.stderr}")


if __name__ == "__main__":
    unittest.main()
