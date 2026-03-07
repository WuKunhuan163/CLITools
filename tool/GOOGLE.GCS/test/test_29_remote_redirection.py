"""
GCS Remote Redirection Test

Tests that user commands with shell redirections work correctly
through the safe-bash heredoc pattern.
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
class TestRemoteRedirection(unittest.TestCase):
    """Test that shell redirections in user commands work via heredoc."""

    @classmethod
    def setUpClass(cls):
        cls.gcs_bin = project_root / "bin" / "GCS" / "GCS"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_redir_test_{ts}_{h}"
        cls._run(cls, [f"mkdir -p {cls.test_dir}"])

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run(self, args, timeout=120):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_echo_redirect(self):
        """echo > file should create file via heredoc."""
        target = f"{self.test_dir}/redir_out.txt"
        res = self._run([f'echo "redirect test" > {target}'])
        self.assertEqual(res.returncode, 0, f"echo redirect failed: {res.stderr}")

    def test_02_cat_redirect_result(self):
        """cat should read the file created by redirect."""
        target = f"{self.test_dir}/redir_out.txt"
        res = self._run([f"cat {target}"])
        self.assertEqual(res.returncode, 0, f"cat failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("redirect test", output)

    def test_03_pipe(self):
        """Pipe commands should work within heredoc."""
        res = self._run([f'echo "aaa\\nbbb\\nccc" | grep bbb'])
        self.assertEqual(res.returncode, 0, f"pipe failed: {res.stderr}")
        output = self._strip_ansi(res.stdout)
        self.assertIn("bbb", output)

    def test_04_append_redirect(self):
        """>> should append to file."""
        target = f"{self.test_dir}/redir_out.txt"
        self._run([f'echo "appended line" >> {target}'])
        res = self._run([f"cat {target}"])
        output = self._strip_ansi(res.stdout)
        self.assertIn("redirect test", output)
        self.assertIn("appended line", output)

    def test_05_stderr_redirect(self):
        """2> should redirect stderr separately."""
        err_file = f"{self.test_dir}/err_output.txt"
        res = self._run([f'ls /nonexistent_xyz 2> {err_file}; echo "done"'])
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
