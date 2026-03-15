"""Test PayPal operations via Chrome CDP.

Skips automatically when CDP is unavailable or no PayPal tab is open.
"""
import unittest
import sys
from pathlib import Path

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


def _tab_exists():
    from tool.PAYPAL.logic.chrome.api import find_paypal_tab
    return find_paypal_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No PayPal tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestPayPalAuthState(unittest.TestCase):
    def test_get_auth_state(self):
        from tool.PAYPAL.logic.chrome.api import get_auth_state
        r = get_auth_state()
        self.assertIn("authenticated", r)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestPayPalPageInfo(unittest.TestCase):
    def test_get_page_info(self):
        from tool.PAYPAL.logic.chrome.api import get_page_info
        r = get_page_info()
        self.assertTrue(r.get("ok"), f"get_page_info failed: {r}")
        self.assertIn("url", r)
        self.assertIn("paypal", r.get("url", "").lower())


if __name__ == "__main__":
    unittest.main()
