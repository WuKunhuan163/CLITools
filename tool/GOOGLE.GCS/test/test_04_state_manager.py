EXPECTED_CPU_LIMIT = 60.0
import unittest
import sys
import tempfile
import shutil
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestGCSStateManager(unittest.TestCase):
    """Test state manager operations using a temporary directory."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        tool_dir = self.tmpdir / "tool" / "GOOGLE.GCS" / "data"
        tool_dir.mkdir(parents=True, exist_ok=True)

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_state",
            str(project_root / "tool" / "GOOGLE.GCS" / "logic" / "state.py")
        )
        state_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(state_mod)
        self.GCSStateManager = state_mod.GCSStateManager
        self.mgr = self.GCSStateManager(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_01_initial_state(self):
        """Fresh state manager should have exactly one default shell."""
        shells = self.mgr.list_shells()
        self.assertEqual(len(shells), 1)
        self.assertEqual(shells[0][1], "default")

    def test_02_create_shell(self):
        """Creating a shell should add it and make it active."""
        new_id = self.mgr.create_shell("test_shell")
        shells = self.mgr.list_shells()
        self.assertEqual(len(shells), 2)
        self.assertEqual(self.mgr.get_active_shell_id(), new_id)

    def test_03_switch_shell(self):
        """Switching shells should change the active shell."""
        shells = self.mgr.list_shells()
        first_id = shells[0][0]
        new_id = self.mgr.create_shell("another")
        self.assertEqual(self.mgr.get_active_shell_id(), new_id)
        self.assertTrue(self.mgr.switch_shell(first_id))
        self.assertEqual(self.mgr.get_active_shell_id(), first_id)

    def test_04_switch_invalid(self):
        """Switching to a non-existent shell should return False."""
        self.assertFalse(self.mgr.switch_shell("invalid_id"))

    def test_05_update_shell(self):
        """Updating shell properties should persist."""
        sid = self.mgr.get_active_shell_id()
        self.mgr.update_shell(sid, current_path="~/projects", current_folder_id="abc123")
        info = self.mgr.get_shell_info(sid)
        self.assertEqual(info["current_path"], "~/projects")
        self.assertEqual(info["current_folder_id"], "abc123")

    def test_06_persistence(self):
        """State should persist across instances."""
        self.mgr.create_shell("persistent_shell")
        mgr2 = self.GCSStateManager(self.tmpdir)
        shells = mgr2.list_shells()
        names = [s[1] for s in shells]
        self.assertIn("persistent_shell", names)

    def test_07_get_shell_info(self):
        """get_shell_info should return dict with expected keys."""
        info = self.mgr.get_shell_info()
        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("created_at", info)
        self.assertIn("last_used", info)

    def test_08_get_shell_info_nonexistent(self):
        """get_shell_info for invalid ID should return None."""
        result = self.mgr.get_shell_info("nonexistent")
        self.assertIsNone(result)

    def test_09_default_shell_type(self):
        """Default shell should have shell_type 'bash'."""
        info = self.mgr.get_shell_info()
        self.assertEqual(info.get("shell_type", "bash"), "bash")

    def test_10_update_shell_type(self):
        """Updating shell_type should persist."""
        sid = self.mgr.get_active_shell_id()
        self.mgr.update_shell(sid, shell_type="zsh")
        info = self.mgr.get_shell_info(sid)
        self.assertEqual(info["shell_type"], "zsh")

    def test_11_create_shell_with_type(self):
        """Creating a shell with custom shell_type should store it."""
        new_id = self.mgr.create_shell("zsh_shell", shell_type="zsh")
        info = self.mgr.get_shell_info(new_id)
        self.assertEqual(info["shell_type"], "zsh")


if __name__ == "__main__":
    unittest.main()
