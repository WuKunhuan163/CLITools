"""
GDS Remote grep Test

Tests grep command for pattern searching in remote files.
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
class TestRemoteGrep(MCPTestCase):
    """Test grep command for searching remote file content."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_grep_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])
        content = "alpha\\nbeta\\ngamma\\ndelta\\nalpha_two"
        cls.gcs(cls, [f'echo -e "{content}" > {cls.test_dir}/grep_target.txt'])

    def test_01_grep_match(self):
        """grep should find matching lines."""
        res = self.gcs(["grep", "alpha", f"{self.test_dir}/grep_target.txt"])
        self.assertSuccess(res, "grep failed")
        self.assertOutput(res, "alpha")

    def test_02_grep_no_match(self):
        """grep for non-existent pattern should return no matches."""
        res = self.gcs(["grep", "zzz_no_match", f"{self.test_dir}/grep_target.txt"])
        output = self.strip_ansi(res.stdout + res.stderr)
        lines = [l for l in output.strip().splitlines() if "zzz_no_match" in l]
        self.assertEqual(len(lines), 0)

    def test_03_grep_nonexistent_file(self):
        """grep on nonexistent file should fail."""
        res = self.gcs(["grep", "test", f"{self.test_dir}/no_file.txt"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
