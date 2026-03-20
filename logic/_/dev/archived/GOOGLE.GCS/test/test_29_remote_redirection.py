"""
GCS Remote Redirection Test

Tests that user commands with shell redirections work correctly
through the safe-bash heredoc pattern.
Automatically uses MCP (CDP) when available, falls back to GUI interaction.
"""
EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 60.0

import unittest
import hashlib
from pathlib import Path
from datetime import datetime

project_root = Path("/Applications/AITerminalTools")

from mcp_test_base import MCPTestCase, has_service_account


@unittest.skipUnless(has_service_account(), "Service account key not configured")
class TestRemoteRedirection(MCPTestCase):
    """Test that shell redirections in user commands work via heredoc."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_redir_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])

    def test_01_echo_redirect(self):
        """echo > file should create file via heredoc."""
        target = f"{self.test_dir}/redir_out.txt"
        res = self.gcs([f'echo "redirect test" > {target}'])
        self.assertSuccess(res, "echo redirect failed")

    def test_02_cat_redirect_result(self):
        """cat should read the file created by redirect."""
        target = f"{self.test_dir}/redir_out.txt"
        res = self.gcs(["cat", target])
        self.assertSuccess(res, "cat failed")
        self.assertOutput(res, "redirect test")

    def test_03_pipe(self):
        """Pipe commands should work within heredoc."""
        res = self.gcs([f'echo "aaa\\nbbb\\nccc" | grep bbb'])
        self.assertSuccess(res, "pipe failed")
        self.assertOutput(res, "bbb")

    def test_04_append_redirect(self):
        """>> should append to file."""
        target = f"{self.test_dir}/redir_out.txt"
        self.gcs([f'echo "appended line" >> {target}'])
        res = self.gcs(["cat", target])
        output = self.strip_ansi(res.stdout)
        self.assertIn("redirect test", output)
        self.assertIn("appended line", output)

    def test_05_stderr_redirect(self):
        """2> should redirect stderr separately."""
        err_file = f"{self.test_dir}/err_output.txt"
        res = self.gcs([f'ls /nonexistent_xyz 2> {err_file}; echo "done"'])
        self.assertSuccess(res)


if __name__ == "__main__":
    unittest.main()
