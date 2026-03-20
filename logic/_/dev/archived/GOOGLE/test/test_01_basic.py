import unittest
import subprocess
from pathlib import Path

class TestGoogleBasic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.google_tool = cls.project_root / "bin" / "GOOGLE" / "GOOGLE"

    def test_help(self):
        """Test GOOGLE help."""
        result = subprocess.run([str(self.google_tool), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("GOOGLE Tool", result.stdout)

    def test_install_list(self):
        """Test sub-tool installation and GCS list."""
        # Ensure installed
        subprocess.run([str(self.google_tool), "--install", "GCS"], capture_output=True)
        
        # Test gcs list
        result = subprocess.run([str(self.google_tool), "gcs", "--list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("GCS Shells", result.stdout)

if __name__ == "__main__":
    unittest.main()

