"""
GCS Remote edit Test

Tests edit command for modifying remote files.
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
class TestRemoteEdit(MCPTestCase):
    """Test edit command for remote file modification."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(ts.encode()).hexdigest()[:6]
        cls.test_dir = f"~/tmp/gcs_edit_test_{ts}_{h}"
        cls.gcs(cls, [f"mkdir -p {cls.test_dir}"])
        cls.gcs(cls, [f'echo "original content" > {cls.test_dir}/edit_target.txt'])

    def test_01_edit_replace(self):
        """edit should replace content in a remote file."""
        import json
        spec = json.dumps([["original content", "modified content"]])
        res = self.gcs(["edit", f"{self.test_dir}/edit_target.txt", spec], timeout=300)
        self.assertSuccess(res, "edit failed")

    def test_02_verify_edit(self):
        """After edit, read should show the modified content."""
        res = self.gcs(["read", f"{self.test_dir}/edit_target.txt", "--force"])
        self.assertSuccess(res, "read after edit failed")
        self.assertOutput(res, "modified content")

    def test_03_edit_nonexistent(self):
        """edit on nonexistent file should fail."""
        import json
        spec = json.dumps([["old", "new"]])
        res = self.gcs(["edit", f"{self.test_dir}/no_such_file.txt", spec])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
