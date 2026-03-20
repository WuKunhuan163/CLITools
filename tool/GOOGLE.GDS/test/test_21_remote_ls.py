"""
GDS Remote ls Test

Tests ls command with both API and --force modes.
Automatically uses MCP (CDP) when available, falls back to GUI interaction.
"""
EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 60.0

import unittest
import hashlib
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent.parent.parent

from mcp_test_base import MCPTestCase, has_service_account


@unittest.skipUnless(has_service_account(), "Service account key not configured")
class TestRemoteLs(MCPTestCase):
    """Test ls command in both API and shell bypass modes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_ls_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}/subdir"])
        cls.gcs(cls, [f'echo "ls test" > {cls.test_dir}/ls_file.txt'])

    def test_01_ls_api_root(self):
        """ls ~ via API should list remote root."""
        res = self.gcs(["ls", "~"], use_mcp=False)
        self.assertSuccess(res)
        output = self.strip_ansi(res.stdout)
        self.assertTrue(len(output.strip()) > 0, "ls ~ should produce output")

    def test_02_ls_api_test_dir(self):
        """ls on test dir via API should show created files."""
        res = self.gcs(["ls", self.test_dir], use_mcp=False)
        self.assertSuccess(res)
        self.assertOutput(res, "ls_file.txt")
        self.assertOutput(res, "subdir")

    def test_03_ls_force(self):
        """ls --force should bypass API cache and list via shell."""
        res = self.gcs(["ls", self.test_dir, "--force"])
        self.assertSuccess(res)
        self.assertOutput(res, "ls_file.txt")

    def test_04_ls_nonexistent(self):
        """ls on nonexistent path should return error."""
        res = self.gcs(["ls", "~/nonexistent_xyz_999"], use_mcp=False)
        self.assertNotEqual(res.returncode, 0)

    def test_05_ls_long_format(self):
        """ls -l should show detailed listing."""
        res = self.gcs(["ls", "-l", "~"], use_mcp=False)
        self.assertSuccess(res)


if __name__ == "__main__":
    unittest.main()
