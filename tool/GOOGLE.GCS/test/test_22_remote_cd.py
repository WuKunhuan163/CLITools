"""
GCS Remote cd Test

Tests cd command navigation with API and --force modes.
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
class TestRemoteCd(unittest.TestCase):
    """Test cd command in both API and shell bypass modes."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_cd_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}/deep/nested"])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_cd_and_pwd(self):
        """cd to test dir then pwd should show correct path."""
        self._run(["cd", self.test_dir])
        res = self._run(["pwd"])
        output = self._strip_ansi(res.stdout).strip()
        self.assertTrue(output.startswith("~/tmp/gcs_cd_test_"), f"Unexpected pwd: {output}")

    def test_02_cd_force(self):
        """cd --force should work via shell bypass."""
        res = self._run(["cd", self.test_dir, "--force"])
        self.assertEqual(res.returncode, 0, f"cd --force failed: {res.stderr}")

    def test_03_cd_nested(self):
        """cd into nested directories should update pwd."""
        self._run(["cd", f"{self.test_dir}/deep/nested"])
        res = self._run(["pwd"])
        output = self._strip_ansi(res.stdout).strip()
        self.assertTrue(output.endswith("deep/nested"), f"Expected nested path, got: {output}")

    def test_04_cd_back_to_root(self):
        """cd ~ should reset to root."""
        self._run(["cd", "~"])
        res = self._run(["pwd"])
        output = self._strip_ansi(res.stdout).strip()
        self.assertEqual(output, "~")

    def test_05_cd_invalid(self):
        """cd to nonexistent dir should fail."""
        res = self._run(["cd", "~/nonexistent_dir_xyz_999"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
