EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
import sys
import re
from pathlib import Path

class TestPythonVersion(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.python_bin = self.project_root / "bin" / "PYTHON"

    def test_python_list(self):
        """Verify PYTHON --py-list returns supported versions with two-pass check."""
        # Pass 1: Remote scan (no timeout)
        res = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Supported versions", res.stdout)
        
        # Pass 2: Cached scan (must return within 5 seconds)
        import time
        start = time.time()
        try:
            res = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True, timeout=5)
            duration = time.time() - start
            self.assertEqual(res.returncode, 0)
            self.assertIn("Supported versions", res.stdout)
            self.assertLess(duration, 5.0, f"Cached list took too long: {duration:.2f}s")
        except subprocess.TimeoutExpired:
            self.fail("PYTHON --py-list (cached) timed out after 5 seconds")
        
    def test_python_exec_identity(self):
        """Verify PYTHON proxy uses the correct version (or system fallback)."""
        # Note: In a test environment, the isolated Python might not be installed yet.
        # We check if it's installed; if so, verify it. Otherwise, we verify the fallback works.
        res_list = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True)
        is_installed = "(installed)" in res_list.stdout
        
        res = subprocess.run([str(self.python_bin), "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        
        if is_installed:
            expected_version = "3.11.14"
            self.assertIn(expected_version, res.stdout)
        else:
            # Should be some Python 3
            self.assertIn("Python 3", res.stdout)

    def test_python_path_injection(self):
        """Verify project root is in sys.path when running via PYTHON proxy."""
        res = subprocess.run([str(self.python_bin), "-c", "import sys; print(sys.path)"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn(str(self.project_root), res.stdout)

if __name__ == "__main__":
    unittest.main()

