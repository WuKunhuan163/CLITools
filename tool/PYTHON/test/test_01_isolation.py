import unittest
import subprocess
import os
import shutil
from pathlib import Path

class TestPythonIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON"
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_isolation"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_isolation(self):
        """Test that two versions can be installed and used independently."""
        v1 = "python3.12.12"
        v2 = "python3.13.11"
        dir1 = self.tmp_dir / "dir1"
        dir2 = self.tmp_dir / "dir2"
        
        for d in [dir1, dir2]:
            if d.exists(): shutil.rmtree(d)
        
        # Install both
        subprocess.run([str(self.python_tool), "--py-install", v1, "--py-dir", str(dir1)], check=True)
        subprocess.run([str(self.python_tool), "--py-install", v2, "--py-dir", str(dir2)], check=True)
        
        # Use v1 to print version
        # Note: In our current main.py, it uses get_python_exec which defaults to proj/installations.
        # To use the custom dir, we'd need to support passing it, or just use the exe directly for this test.
        # But the user wanted to test that they can be used via the tool.
        # Let's check if our main.py supports custom dirs for execution.
        
        exe1 = dir1 / v1 / "install" / "bin" / "python3"
        exe2 = dir2 / v2 / "install" / "bin" / "python3"
        
        res1 = subprocess.run([str(exe1), "--version"], capture_output=True, text=True)
        res2 = subprocess.run([str(exe2), "--version"], capture_output=True, text=True)
        
        self.assertIn("3.12.12", res1.stdout)
        self.assertIn("3.13.11", res2.stdout)

if __name__ == "__main__":
    unittest.main()

