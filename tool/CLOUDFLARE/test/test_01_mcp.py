"""MCP unit tests for CLOUDFLARE tool via Chrome CDP.

Tests are skipped automatically when CDP is unavailable or the
Cloudflare dashboard tab is not open.
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


def _cf_tab_exists():
    from tool.CLOUDFLARE.logic.chrome.api import find_cloudflare_tab
    return find_cloudflare_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _cf_tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "Cloudflare dashboard tab not found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareUser(unittest.TestCase):
    def test_get_user(self):
        """get_user returns email and username."""
        from tool.CLOUDFLARE.logic.chrome.api import get_user
        r = get_user()
        self.assertTrue(r.get("success"), f"get_user failed: {r}")
        self.assertIn("email", r.get("result", {}))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareAccount(unittest.TestCase):
    def test_get_account(self):
        """get_account returns account info."""
        from tool.CLOUDFLARE.logic.chrome.api import get_account
        r = get_account()
        self.assertTrue(r.get("success"), f"get_account failed: {r}")
        self.assertIn("id", r.get("result", {}))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareZones(unittest.TestCase):
    def test_list_zones(self):
        """list_zones returns a result list (may be empty)."""
        from tool.CLOUDFLARE.logic.chrome.api import list_zones
        r = list_zones()
        self.assertTrue(r.get("success"), f"list_zones failed: {r}")
        self.assertIsInstance(r.get("result"), list)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareWorkers(unittest.TestCase):
    def test_list_workers(self):
        """list_workers returns a result list."""
        from tool.CLOUDFLARE.logic.chrome.api import list_workers
        r = list_workers()
        self.assertTrue(r.get("success"), f"list_workers failed: {r}")
        self.assertIsInstance(r.get("result"), list)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Cloudflare tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Cloudflare tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
