"""
GCS Remote read Test

Tests read command for remote file content retrieval.
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
class TestRemoteRead(MCPTestCase):
    """Test read command for viewing remote files."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_read_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])
        content = "line1\\nline2\\nline3\\nline4\\nline5"
        cls.gcs(cls, [f'echo -e "{content}" > {cls.test_dir}/read_test.txt'])

    def test_01_read_file(self):
        """read should display file content with line numbers."""
        res = self.gcs(["read", f"{self.test_dir}/read_test.txt"])
        self.assertSuccess(res, "read failed")
        self.assertOutput(res, "line1")

    def test_02_read_force(self):
        """read --force should bypass API cache."""
        res = self.gcs(["read", f"{self.test_dir}/read_test.txt", "--force"])
        self.assertSuccess(res, "read --force failed")
        self.assertOutput(res, "line1")

    def test_03_read_nonexistent(self):
        """read on nonexistent file should fail."""
        res = self.gcs(["read", f"{self.test_dir}/no_such_file.txt"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
