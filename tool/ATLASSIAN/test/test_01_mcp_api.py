"""Test Atlassian API operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Atlassian tab is open.
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


def _atlassian_tab_exists():
    from tool.ATLASSIAN.logic.utils.chrome.api import find_atlassian_tab
    return find_atlassian_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _atlassian_tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No Atlassian tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAtlassianMe(unittest.TestCase):

    def test_get_me(self):
        """get_me returns user name, email, and account status."""
        from tool.ATLASSIAN.logic.utils.chrome.api import get_me
        r = get_me()
        self.assertTrue(r.get("ok"), f"get_me failed: {r}")
        data = r.get("data", {})
        self.assertIsInstance(data, dict)
        self.assertIn("name", data)
        self.assertIn("email", data)
        self.assertIn("account_status", data)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAtlassianNotifications(unittest.TestCase):

    def test_get_notifications(self):
        """get_notifications returns a data structure with hasUnread."""
        from tool.ATLASSIAN.logic.utils.chrome.api import get_notifications
        r = get_notifications(max_count=5)
        self.assertTrue(r.get("ok"), f"get_notifications failed: {r}")
        data = r.get("data", {})
        self.assertIn("hasUnread", data)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAtlassianPreferences(unittest.TestCase):

    def test_get_user_preferences(self):
        """get_user_preferences returns locale and account info."""
        from tool.ATLASSIAN.logic.utils.chrome.api import get_user_preferences
        r = get_user_preferences()
        self.assertTrue(r.get("ok"), f"get_user_preferences failed: {r}")
        data = r.get("data", {})
        self.assertIn("name", data)
        self.assertIn("locale", data)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Atlassian tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Atlassian tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
