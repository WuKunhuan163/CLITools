EXPECTED_CPU_LIMIT = 60.0
import unittest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestPathNormalization(unittest.TestCase):
    """Test logical path normalization without API calls."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_utils",
            str(project_root / "tool" / "GOOGLE.GDS" / "logic" / "utils.py")
        )
        cls.utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.utils)

    def test_01_normalize_tilde(self):
        """~ should normalize to ~."""
        self.assertEqual(self.utils._normalize_logical_path("~"), "~")

    def test_02_normalize_tilde_subpath(self):
        """~/foo/bar should stay as-is."""
        self.assertEqual(self.utils._normalize_logical_path("~/foo/bar"), "~/foo/bar")

    def test_03_normalize_dotdot(self):
        """~/a/b/.. should resolve to ~/a."""
        result = self.utils._normalize_logical_path("~/a/b/..")
        self.assertEqual(result, "~/a")

    def test_04_normalize_dot(self):
        """~/a/./b should resolve to ~/a/b."""
        result = self.utils._normalize_logical_path("~/a/./b")
        self.assertEqual(result, "~/a/b")

    def test_05_normalize_at(self):
        """@ should normalize to @."""
        self.assertEqual(self.utils._normalize_logical_path("@"), "@")

    def test_06_normalize_trailing_slash(self):
        """~/foo/ should normalize to ~/foo."""
        result = self.utils._normalize_logical_path("~/foo/")
        self.assertEqual(result, "~/foo")

    def test_07_normalize_dotdot_past_root(self):
        """~/.. should not go above ~."""
        result = self.utils._normalize_logical_path("~/..")
        self.assertEqual(result, "~")


class TestMountPathConversion(unittest.TestCase):
    """Test logical to mount path conversion."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_utils",
            str(project_root / "tool" / "GOOGLE.GDS" / "logic" / "utils.py")
        )
        cls.utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.utils)

    def test_01_tilde_to_mount(self):
        """~ should map to /content/drive/MyDrive/REMOTE_ROOT."""
        result = self.utils.logical_to_mount_path("~")
        self.assertIn("REMOTE_ROOT", result)
        self.assertTrue(result.startswith("/content/drive/MyDrive/"))

    def test_02_at_to_mount(self):
        """@ should map to /content/drive/MyDrive/REMOTE_ROOT/REMOTE_ENV."""
        result = self.utils.logical_to_mount_path("@")
        self.assertIn("REMOTE_ENV", result)

    def test_03_subpath_to_mount(self):
        """~/foo should map to /content/drive/MyDrive/REMOTE_ROOT/foo."""
        result = self.utils.logical_to_mount_path("~/foo")
        self.assertTrue(result.endswith("/foo"))
        self.assertIn("REMOTE_ROOT", result)


class TestExpandRemotePaths(unittest.TestCase):
    """Test ~ and @ expansion with quoting rules."""

    R = "/content/drive/MyDrive/REMOTE_ROOT"
    E = "/content/drive/MyDrive/REMOTE_ENV"

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_utils",
            str(project_root / "tool" / "GOOGLE.GDS" / "logic" / "utils.py")
        )
        cls.utils = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.utils)

    def _expand(self, cmd):
        return self.utils.expand_remote_paths(cmd, self.R, self.E)

    def test_01_bare_tilde(self):
        """Unquoted ~ should expand."""
        self.assertEqual(self._expand("echo ~"), f"echo {self.R}")

    def test_02_tilde_path(self):
        """~/path should expand."""
        self.assertEqual(self._expand("ls ~/tmp"), f"ls {self.R}/tmp")

    def test_03_at_path(self):
        """@/path should expand."""
        self.assertEqual(self._expand("ls @/env"), f"ls {self.E}/env")

    def test_04_double_quoted_tilde_preserved(self):
        """~ inside double quotes should NOT expand."""
        self.assertEqual(self._expand('echo "~"'), 'echo "~"')

    def test_05_single_quoted_tilde_preserved(self):
        """~ inside single quotes should NOT expand."""
        self.assertEqual(self._expand("echo '~'"), "echo '~'")

    def test_06_mixed_quoted_unquoted(self):
        """Only unquoted ~ should expand in mixed string."""
        result = self._expand("echo '~' and ~")
        self.assertIn(self.R, result)
        self.assertIn("'~'", result)

    def test_07_no_expansion_needed(self):
        """Command without ~ or @ should be unchanged."""
        self.assertEqual(self._expand("echo hello"), "echo hello")

    def test_08_multiple_paths(self):
        """Multiple paths in one command should all expand."""
        result = self._expand("cat ~/a @/b")
        self.assertIn(f"{self.R}/a", result)
        self.assertIn(f"{self.E}/b", result)


if __name__ == "__main__":
    unittest.main()
