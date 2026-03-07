"""
GCS Remote linter Test

Tests linter command for checking remote Python files.
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
class TestRemoteLinter(MCPTestCase):
    """Test linter command for checking remote Python files."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_lint_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])
        content = 'import os\\nimport sys\\nprint("hello")'
        cls.gcs(cls, [f'echo -e "{content}" > {cls.test_dir}/lint_target.py'])

    def test_01_linter_python(self):
        """linter should analyze a remote Python file."""
        res = self.gcs(["linter", f"{self.test_dir}/lint_target.py"])
        self.assertSuccess(res, "linter failed")
        output = self.strip_ansi(res.stdout + res.stderr).lower()
        has_lint = any(kw in output for kw in [
            "unused", "import", "no issues", "pass", "pyflakes", "linting"
        ])
        self.assertTrue(has_lint, f"Expected lint output, got: {output[:200]}")

    def test_02_linter_nonexistent(self):
        """linter on nonexistent file should fail."""
        res = self.gcs(["linter", f"{self.test_dir}/no_file.py"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
