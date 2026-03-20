"""Test Kling AI operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Kling tab is open.
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
    from tool.KLING.logic.utils.chrome.api import find_kling_tab
    return find_kling_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No Kling AI tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestKlingUserInfo(unittest.TestCase):

    def test_get_user_info(self):
        """get_user_info returns userId, userName, email from localStorage."""
        from tool.KLING.logic.utils.chrome.api import get_user_info
        r = get_user_info()
        self.assertTrue(r.get("ok"), f"get_user_info failed: {r}")
        d = r.get("data", {})
        self.assertTrue(d.get("userId"), "No userId")
        self.assertTrue(d.get("email"), "No email")


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestKlingPoints(unittest.TestCase):

    def test_get_points(self):
        """get_points returns a points value from DOM."""
        from tool.KLING.logic.utils.chrome.api import get_points
        r = get_points()
        self.assertTrue(r.get("ok"), f"get_points failed: {r}")
        self.assertIsNotNone(r.get("data", {}).get("points"))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestKlingPageInfo(unittest.TestCase):

    def test_get_page_info(self):
        """get_page_info returns title and URL."""
        from tool.KLING.logic.utils.chrome.api import get_page_info
        r = get_page_info()
        self.assertTrue(r.get("ok"), f"get_page_info failed: {r}")
        self.assertIn("url", r)
        self.assertIn("klingai", r.get("url", ""))


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Kling tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Kling tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
