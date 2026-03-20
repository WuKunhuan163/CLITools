"""Test Intercom operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Intercom tab is open.
"""
import unittest
import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)


def _cdp_enabled():
    from interface.chrome import is_chrome_cdp_available
    return is_chrome_cdp_available()


def _tab_exists():
    from tool.INTERCOM.logic.utils.chrome.api import find_intercom_tab
    return find_intercom_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No Intercom tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestIntercomAuthState(unittest.TestCase):

    def test_get_auth_state(self):
        """get_auth_state returns authentication info."""
        from tool.INTERCOM.logic.utils.chrome.api import get_auth_state
        r = get_auth_state()
        self.assertIn("authenticated", r)
        self.assertIn("pageTitle", r)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestIntercomPageInfo(unittest.TestCase):

    def test_get_page_info(self):
        """get_page_info returns title and URL."""
        from tool.INTERCOM.logic.utils.chrome.api import get_page_info
        r = get_page_info()
        self.assertTrue(r.get("ok"), f"get_page_info failed: {r}")
        self.assertIn("url", r)
        self.assertIn("title", r)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Intercom tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Intercom tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
