import unittest
import subprocess
import os
import sys
import shutil
from pathlib import Path

class TestPythonManage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the command name directly as it should be in the PATH
        cls.python_tool = "PYTHON"
        
        # Access tool configuration via its logic module
        # Determine project root to add to sys.path if not there
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(cls.project_root) not in sys.path:
            sys.path.insert(0, str(cls.project_root))
            
        from tool.PYTHON.logic.config import DATA_DIR, ensure_dirs
        cls.data_dir = DATA_DIR
        ensure_dirs()
        
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_test"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_list(self):
        """Test listing supported versions."""
        # Force refresh by removing audit cache if possible, or just use the tool's list
        # Currently --py-list doesn't have a --force, but --py-update does
        result = subprocess.run([self.python_tool, "--py-list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_install_custom_dir(self):
        """Test installing to a custom directory and verifying version."""
        custom_dir = self.tmp_dir / "custom_install"
        if custom_dir.exists():
            shutil.rmtree(custom_dir)
            
        version = "3.11.14" 
        
        # Run install
        cmd = [self.python_tool, "--py-install", version, "--py-dir", str(custom_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # Try migration first
            subprocess.run([self.python_tool, "--py-update", "--version", version], capture_output=True)
            result = subprocess.run(cmd, capture_output=True, text=True)
            
        self.assertEqual(result.returncode, 0)
        
        # Verify success without assuming full path structure if possible, 
        # but custom dir test naturally needs to check the dir.
        python_binaries = list(custom_dir.glob("**/bin/python3")) + list(custom_dir.glob("**/python.exe"))
        self.assertTrue(len(python_binaries) > 0, "No python binary found in custom installation")
        
        python_exe = python_binaries[0]
        ver_result = subprocess.run([str(python_exe), "--version"], capture_output=True, text=True)
        self.assertIn(version, ver_result.stdout)

    def test_invalid_version(self):
        """Test installing an unsupported version."""
        result = subprocess.run([str(self.python_tool), "--py-install", "python3.9.9"], capture_output=True, text=True)
        # Check for existence of output regardless of language, or common keywords
        self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0)

if __name__ == "__main__":
    unittest.main()

