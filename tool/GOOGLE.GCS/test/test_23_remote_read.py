"""
GCS Remote read Test

Tests read command for remote file content retrieval.
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
class TestRemoteRead(unittest.TestCase):
    """Test read command for viewing remote files."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_read_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])
        # Create a multi-line test file
        content = "line1\\nline2\\nline3\\nline4\\nline5"
        cls._run(cls, [f'echo -e "{content}" > {cls.test_dir}/read_test.txt'])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_read_file(self):
        """read should display file content with line numbers."""
        res = self._run(["read", f"{self.test_dir}/read_test.txt"])
        self.assertEqual(res.returncode, 0, f"read failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("line1", output)

    def test_02_read_force(self):
        """read --force should bypass API cache."""
        res = self._run(["read", f"{self.test_dir}/read_test.txt", "--force"])
        self.assertEqual(res.returncode, 0, f"read --force failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("line1", output)

    def test_03_read_nonexistent(self):
        """read on nonexistent file should fail."""
        res = self._run(["read", f"{self.test_dir}/no_such_file.txt"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
