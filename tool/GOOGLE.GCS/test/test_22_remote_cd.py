"""
GCS Remote cd Test

Tests cd command navigation with API and --force modes.
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
class TestRemoteCd(MCPTestCase):
    """Test cd command in both API and shell bypass modes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_cd_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}/deep/nested"])

    def test_01_cd_and_pwd(self):
        """cd to test dir then pwd should show correct path."""
        self.gcs(["cd", self.test_dir])
        res = self.gcs(["pwd"])
        output = self.strip_ansi(res.stdout).strip()
        self.assertTrue(output.startswith("~/tmp/gcs_cd_test_"), f"Unexpected pwd: {output}")

    def test_02_cd_force(self):
        """cd --force should work via shell bypass."""
        res = self.gcs(["cd", self.test_dir, "--force"])
        self.assertSuccess(res, "cd --force failed")

    def test_03_cd_nested(self):
        """cd into nested directories should update pwd."""
        self.gcs(["cd", f"{self.test_dir}/deep/nested"])
        res = self.gcs(["pwd"])
        output = self.strip_ansi(res.stdout).strip()
        self.assertTrue(output.endswith("deep/nested"), f"Expected nested path, got: {output}")

    def test_04_cd_back_to_root(self):
        """cd ~ should reset to root."""
        self.gcs(["cd", "~"])
        res = self.gcs(["pwd"])
        output = self.strip_ansi(res.stdout).strip()
        self.assertEqual(output, "~")

    def test_05_cd_invalid(self):
        """cd to nonexistent dir should fail."""
        res = self.gcs(["cd", "~/nonexistent_dir_xyz_999"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
