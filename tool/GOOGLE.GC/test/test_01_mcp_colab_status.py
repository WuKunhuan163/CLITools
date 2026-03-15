"""Test Google Colab tab detection and status via CDP."""
import unittest
import sys
from pathlib import Path

EXPECTED_TIMEOUT = 15

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)


def _cdp_enabled():
    from logic.chrome.session import is_chrome_cdp_available
    return is_chrome_cdp_available()


class TestMcpColabStatus(unittest.TestCase):

    def test_find_colab_tab(self):
        """find_colab_tab returns a dict with url and webSocketDebuggerUrl."""
        if not _cdp_enabled():
            self.skipTest("Chrome CDP not available")
        from tool.GOOGLE.logic.chrome.colab import find_colab_tab
        tab = find_colab_tab()
        if tab is None:
            self.skipTest("No Colab tab found (not a failure, just not open)")
        self.assertIn("url", tab)
        self.assertIn("colab", tab["url"].lower())
        self.assertIn("webSocketDebuggerUrl", tab)


class TestMcpColabInject(unittest.TestCase):

    def test_inject_and_execute(self):
        """inject_and_execute runs Python code and detects completion marker."""
        if not _cdp_enabled():
            self.skipTest("Chrome CDP not available")
        from tool.GOOGLE.logic.chrome.colab import find_colab_tab, inject_and_execute
        tab = find_colab_tab()
        if tab is None:
            self.skipTest("No Colab tab found")
        marker = "GC_UNIT_TEST_OK"
        result = inject_and_execute(
            f"print('{marker}')",
            timeout=30,
            done_marker=marker,
        )
        self.assertTrue(result.get("success"), f"Inject failed: {result.get('error')}")
        self.assertIn(marker, result.get("output", ""))


if __name__ == "__main__":
    unittest.main()
