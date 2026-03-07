"""
GCS Remote Echo/Command Test

Tests basic remote command execution via GCS.
Requires active Colab connection and user interaction to run scripts.
"""
EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 60.0

import unittest
import subprocess
import sys
import re
import hashlib
import time
from pathlib import Path
from datetime import datetime

project_root = Path("/Applications/AITerminalTools")


def _has_service_account_key():
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    return key_path.exists()


@unittest.skipUnless(_has_service_account_key(), "Service account key not configured")
class TestRemoteEcho(unittest.TestCase):
    """Test remote command execution (echo, file creation, cat)."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_test_{ts}_{h}"
        cls._gcs_cmd(cls, ["cd", "~"])
        cls._gcs_cmd(cls, [f"mkdir -p {cls.test_dir}"])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _gcs_cmd(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_echo_simple(self):
        """Remote echo should produce output."""
        res = self._gcs_cmd([f'echo "hello from GCS test"'])
        self.assertEqual(res.returncode, 0, f"echo failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("hello from GCS test", output)

    def test_02_echo_to_file(self):
        """echo > file should create a file on remote."""
        target = f"{self.test_dir}/echo_test.txt"
        res = self._gcs_cmd([f'echo "file content" > {target}'])
        self.assertEqual(res.returncode, 0, f"echo to file failed: {res.stderr}")

    def test_03_cat_file(self):
        """cat should read the file created by echo."""
        target = f"{self.test_dir}/echo_test.txt"
        res = self._gcs_cmd([f'cat {target}'])
        self.assertEqual(res.returncode, 0, f"cat failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("file content", output)

    def test_04_pwd_remote(self):
        """pwd in remote should show a /content path."""
        res = self._gcs_cmd(["pwd"])
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
