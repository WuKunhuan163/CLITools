EXPECTED_CPU_LIMIT = 40.0
import unittest
import subprocess
import os
from pathlib import Path

class TestPythonPipUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON" / "PYTHON"
        
        # Find a supported version, favoring installed ones
        import re
        result = subprocess.run([str(cls.python_tool), "--py-list"], capture_output=True, text=True)
        cls.version = None
        capture = False
        supported_versions = []
        for line in result.stdout.splitlines():
            # Strip ANSI escape codes
            clean_line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line).strip()
            if "Supported versions" in clean_line:
                capture = True
                continue
            if capture:
                if clean_line and not clean_line.startswith("Full result"):
                    v = clean_line.split()[0]
                    # More robust check for installed status
                    if "installed" in clean_line.lower():
                        cls.version = v
                        break
                    supported_versions.append(v)
        
        if not cls.version and supported_versions:
            cls.version = supported_versions[0]
        
        if not cls.version:
            raise unittest.SkipTest("No supported versions found.")
            
        # Ensure it's installed
        subprocess.run([str(cls.python_tool), "--py-install", cls.version], capture_output=True)
        
        # VERIFY that we are using the managed python
        res = subprocess.run([str(cls.python_tool), "--no-warning", "--py-version", cls.version, "-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
        if "tool/PYTHON/data/install" not in res.stdout:
            # Try without --py-version if it's the default
            res = subprocess.run([str(cls.python_tool), "--no-warning", "-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
            if "tool/PYTHON/data/install" not in res.stdout:
                # If we're testing the default version and it's installed, it should work
                pass
            else:
                cls.version = None # Force re-selection or fail
        
        if not cls.version:
             raise unittest.SkipTest(f"PYTHON tool is falling back to system python for {cls.version}")

    def test_pip_install_and_import(self):
        """Verify that we can pip install a package and then import it."""
        package = "pyjokes"
        
        # 1. Uninstall if already there
        subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-m", "pip", "uninstall", "-y", package], capture_output=True)
        
        # 2. Verify it's NOT importable
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-c", f"import {package}"], capture_output=True)
        self.assertNotEqual(res.returncode, 0)
        
        # 3. Install it
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-m", "pip", "install", package], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"pip install failed: {res.stderr}")
        
        # 4. Verify it's NOW importable
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-c", f"import {package}; print({package}.get_joke())"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import failed after install: {res.stderr}")
        self.assertTrue(len(res.stdout.strip()) > 10)

    def test_requests_availability(self):
        """Specifically verify requests can be used in managed environment."""
        # Ensure it's installed
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-m", "pip", "install", "requests"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"pip install requests failed: {res.stderr}")
        
        # Verify usage
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-c", "import requests; print(requests.__name__)"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import requests failed: {res.stderr}")
        self.assertEqual(res.stdout.strip(), "requests")

    def test_pip_installed_executable(self):
        """Verify that a package installed via pip that provides an executable is available in PATH."""
        package = "pyjokes"
        
        # 1. Install
        subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-m", "pip", "install", package], capture_output=True)
        
        # 2. Check if the executable is found when running via our proxy
        # We use a trick: run python and check shutil.which
        code = f"import shutil; import os; print(f'PATH: {{os.environ.get(\"PATH\")}}'); print(shutil.which('{package}'))"
        res = subprocess.run([str(self.python_tool), "--no-warning", "--py-version", self.version, "-c", code], capture_output=True, text=True)
        
        self.assertEqual(res.returncode, 0)
        output_lines = res.stdout.strip().splitlines()
        exe_path = output_lines[-1]
        
        if "tool/PYTHON/data/install" not in exe_path:
            print(f"\nDEBUG INFO for {self.id()}:")
            print(f"Version: {self.version}")
            print(f"Output:\n{res.stdout}")
            
        self.assertIsNotNone(exe_path)
        self.assertIn("tool/PYTHON/data/install", exe_path)
        self.assertTrue(os.access(exe_path, os.X_OK))

if __name__ == "__main__":
    unittest.main()
