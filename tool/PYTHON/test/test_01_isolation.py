import unittest
import subprocess
import os
import sys
import shutil
from pathlib import Path

class TestPythonIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the command name directly
        cls.python_tool = "PYTHON"
        
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(cls.project_root) not in sys.path:
            sys.path.insert(0, str(cls.project_root))
            
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_isolation"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_isolation(self):
        """Test that two versions can be installed and used independently."""
        # Use different versions if possible, or same in different dirs
        v1_base = "3.11.14"
        v2_base = "3.11.14" # Testing isolation in different dirs
        
        dir1 = self.tmp_dir / "dir1"
        dir2 = self.tmp_dir / "dir2"
        
        for d in [dir1, dir2]:
            if d.exists(): shutil.rmtree(d)
        
        # Install both
        for v, d in [(v1_base, dir1), (v2_base, dir2)]:
            cmd = [self.python_tool, "--py-install", v, "--py-dir", str(d)]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode != 0:
                # Try migration
                subprocess.run([self.python_tool, "--py-update", "--version", v], capture_output=True)
                subprocess.run(cmd, check=True)
        
        # Find binaries without assuming full path structure
        exes = []
        for d in [dir1, dir2]:
            found = list(d.glob("**/bin/python3")) + list(d.glob("**/python.exe"))
            self.assertTrue(len(found) > 0, f"Binary not found in {d}")
            exes.append(found[0])
        
        res1 = subprocess.run([str(exes[0]), "--version"], capture_output=True, text=True)
        res2 = subprocess.run([str(exes[1]), "--version"], capture_output=True, text=True)
        
        self.assertIn(v1_base, res1.stdout)
        self.assertIn(v2_base, res2.stdout)
        # Even if same version, they should be different physical files
        self.assertNotEqual(str(exes[0]), str(exes[1]))

if __name__ == "__main__":
    unittest.main()

