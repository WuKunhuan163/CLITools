"""
GCS Remote edit Test

Tests edit command for modifying remote files.
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
class TestRemoteEdit(unittest.TestCase):
    """Test edit command for remote file modification."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_edit_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])
        cls._run(cls, [f'echo "original content" > {cls.test_dir}/edit_target.txt'])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_edit_replace(self):
        """edit should replace content in a remote file."""
        res = self._run(["edit", f"{self.test_dir}/edit_target.txt",
                         "original content", "modified content"])
        self.assertEqual(res.returncode, 0, f"edit failed: {res.stderr}")

    def test_02_verify_edit(self):
        """After edit, read should show the modified content."""
        res = self._run(["read", f"{self.test_dir}/edit_target.txt", "--force"])
        self.assertEqual(res.returncode, 0, f"read after edit failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("modified content", output)

    def test_03_edit_nonexistent(self):
        """edit on nonexistent file should fail."""
        res = self._run(["edit", f"{self.test_dir}/no_such_file.txt",
                         "old", "new"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
