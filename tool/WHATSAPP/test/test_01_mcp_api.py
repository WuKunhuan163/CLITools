"""Test WhatsApp Web operations via Chrome CDP.

Skips automatically when CDP is unavailable or no WhatsApp tab is open.
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
    from tool.WHATSAPP.logic.chrome.api import find_whatsapp_tab
    return find_whatsapp_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No WhatsApp tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestWhatsAppAuthState(unittest.TestCase):
    def test_get_auth_state(self):
        from tool.WHATSAPP.logic.chrome.api import get_auth_state
        r = get_auth_state()
        self.assertIn("authenticated", r)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestWhatsAppPageInfo(unittest.TestCase):
    def test_get_page_info(self):
        from tool.WHATSAPP.logic.chrome.api import get_page_info
        r = get_page_info()
        self.assertTrue(r.get("ok"), f"get_page_info failed: {r}")
        self.assertIn("whatsapp", r.get("url", "").lower())


if __name__ == "__main__":
    unittest.main()
