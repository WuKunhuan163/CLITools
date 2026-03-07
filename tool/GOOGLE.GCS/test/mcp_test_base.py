"""
Shared base for MCP-enabled GCS tests.

When MCP (Chrome DevTools Protocol) is available, tests run automatically
via CDP injection. Otherwise, falls back to manual GUI interaction.
"""
import unittest
import subprocess
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path("/Applications/AITerminalTools")


def is_mcp_available():
    """Check if MCP (CDP) is available for automated testing."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from logic.cdp.colab import is_chrome_cdp_available, find_colab_tab
        if not is_chrome_cdp_available():
            return False
        tab = find_colab_tab()
        return tab is not None
    except Exception:
        return False


def has_service_account():
    """Check if the GCS service account key is configured."""
    key_path = PROJECT_ROOT / "data" / "google_cloud_console" / "console_key.json"
    return key_path.exists()


class MCPTestCase(unittest.TestCase):
    """Base test case that auto-adds --mcp when CDP is available."""

    _mcp_available = None
    gcs_bin = PROJECT_ROOT / "bin" / "GCS" / "GCS"

    @classmethod
    def setUpClass(cls):
        if cls._mcp_available is None:
            cls._mcp_available = is_mcp_available()
        if cls._mcp_available:
            print(f"[MCP] CDP available - tests will run automatically.")
        else:
            print(f"[MCP] CDP not available - tests require manual GUI interaction.")

    @staticmethod
    def strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def gcs(self, args, timeout=180, use_mcp=None):
        """Run a GCS command. Adds --mcp flag when CDP is available.
        
        Args:
            args: List of command arguments (after GCS)
            timeout: Subprocess timeout in seconds
            use_mcp: Override MCP usage (None = auto-detect)
        """
        cmd = [sys.executable, str(self.gcs_bin)] + args + ["--no-warning"]
        if (use_mcp is True) or (use_mcp is None and self._mcp_available):
            cmd.append("--mcp")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def assertOutput(self, result, expected_text, msg=None):
        """Assert that expected text appears in the command output."""
        output = self.strip_ansi(result.stdout)
        self.assertIn(expected_text, output,
                      msg or f"Expected '{expected_text}' in output:\n{output[:500]}")

    def assertSuccess(self, result, msg=None):
        """Assert command returned exit code 0."""
        self.assertEqual(result.returncode, 0,
                         msg or f"Command failed (rc={result.returncode}): {result.stderr[:300]}")
