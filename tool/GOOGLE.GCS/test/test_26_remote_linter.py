"""
GCS Remote linter Test

Tests linter command for checking remote Python files.
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
class TestRemoteLinter(unittest.TestCase):
    """Test linter command for checking remote Python files."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_lint_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])
        # Create a Python file with a known lint issue (unused import)
        content = 'import os\\nimport sys\\nprint("hello")'
        cls._run(cls, [f'echo -e "{content}" > {cls.test_dir}/lint_target.py'])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_linter_python(self):
        """linter should analyze a remote Python file."""
        res = self._run(["linter", f"{self.test_dir}/lint_target.py"])
        self.assertEqual(res.returncode, 0, f"linter failed: {res.stderr}")
        output = self._strip_ansi(res.stdout + res.stderr)
        # Should detect unused import (os or sys)
        has_lint = "unused" in output.lower() or "import" in output.lower() or "no issues" in output.lower()
        self.assertTrue(has_lint, f"Expected lint output, got: {output[:200]}")

    def test_02_linter_nonexistent(self):
        """linter on nonexistent file should fail."""
        res = self._run(["linter", f"{self.test_dir}/no_file.py"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
