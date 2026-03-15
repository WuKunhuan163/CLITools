"""Test GCS echo command via MCP (CDP auto-injection)."""
import unittest
import sys
from pathlib import Path

EXPECTED_TIMEOUT = 60

_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp_test_base import MCPTestCase


class TestMcpEcho(MCPTestCase):

    def test_echo_mcp(self):
        """GCS echo <text> --mcp executes and returns the echoed text."""
        if not self._mcp_available:
            self.skipTest("MCP (CDP) not available")
        result = self.gcs(["echo", "MCP_ECHO_UNIT_TEST"])
        self.assertSuccess(result, "GCS echo --mcp failed")
        self.assertOutput(result, "MCP_ECHO_UNIT_TEST")


if __name__ == "__main__":
    unittest.main()
