"""
GCS Remote File Operations Test

Tests mkdir, touch, mv, rm operations via remote commands.
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
class TestRemoteFileOps(MCPTestCase):
    """Test file operations via remote commands."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_fileops_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])

    def test_01_mkdir(self):
        """mkdir -p should create directories."""
        target = f"{self.test_dir}/new_dir/nested"
        res = self.gcs([f"mkdir -p {target}"])
        self.assertSuccess(res, "mkdir failed")

    def test_02_touch(self):
        """touch should create an empty file."""
        target = f"{self.test_dir}/touched.txt"
        res = self.gcs([f"touch {target}"])
        self.assertSuccess(res, "touch failed")

    def test_03_mv(self):
        """mv should rename a file."""
        src = f"{self.test_dir}/touched.txt"
        dst = f"{self.test_dir}/renamed.txt"
        res = self.gcs([f"mv {src} {dst}"])
        self.assertSuccess(res, "mv failed")

    def test_04_rm(self):
        """rm should delete a file."""
        target = f"{self.test_dir}/renamed.txt"
        res = self.gcs([f"rm {target}"])
        self.assertSuccess(res, "rm failed")

    def test_05_ls_after_ops(self):
        """ls should reflect file operations."""
        res = self.gcs(["ls", self.test_dir, "--force"])
        self.assertSuccess(res, "ls --force failed")
        output = self.strip_ansi(res.stdout)
        self.assertIn("new_dir", output)
        self.assertNotIn("renamed.txt", output)


if __name__ == "__main__":
    unittest.main()
