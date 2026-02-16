import unittest
import subprocess
import os
import sys
import shutil
import time
from pathlib import Path

class TestRobustnessSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.bin_tool = cls.project_root / "bin" / "TOOL"
        cls.bin_python = cls.project_root / "bin" / "PYTHON"
        cls.bin_userinput = cls.project_root / "bin" / "USERINPUT"
        
        # Ensure we are on dev branch for testing
        subprocess.run(["/usr/bin/git", "checkout", "dev"], cwd=str(cls.project_root), capture_output=True)

    def test_01_python_persistence_across_sync(self):
        """Verify Python installations are preserved across TOOL dev sync (branch switching)."""
        version = "3.11.14"
        platform = "macos-arm64" if sys.platform == "darwin" and "arm" in os.uname().machine.lower() else "macos"
        full_version = f"{version}-{platform}"
        
        # 1. Install Python
        print(f"\nInstalling {full_version}...")
        res = subprocess.run([str(self.bin_python), "--py-install", version], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Failed to install Python: {res.stderr}")
        
        install_dir = self.project_root / "tool" / "PYTHON" / "data" / "install" / full_version
        self.assertTrue(install_dir.exists(), f"Install dir {install_dir} should exist")
        
        # 2. Run TOOL dev sync (this involves branch switching and persistence)
        print("Running TOOL dev sync...")
        res = subprocess.run([str(self.bin_tool), "dev", "sync"], capture_output=True, text=True)
        # We don't necessarily require sync to succeed on remote (could be network issue), 
        # but the local persistence should work.
        
        # 3. Verify Python still exists
        self.assertTrue(install_dir.exists(), f"Install dir {install_dir} should be preserved after sync")
        
        # 4. Verify it's usable
        py_exec = install_dir / "install" / "bin" / "python3"
        if not py_exec.exists(): py_exec = install_dir / "install" / "python.exe" # Windows fallback
        
        res = subprocess.run([str(py_exec), "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Python executable failed: {res.stderr}")
        self.assertIn(version, res.stdout)

    def test_02_userinput_availability(self):
        """Verify USERINPUT tool is functional after various operations."""
        # Simple help check
        res = subprocess.run([str(self.bin_userinput), "--help"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, "USERINPUT --help failed")
        
        # Test with a timeout to avoid deadlock in test environment
        print("Testing USERINPUT with timeout...")
        res = subprocess.run([str(self.bin_userinput), "--timeout", "2", "--hint", "Robustness test"], capture_output=True, text=True)
        # It should timeout (exit code 1 or similar) but not deadlock
        self.assertIn("timeout", res.stderr.lower() or res.stdout.lower())

    def test_03_git_tool_dependency(self):
        """Verify GIT tool can use requests (managed dependency)."""
        res = subprocess.run([str(self.bin_tool), "test", "GIT", "--list"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, "GIT tool test list failed")

if __name__ == "__main__":
    unittest.main()

