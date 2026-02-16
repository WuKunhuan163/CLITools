EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
import os
import shutil
import re
from pathlib import Path

class TestPythonInstall(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.python_bin = self.project_root / "bin" / "PYTHON"
        self.install_dir = self.project_root / "tool" / "PYTHON" / "data" / "install"
        
        # Ensure cache is populated
        subprocess.run([str(self.python_bin), "--py-list"], capture_output=True)
        
        # Dynamically find a version that is available but NOT installed
        res = subprocess.run([str(self.python_bin), "--py-list"], capture_output=True, text=True)
        installed = []
        available = []
        for line in res.stdout.splitlines():
            # Clean ANSI
            line = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', line).strip()
            if not line or "Supported versions" in line or "Full result" in line: continue
            v = line.split()[0]
            if "(installed)" in line:
                installed.append(v)
            else:
                available.append(v)
        
        if not available:
            # Try to find a migrated but not installed version
            if not available:
                raise unittest.SkipTest("No available uninstalled versions found for testing.")
            
        # Pick the latest available uninstalled version
        self.target_vtag = available[-1]
        self.test_version = self.target_vtag.split("-")[0]
        
        # Cleanup if exists
        v_path = self.install_dir / self.target_vtag
        if v_path.exists():
            shutil.rmtree(v_path)

    def test_install_from_github(self):
        """Verify installation from GitHub for un-migrated versions."""
        # Ensure cache is populated
        subprocess.run([str(self.python_bin), "--py-list"], capture_output=True)
        
        # Note: This requires network access
        res = subprocess.run([str(self.python_bin), "--py-install", self.test_version], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        
        # Verify directory structure
        v_dir = self.install_dir / self.target_vtag
        self.assertTrue(v_dir.exists())
        self.assertTrue((v_dir / "install").exists())
        self.assertTrue((v_dir / "install" / "bin").exists())
        
        # Verify it can run
        res = subprocess.run([str(self.python_bin), "--py-version", self.target_vtag, "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn(self.test_version, res.stdout)

if __name__ == "__main__":
    unittest.main()

