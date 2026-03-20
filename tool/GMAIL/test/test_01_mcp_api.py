"""Test Gmail operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Gmail tab is open.
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
    from tool.GMAIL.logic.utils.chrome.api import find_gmail_tab
    return find_gmail_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No Gmail tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestGmailAuthState(unittest.TestCase):
    def test_get_auth_state(self):
        from tool.GMAIL.logic.utils.chrome.api import get_auth_state
        r = get_auth_state()
        self.assertIn("authenticated", r)
        self.assertTrue(r.get("ok"))

    def test_email_detected(self):
        from tool.GMAIL.logic.utils.chrome.api import get_auth_state
        r = get_auth_state()
        if r.get("authenticated"):
            self.assertIsNotNone(r.get("email"))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestGmailPageInfo(unittest.TestCase):
    def test_get_page_info(self):
        from tool.GMAIL.logic.utils.chrome.api import get_page_info
        r = get_page_info()
        self.assertTrue(r.get("ok"), f"get_page_info failed: {r}")
        self.assertIn("mail.google.com", r.get("url", ""))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestGmailInbox(unittest.TestCase):
    def test_get_inbox(self):
        from tool.GMAIL.logic.utils.chrome.api import get_inbox
        r = get_inbox(limit=5)
        self.assertTrue(r.get("ok"), f"get_inbox failed: {r}")
        self.assertIsInstance(r.get("emails"), list)


if __name__ == "__main__":
    unittest.main()
