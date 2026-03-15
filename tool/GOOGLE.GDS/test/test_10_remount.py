EXPECTED_CPU_LIMIT = 60.0
import unittest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _has_config():
    config_path = project_root / "data" / "config.json"
    return config_path.exists()


class TestRemountScriptGeneration(unittest.TestCase):
    """Test remount script generation logic."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gcs_remount",
            str(project_root / "tool" / "GOOGLE.GDS" / "logic" / "remount.py")
        )
        cls.remount = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.remount)

    @unittest.skipUnless(_has_config(), "GDS config.json not found")
    def test_01_generate_remount_script(self):
        """generate_remount_script should produce a valid script and metadata."""
        script, metadata = self.remount.generate_remount_script(project_root)
        if not script:
            self.skipTest(f"Remount script generation skipped: {metadata}")
        self.assertIsInstance(script, str)
        self.assertIn("drive", script.lower())
        self.assertIn("ts", metadata)
        self.assertIn("session_hash", metadata)

    @unittest.skipUnless(_has_config(), "GDS config.json not found")
    def test_02_remount_metadata_fields(self):
        """Remount metadata should contain required fields."""
        script, metadata = self.remount.generate_remount_script(project_root)
        if not script:
            self.skipTest(f"Remount script generation skipped: {metadata}")
        self.assertIn("ts", metadata)
        self.assertIn("session_hash", metadata)
        self.assertTrue(len(metadata["session_hash"]) > 0)


if __name__ == "__main__":
    unittest.main()
