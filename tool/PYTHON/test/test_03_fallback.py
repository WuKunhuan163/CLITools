import unittest
import subprocess
import os
from pathlib import Path

class TestPythonFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON"

    def test_system_fallback(self):
        """Test fallback to system python when specified version is not found."""
        # Use a version that we know is not installed (but supported in list, maybe?)
        # For this test, we can just use a version that doesn't exist.
        result = subprocess.run([str(self.python_tool), "--py-version", "nonexistent_version", "--version"], capture_output=True, text=True)
        # It should still succeed by using system python
        self.assertEqual(result.returncode, 0)
        self.assertIn("Python", result.stdout)

    def test_direct_call(self):
        """Test calling without any --py flags behaves like system python."""
        result = subprocess.run([str(self.python_tool), "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Python", result.stdout)

if __name__ == "__main__":
    unittest.main()

