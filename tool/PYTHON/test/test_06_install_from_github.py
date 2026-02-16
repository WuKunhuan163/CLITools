EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
import os
import shutil
from pathlib import Path

class TestPythonInstall(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.python_bin = self.project_root / "bin" / "PYTHON"
        self.install_dir = self.project_root / "tool" / "PYTHON" / "data" / "install"
        # Pick a version that is NOT currently installed and NOT in resource
        # (Assuming 3.12.12 is available on GitHub but not migrated yet)
        self.test_version = "3.12.12"
        self.target_vtag = f"{self.test_version}-macos-arm64"
        
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

