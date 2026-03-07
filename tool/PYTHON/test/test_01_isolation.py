EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
import os
import shutil
from pathlib import Path

class TestPythonIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON" / "PYTHON"
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_isolation"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_isolation(self):
        """Test that two versions can be installed and used independently."""
        # 1. Find two supported versions dynamically
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        versions = []
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                parts = line.split(":", 1)[1].split(",")
                versions = [p.strip() for p in parts if p.strip()]
                break
        
        if len(versions) < 2:
            self.skipTest("Not enough supported versions to test isolation.")
            
        v1 = versions[0]
        v2 = versions[1]
        dir1 = self.tmp_dir / "dir1"
        dir2 = self.tmp_dir / "dir2"
        
        for d in [dir1, dir2]:
            if d.exists(): shutil.rmtree(d)
        
        # Install both
        subprocess.run([str(self.python_tool), "--py-install", v1, "--py-dir", str(dir1)], check=True)
        subprocess.run([str(self.python_tool), "--py-install", v2, "--py-dir", str(dir2)], check=True)
        
        # Use them
        if sys.platform == "win32":
            exe1 = dir1 / v1 / "install" / "python.exe"
            exe2 = dir2 / v2 / "install" / "python.exe"
        else:
            exe1 = dir1 / v1 / "install" / "bin" / "python3"
            exe2 = dir2 / v2 / "install" / "bin" / "python3"
        
        res1 = subprocess.run([str(exe1), "--version"], capture_output=True, text=True)
        res2 = subprocess.run([str(exe2), "--version"], capture_output=True, text=True)
        
        # Verify they are actually different versions or at least from different locations
        self.assertEqual(res1.returncode, 0)
        self.assertEqual(res2.returncode, 0)
        self.assertNotEqual(str(exe1), str(exe2))

if __name__ == "__main__":
    unittest.main()

