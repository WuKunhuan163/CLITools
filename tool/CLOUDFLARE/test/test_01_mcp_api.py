"""Test Cloudflare API operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Cloudflare tab is open.
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
SKIP_TAB = "No Cloudflare dashboard tab found"


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
        """get_account returns account name and ID."""
        from tool.CLOUDFLARE.logic.chrome.api import get_account
        r = get_account()
        self.assertTrue(r.get("success"), f"get_account failed: {r}")
        self.assertIn("id", r.get("result", {}))
        self.assertIn("name", r.get("result", {}))


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareZones(unittest.TestCase):

    def test_list_zones(self):
        """list_zones returns a result list (may be empty)."""
        from tool.CLOUDFLARE.logic.chrome.api import list_zones
        r = list_zones(per_page=5)
        self.assertTrue(r.get("success"), f"list_zones failed: {r}")
        self.assertIsInstance(r.get("result"), list)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflareWorkers(unittest.TestCase):

    def test_list_workers(self):
        """list_workers returns a result list (may be empty)."""
        from tool.CLOUDFLARE.logic.chrome.api import list_workers
        r = list_workers()
        self.assertTrue(r.get("success"), f"list_workers failed: {r}")
        self.assertIsInstance(r.get("result"), list)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestCloudflarePages(unittest.TestCase):

    def test_list_pages(self):
        """list_pages_projects returns a result list (may be empty)."""
        from tool.CLOUDFLARE.logic.chrome.api import list_pages_projects
        r = list_pages_projects()
        self.assertTrue(r.get("success"), f"list_pages failed: {r}")
        self.assertIsInstance(r.get("result"), list)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Cloudflare tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Cloudflare tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
