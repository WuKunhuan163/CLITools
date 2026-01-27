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
        # Check for presence of "Supported versions:" regardless of language
        self.assertIn("Supported versions:", result.stdout)
        
    def test_install_custom_dir(self):
        """Test installing a supported version to a custom directory."""
        # 1. Find a supported version dynamically
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        versions = []
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                # Extract versions after the label
                parts = line.split(":", 1)[1].split(",")
                versions = [p.strip() for p in parts if p.strip()]
                break
        
        if not versions:
            self.skipTest("No supported versions found to test install.")
            
        version = versions[0]
        custom_dir = self.tmp_dir / "custom_install"
        if custom_dir.exists():
            shutil.rmtree(custom_dir)
            
        # Run install
        cmd = [str(self.python_tool), "--py-install", version, "--py-dir", str(custom_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        # Verify success by checking binary
        if sys.platform == "win32":
            python_exe = custom_dir / version / "install" / "python.exe"
        else:
            python_exe = custom_dir / version / "install" / "bin" / "python3"
            
        self.assertTrue(python_exe.exists(), f"Python binary not found at {python_exe}")

    def test_invalid_version(self):
        """Test installing an unsupported version."""
        result = subprocess.run([str(self.python_tool), "--py-install", "python3.9.9"], capture_output=True, text=True)
        # Check for existence of output regardless of language, or common keywords
        self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0)

if __name__ == "__main__":
    unittest.main()

