EXPECTED_CPU_LIMIT = 40.0
import unittest
import subprocess
import os
import sys
import shutil
from pathlib import Path

class TestPythonPipUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON"
        
        # Find a supported version
        import re
        result = subprocess.run([str(cls.python_tool), "--py-list"], capture_output=True, text=True)
        cls.version = None
        capture = False
        for line in result.stdout.splitlines():
            clean_line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line).strip()
            if "Supported versions" in clean_line:
                capture = True
                continue
            if capture:
                if clean_line and not clean_line.startswith("Full result"):
                    cls.version = clean_line.split()[0]
                    break
        
        if not cls.version:
            raise unittest.SkipTest("No supported versions found.")
            
        # Ensure it's installed
        subprocess.run([str(cls.python_tool), "--py-install", cls.version], capture_output=True)
        
        # VERIFY that we are using the managed python
        res = subprocess.run([str(cls.python_tool), "--py-version", cls.version, "-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
        if "tool/PYTHON/data/install" not in res.stdout:
            raise unittest.SkipTest(f"PYTHON tool is falling back to system python: {res.stdout.strip()}")

    def test_pip_install_and_import(self):
        """Verify that we can pip install a package and then import it."""
        package = "pyjokes" # Small, no dependencies, fun
        
        # 1. Uninstall if already there to ensure clean test
        subprocess.run([str(self.python_tool), "--py-version", self.version, "-m", "pip", "uninstall", "-y", package], capture_output=True)
        
        # 2. Verify it's NOT importable
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-c", f"import {package}"], capture_output=True)
        self.assertNotEqual(res.returncode, 0)
        
        # 3. Install it
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-m", "pip", "install", package], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"pip install failed: {res.stderr}")
        
        # 4. Verify it's NOW importable
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-c", f"import {package}; print({package}.get_joke())"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import failed after install: {res.stderr}")
        self.assertTrue(len(res.stdout.strip()) > 10)

    def test_requests_availability(self):
        """Specifically verify requests can be installed and used, as reported by user."""
        package = "requests"
        
        # Ensure it's installed
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-m", "pip", "install", package], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"pip install requests failed: {res.stderr}")
        
        # Verify usage
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-c", "import requests; print(requests.__name__)"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import requests failed: {res.stderr}")
        self.assertEqual(res.stdout.strip(), "requests")

    def test_pip_installed_executable(self):
        """Verify that a package installed via pip that provides an executable is available in PATH."""
        package = "pyjokes"
        
        # 1. Install
        subprocess.run([str(self.python_tool), "--py-version", self.version, "-m", "pip", "install", package], capture_output=True)
        
        # 2. Check if the executable is found when running via our proxy
        # We use a trick: run python and check shutil.which
        code = f"import shutil; import os; print(shutil.which('{package}'))"
        res = subprocess.run([str(self.python_tool), "--py-version", self.version, "-c", code], capture_output=True, text=True)
        
        self.assertEqual(res.returncode, 0)
        exe_path = res.stdout.strip()
        self.assertIsNotNone(exe_path)
        self.assertIn("tool/PYTHON/data/install", exe_path)
        self.assertTrue(os.access(exe_path, os.X_OK))

if __name__ == "__main__":
    unittest.main()

