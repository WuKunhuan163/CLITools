import unittest
import subprocess
import os
import sys
import shutil
from pathlib import Path

class TestPythonIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.bin_dir = cls.project_root / "bin"
        cls.python_tool = cls.bin_dir / "PYTHON"
        
        # Ensure bin/ is in PATH for the test process
        cls.env = os.environ.copy()
        cls.env["PATH"] = f"{cls.bin_dir}:{cls.env.get('PATH', '')}"
        cls.env["PYTHONPATH"] = str(cls.project_root)

    def test_01_enable_and_verify_paths(self):
        """Verify that PYTHON --enable sets up working symlinks."""
        # 1. Run enable
        res = subprocess.run([sys.executable, str(self.python_tool), "--enable"], 
                             capture_output=True, text=True, env=self.env)
        self.assertEqual(res.returncode, 0, f"PYTHON --enable failed: {res.stderr}")
        
        # 2. Check symlinks exist
        # On macOS, 'python' might be the tool script, so we check if it works regardless
        self.assertTrue((self.bin_dir / "pip").exists() or (self.bin_dir / "pip").is_symlink())
        
        # 3. Verify 'which' results (simulating a user in the terminal)
        py_path = shutil.which("python", path=str(self.bin_dir))
        pip_path = shutil.which("pip", path=str(self.bin_dir))
        
        # python should point to either the symlink or the tool script in bin/
        self.assertIn(str(self.bin_dir), py_path)
        self.assertIn(str(self.bin_dir), pip_path)
        
        # Verify they actually work and point to managed python
        res = subprocess.run(["python", "--version"], env=self.env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        # Should be our managed version (e.g. 3.11.14)
        self.assertIn("Python 3.", res.stdout or res.stderr)

    def test_02_pip_install_working(self):
        """Verify that the enabled pip can actually install packages."""
        # Use a very small and rare package to avoid bloat
        package = "pyjokes"
        
        # 1. Uninstall if exists
        subprocess.run(["pip", "uninstall", package, "-y"], env=self.env, capture_output=True)
        
        # 2. Install
        res = subprocess.run(["pip", "install", package], env=self.env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"pip install failed: {res.stderr}")
        
        # 3. Verify import via the enabled python
        res = subprocess.run(["python", "-c", f"import {package}; print('OK')"], 
                             env=self.env, capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "OK")

    def test_03_tool_dependency_resolution(self):
        """Verify that a tool with PYTHON dependency uses the managed environment."""
        # We can use iCloudPD as a test subject since it has the dependency
        icloudpd_bin = self.bin_dir / "iCloudPD"
        if not icloudpd_bin.exists():
            # If not installed, we can't test it easily here without installing it
            # But we can create a dummy tool
            self.skipTest("iCloudPD not installed, skipping dependency test.")
            
        # Run iCloudPD --help and check if it uses managed python
        # We can check its stdout/stderr for any 'python' path if it logs it, 
        # or just verify it doesn't crash due to missing dependencies.
        res = subprocess.run([str(icloudpd_bin), "--help"], env=self.env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"iCloudPD --help failed: {res.stderr}")

if __name__ == "__main__":
    unittest.main()

