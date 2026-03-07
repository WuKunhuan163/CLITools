"""Test Chrome CDP availability via the GOOGLE tool's session module."""
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


class TestMcpCdpAvailable(unittest.TestCase):

    def test_cdp_availability_check(self):
        """is_chrome_cdp_available returns bool without error."""
        from logic.chrome.session import is_chrome_cdp_available
        result = is_chrome_cdp_available()
        self.assertIsInstance(result, bool)

    def test_list_tabs_when_available(self):
        """list_tabs returns a list when CDP is reachable."""
        from logic.chrome.session import is_chrome_cdp_available, list_tabs
        if not is_chrome_cdp_available():
            self.skipTest("Chrome CDP not available")
        tabs = list_tabs()
        self.assertIsInstance(tabs, list)
        self.assertGreater(len(tabs), 0)

    def test_cdp_session_evaluate(self):
        """CDPSession can evaluate simple JS when CDP is reachable."""
        from logic.chrome.session import is_chrome_cdp_available, list_tabs, CDPSession
        if not is_chrome_cdp_available():
            self.skipTest("Chrome CDP not available")
        tabs = list_tabs()
        page_tabs = [t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if not page_tabs:
            self.skipTest("No page tabs with WebSocket URL")
        session = CDPSession(page_tabs[0]["webSocketDebuggerUrl"])
        try:
            result = session.evaluate("1 + 1")
            self.assertEqual(result, 2)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
