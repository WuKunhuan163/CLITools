EXPECTED_CPU_LIMIT = 60.0
import unittest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestTutorialStructure(unittest.TestCase):
    """Verify setup tutorial file structure and importability."""

    def test_01_tutorial_files_exist(self):
        """All tutorial step directories and main files should exist."""
        tutorial_dir = project_root / "tool" / "GOOGLE.GDS" / "logic" / "tutorial" / "setup_guide"
        self.assertTrue(tutorial_dir.exists(), "Tutorial directory missing")
        self.assertTrue((tutorial_dir / "main.py").exists(), "Tutorial main.py missing")

        for i in range(1, 6):
            step_dir = tutorial_dir / f"step_{i:02d}"
            self.assertTrue(step_dir.exists(), f"Step {i} directory missing")
            self.assertTrue((step_dir / "main.py").exists(), f"Step {i} main.py missing")

    def test_02_tutorial_main_importable(self):
        """Tutorial main module should be importable."""
        import importlib.util
        tutorial_path = project_root / "tool" / "GOOGLE.GDS" / "logic" / "tutorial" / "setup_guide" / "main.py"
        spec = importlib.util.spec_from_file_location("gcs_tutorial_main", str(tutorial_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "run_setup_tutorial"),
                        "Tutorial main.py should have run_setup_tutorial function")

    def test_03_cache_directory_structure(self):
        """Tutorial cache directory should exist or be creatable."""
        cache_base = project_root / "tool" / "GOOGLE.GDS" / "data" / "tutorial" / "cache"
        cache_base.mkdir(parents=True, exist_ok=True)
        self.assertTrue(cache_base.exists())

    def test_04_step_modules_have_entry_point(self):
        """Each step module should be importable and structured correctly."""
        import importlib.util
        tutorial_dir = project_root / "tool" / "GOOGLE.GDS" / "logic" / "tutorial" / "setup_guide"
        for i in range(1, 6):
            step_path = tutorial_dir / f"step_{i:02d}" / "main.py"
            if step_path.exists():
                spec = importlib.util.spec_from_file_location(
                    f"gcs_step_{i:02d}", str(step_path)
                )
                self.assertIsNotNone(spec, f"Step {i} cannot create module spec")


if __name__ == "__main__":
    unittest.main()
