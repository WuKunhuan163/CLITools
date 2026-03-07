"""
GCS Remote File Operations Test

Tests mkdir, touch, mv, rm operations via remote commands.
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
class TestRemoteFileOps(unittest.TestCase):
    """Test file operations via remote commands."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_fileops_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_mkdir(self):
        """mkdir -p should create directories."""
        target = f"{self.test_dir}/new_dir/nested"
        res = self._run([f"mkdir -p {target}"])
        self.assertEqual(res.returncode, 0, f"mkdir failed: {res.stderr}")

    def test_02_touch(self):
        """touch should create an empty file."""
        target = f"{self.test_dir}/touched.txt"
        res = self._run([f"touch {target}"])
        self.assertEqual(res.returncode, 0, f"touch failed: {res.stderr}")

    def test_03_mv(self):
        """mv should rename a file."""
        src = f"{self.test_dir}/touched.txt"
        dst = f"{self.test_dir}/renamed.txt"
        res = self._run([f"mv {src} {dst}"])
        self.assertEqual(res.returncode, 0, f"mv failed: {res.stderr}")

    def test_04_rm(self):
        """rm should delete a file."""
        target = f"{self.test_dir}/renamed.txt"
        res = self._run([f"rm {target}"])
        self.assertEqual(res.returncode, 0, f"rm failed: {res.stderr}")

    def test_05_ls_after_ops(self):
        """ls should reflect file operations."""
        res = self._run(["ls", self.test_dir, "--force"])
        self.assertEqual(res.returncode, 0, f"ls --force failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("new_dir", output)
        self.assertNotIn("renamed.txt", output)


if __name__ == "__main__":
    unittest.main()
