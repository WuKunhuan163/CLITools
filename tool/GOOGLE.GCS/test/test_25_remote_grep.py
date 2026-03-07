"""
GCS Remote grep Test

Tests grep command for pattern searching in remote files.
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
class TestRemoteGrep(unittest.TestCase):
    """Test grep command for searching remote file content."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_grep_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])
        content = "alpha\\nbeta\\ngamma\\ndelta\\nalpha_two"
        cls._run(cls, [f'echo -e "{content}" > {cls.test_dir}/grep_target.txt'])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_grep_match(self):
        """grep should find matching lines."""
        res = self._run(["grep", "alpha", f"{self.test_dir}/grep_target.txt"])
        self.assertEqual(res.returncode, 0, f"grep failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("alpha", output)

    def test_02_grep_no_match(self):
        """grep for non-existent pattern should return no matches."""
        res = self._run(["grep", "zzz_no_match", f"{self.test_dir}/grep_target.txt"])
        output = self._strip_ansi(res.stdout + res.stderr)
        lines = [l for l in output.strip().splitlines() if "zzz_no_match" in l]
        self.assertEqual(len(lines), 0)

    def test_03_grep_nonexistent_file(self):
        """grep on nonexistent file should fail."""
        res = self._run(["grep", "test", f"{self.test_dir}/no_file.txt"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
