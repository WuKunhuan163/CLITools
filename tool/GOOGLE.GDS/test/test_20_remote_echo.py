"""
GDS Remote Echo/Command Test

Tests basic remote command execution via GDS.
Automatically uses MCP (CDP) when available, falls back to GUI interaction.
"""
EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 60.0

import unittest
import hashlib
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent

from mcp_test_base import MCPTestCase, has_service_account


@unittest.skipUnless(has_service_account(), "Service account key not configured")
class TestRemoteEcho(MCPTestCase):
    """Test remote command execution (echo, file creation, cat)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_test_{ts}_{h}"
        cls.gcs(cls, ["cd", "~"], use_mcp=False)
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])

    def test_01_echo_simple(self):
        """Remote echo should produce output."""
        res = self.gcs([f'echo "hello from GDS test"'])
        self.assertSuccess(res)
        self.assertOutput(res, "hello from GDS test")

    def test_02_echo_to_file(self):
        """echo > file should create a file on remote."""
        target = f"{self.test_dir}/echo_test.txt"
        res = self.gcs([f'echo "file content" > {target}'])
        self.assertSuccess(res)

    def test_03_cat_file(self):
        """cat should read the file created by echo."""
        target = f"{self.test_dir}/echo_test.txt"
        res = self.gcs(["cat", target])
        self.assertSuccess(res)
        self.assertOutput(res, "file content")

    def test_04_pwd_remote(self):
        """pwd in remote should show a path."""
        res = self.gcs(["pwd"])
        self.assertSuccess(res)


if __name__ == "__main__":
    unittest.main()
