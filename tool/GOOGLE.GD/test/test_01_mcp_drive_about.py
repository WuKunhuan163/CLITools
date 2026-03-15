"""Test Google Drive 'about' query via CDP."""
import unittest
import sys
from pathlib import Path

EXPECTED_TIMEOUT = 20

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


def _colab_tab_exists():
    from tool.GOOGLE.interface.main import find_colab_tab
    return find_colab_tab() is not None


class TestMcpDriveAbout(unittest.TestCase):

    def test_drive_about(self):
        """get_drive_about returns user and quota info."""
        if not _cdp_enabled():
            self.skipTest("Chrome CDP not available")
        if not _colab_tab_exists():
            self.skipTest("No Colab tab found")
        from tool.GOOGLE.interface.main import get_drive_about
        result = get_drive_about()
        self.assertTrue(result.get("success"), f"Drive about failed: {result.get('error')}")
        data = result.get("data", {})
        self.assertIn("user", data)
        self.assertIn("emailAddress", data["user"])


class TestMcpDriveList(unittest.TestCase):

    def test_list_root_folder(self):
        """list_drive_files with 'root' returns files."""
        if not _cdp_enabled():
            self.skipTest("Chrome CDP not available")
        if not _colab_tab_exists():
            self.skipTest("No Colab tab found")
        from tool.GOOGLE.interface.main import list_drive_files
        result = list_drive_files("root", page_size=3)
        self.assertTrue(result.get("success"), f"Drive list failed: {result.get('error')}")
        self.assertIsInstance(result.get("files"), list)


if __name__ == "__main__":
    unittest.main()
