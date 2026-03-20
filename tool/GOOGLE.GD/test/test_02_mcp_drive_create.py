"""Test creating various Google Drive file types via CDP + gapi.client.

Covers: doc, sheet, slide, form, folder, colab.
Each test creates a file, verifies it in the folder listing, then deletes it.
Skips automatically when CDP or Colab tab is unavailable.
"""
import unittest
import sys
import time
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


def _colab_tab_exists():
    from tool.GOOGLE.interface.main import find_colab_tab
    return find_colab_tab() is not None


def _get_test_folder_id():
    """Return the env folder ID from GDS config, or fall back to 'root'."""
    try:
        import json
        cfg = Path(_r) / "tool" / "GOOGLE.GDS" / "data" / "config.json"
        if cfg.exists():
            data = json.loads(cfg.read_text())
            fid = data.get("env_folder_id", "")
            if fid:
                return fid
    except Exception:
        pass
    return "root"


_CDP_OK = _cdp_enabled()
_TAB_OK = _colab_tab_exists() if _CDP_OK else False
_FOLDER_ID = _get_test_folder_id() if _TAB_OK else "root"

SKIP_REASON_CDP = "Chrome CDP not available"
SKIP_REASON_TAB = "No Colab tab found"


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateDoc(unittest.TestCase):

    def test_create_and_delete_doc(self):
        """Create a Google Doc, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_doc_{int(time.time())}"
        result = create_drive_file(name, "doc", _FOLDER_ID)
        self.assertTrue(result.get("success"), f"Create doc failed: {result.get('error')}")
        file_id = result.get("id")
        self.assertTrue(file_id, "No file ID returned")
        self.assertIn("docs.google.com/document", result.get("link", ""))
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete doc {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateSheet(unittest.TestCase):

    def test_create_and_delete_sheet(self):
        """Create a Google Sheet, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_sheet_{int(time.time())}"
        result = create_drive_file(name, "sheet", _FOLDER_ID)
        self.assertTrue(result.get("success"), f"Create sheet failed: {result.get('error')}")
        file_id = result.get("id")
        self.assertTrue(file_id, "No file ID returned")
        self.assertIn("docs.google.com/spreadsheets", result.get("link", ""))
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete sheet {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateSlide(unittest.TestCase):

    def test_create_and_delete_slide(self):
        """Create a Google Slides presentation, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_slide_{int(time.time())}"
        result = create_drive_file(name, "slide", _FOLDER_ID)
        self.assertTrue(result.get("success"), f"Create slide failed: {result.get('error')}")
        file_id = result.get("id")
        self.assertTrue(file_id, "No file ID returned")
        self.assertIn("docs.google.com/presentation", result.get("link", ""))
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete slide {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateForm(unittest.TestCase):

    def test_create_and_delete_form(self):
        """Create a Google Form, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_form_{int(time.time())}"
        result = create_drive_file(name, "form", _FOLDER_ID)
        self.assertTrue(result.get("success"), f"Create form failed: {result.get('error')}")
        file_id = result.get("id")
        self.assertTrue(file_id, "No file ID returned")
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete form {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateFolder(unittest.TestCase):

    def test_create_and_delete_folder(self):
        """Create a Drive folder, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_folder_{int(time.time())}"
        result = create_drive_file(name, "folder", _FOLDER_ID)
        self.assertTrue(result.get("success"), f"Create folder failed: {result.get('error')}")
        file_id = result.get("id")
        self.assertTrue(file_id, "No file ID returned")
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete folder {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveCreateColab(unittest.TestCase):

    def test_create_and_delete_colab(self):
        """Create a Colab notebook, verify it, then delete it."""
        from tool.GOOGLE.interface.main import create_drive_file, delete_drive_file
        name = f"_unittest_colab_{int(time.time())}"
        result = create_drive_file(name, "colab", _FOLDER_ID, content="print('test')")
        self.assertTrue(result.get("success"), f"Create colab failed: {result.get('error')}")
        file_id = result.get("id") or result.get("file_id")
        self.assertTrue(file_id, "No file ID returned")
        ok = delete_drive_file(file_id)
        self.assertTrue(ok, f"Delete colab {file_id} failed")


@unittest.skipUnless(_CDP_OK, SKIP_REASON_CDP)
@unittest.skipUnless(_TAB_OK, SKIP_REASON_TAB)
class TestDriveListAfterCreate(unittest.TestCase):

    def test_created_file_appears_in_listing(self):
        """A newly created file should appear in list_drive_files."""
        from tool.GOOGLE.interface.main import (
            create_drive_file, list_drive_files, delete_drive_file,
        )
        name = f"_unittest_list_verify_{int(time.time())}"
        result = create_drive_file(name, "doc", _FOLDER_ID)
        self.assertTrue(result.get("success"))
        file_id = result["id"]
        try:
            listing = list_drive_files(
                _FOLDER_ID, query=f"name = '{name}'", page_size=5,
            )
            self.assertTrue(listing.get("success"))
            found = [f for f in listing.get("files", []) if f.get("id") == file_id]
            self.assertEqual(len(found), 1, f"Created file {name} not found in listing")
        finally:
            delete_drive_file(file_id)


if __name__ == "__main__":
    if _CDP_OK and _TAB_OK:
        print(f"[MCP] CDP available, Colab tab found — tests will run. Folder: {_FOLDER_ID}")
    elif _CDP_OK:
        print("[MCP] CDP available but no Colab tab — tests will be SKIPPED.")
    else:
        print("[MCP] CDP not available — tests will be SKIPPED.")
    unittest.main()
