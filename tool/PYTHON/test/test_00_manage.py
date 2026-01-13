import unittest
import subprocess
import os
import shutil
from pathlib import Path

class TestPythonManage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON"
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_test"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_list(self):
        """Test listing supported versions."""
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Supported versions:", result.stdout)
        self.assertIn("python3.10.19", result.stdout)

    def test_install_custom_dir(self):
        """Test installing to a custom directory and verifying version."""
        version = "python3.11.14"
        custom_dir = self.tmp_dir / "custom_install"
        if custom_dir.exists():
            shutil.rmtree(custom_dir)
            
        # Run install
        cmd = [str(self.python_tool), "--py-install", version, "--py-dir", str(custom_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Successfully installed", result.stdout)
        
        # Verify executable exists and works
        python_exe = custom_dir / version / "install" / "bin" / "python3"
        self.assertTrue(python_exe.exists())
        
        ver_result = subprocess.run([str(python_exe), "--version"], capture_output=True, text=True)
        self.assertIn("3.11.14", ver_result.stdout)

    def test_invalid_version(self):
        """Test installing an unsupported version."""
        result = subprocess.run([str(self.python_tool), "--py-install", "python3.9.9"], capture_output=True, text=True)
        self.assertIn("not supported", result.stdout.lower())

if __name__ == "__main__":
    unittest.main()

