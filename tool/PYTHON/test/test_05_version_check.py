EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
from pathlib import Path

class TestPythonVersion(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.python_bin = self.project_root / "bin" / "PYTHON" / "PYTHON"

    def test_python_list(self):
        """Verify PYTHON --py-list returns supported versions with two-pass check."""
        import re
        res = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        # Accept either English or Chinese header
        plain = re.sub(r'\x1b\[[0-9;]*m', '', res.stdout)
        self.assertTrue(
            "Supported versions" in plain or "支持的版本" in plain,
            f"Expected version list header, got: {plain[:200]}"
        )

        import time
        start = time.time()
        try:
            res = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True, timeout=5)
            duration = time.time() - start
            self.assertEqual(res.returncode, 0)
            plain = re.sub(r'\x1b\[[0-9;]*m', '', res.stdout)
            self.assertTrue(
                "Supported versions" in plain or "支持的版本" in plain,
            )
            self.assertLess(duration, 5.0, f"Cached list took too long: {duration:.2f}s")
        except subprocess.TimeoutExpired:
            self.fail("PYTHON --py-list (cached) timed out after 5 seconds")
        
    def test_python_exec_identity(self):
        """Verify PYTHON proxy uses the correct version (or system fallback)."""
        # Note: In a test environment, the isolated Python might not be installed yet.
        # We check if it's installed; if so, verify it. Otherwise, we verify the fallback works.
        import re as _re
        res_list = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True)
        plain_list = _re.sub(r'\x1b\[[0-9;]*m', '', res_list.stdout)
        is_installed = "(installed)" in plain_list or "(已安装)" in plain_list
        
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

