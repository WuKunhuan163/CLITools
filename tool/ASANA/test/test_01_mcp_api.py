"""Test Asana API operations via Chrome CDP.

Skips automatically when CDP is unavailable or no Asana tab is open.
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


def _asana_tab_exists():
    from tool.ASANA.logic.chrome.api import find_asana_tab
    return find_asana_tab() is not None


_CDP_OK = _cdp_enabled()
_TAB_OK = _asana_tab_exists() if _CDP_OK else False

SKIP_CDP = "Chrome CDP not available"
SKIP_TAB = "No Asana tab found"


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAsanaMe(unittest.TestCase):

    def test_get_me(self):
        """get_me returns user name, email, and workspaces."""
        from tool.ASANA.logic.chrome.api import get_me
        r = get_me()
        data = r.get("data", {})
        self.assertTrue(data, f"get_me failed: {r}")
        self.assertIn("email", data)
        self.assertIn("name", data)
        self.assertIn("workspaces", data)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAsanaWorkspaces(unittest.TestCase):

    def test_list_workspaces(self):
        """list_workspaces returns a data list."""
        from tool.ASANA.logic.chrome.api import list_workspaces
        r = list_workspaces()
        ws = r.get("data", [])
        self.assertIsInstance(ws, list)
        self.assertGreater(len(ws), 0, "Expected at least one workspace")
        self.assertIn("gid", ws[0])
        self.assertIn("name", ws[0])


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAsanaProjects(unittest.TestCase):

    def test_list_projects(self):
        """list_projects returns a data list (may be empty)."""
        from tool.ASANA.logic.chrome.api import list_workspaces, list_projects
        ws = list_workspaces().get("data", [])
        if not ws:
            self.skipTest("No workspaces available")
        r = list_projects(ws[0]["gid"], limit=5)
        self.assertIsInstance(r.get("data", []), list)


@unittest.skipUnless(_CDP_OK, SKIP_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_TAB)
class TestAsanaTasks(unittest.TestCase):

    def test_list_tasks(self):
        """list_tasks returns a data list (may be empty)."""
        from tool.ASANA.logic.chrome.api import list_workspaces, list_tasks
        ws = list_workspaces().get("data", [])
        if not ws:
            self.skipTest("No workspaces available")
        r = list_tasks(ws[0]["gid"], limit=5)
        self.assertIsInstance(r.get("data", []), list)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print("[MCP] CDP available, Asana tab found - tests will run.")
    elif _CDP_OK:
        print("[MCP] CDP available but no Asana tab - tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available - tests will be SKIPPED.")
    unittest.main()
