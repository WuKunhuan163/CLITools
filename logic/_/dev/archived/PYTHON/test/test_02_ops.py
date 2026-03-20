EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
from pathlib import Path

class TestPythonOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON" / "PYTHON"

    def test_python_c(self):
        """Test python -c execution."""
        # 1. Find a supported version
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        version = None
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                version = line.split(":", 1)[1].split(",")[0].strip()
                break
        if not version: self.skipTest("No supported versions found.")
        
        # 2. Install if not already there
        subprocess.run([str(self.python_tool), "--py-install", version], capture_output=True)
        
        code = "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"
        result = subprocess.run([str(self.python_tool), "--py-version", version, "-c", code], capture_output=True, text=True)
        self.assertIn(f"Python {version.split('python')[1][:4]}", result.stdout)

    def test_python_executable_path(self):
        """Verify that the tool uses the standalone executable, not the system one."""
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        version = None
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                version = line.split(":", 1)[1].split(",")[0].strip()
                break
        if not version: self.skipTest("No supported versions found.")
        
        code = "import sys; print(sys.executable)"
        result = subprocess.run([str(self.python_tool), "--py-version", version, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        # The output should contain our installations directory
        self.assertIn("tool/PYTHON/data/install", result.stdout)

    def test_pip_install(self):
        """Test pip availability in the standalone environment."""
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        version = None
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                version = line.split(":", 1)[1].split(",")[0].strip()
                break
        if not version: self.skipTest("No supported versions found.")
        
        result = subprocess.run([str(self.python_tool), "--py-version", version, "-m", "pip", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("pip", result.stdout)

    def test_venv_creation(self):
        """Test venv creation."""
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        version = None
        for line in result.stdout.splitlines():
            if "Supported versions:" in line:
                version = line.split(":", 1)[1].split(",")[0].strip()
                break
        if not version: self.skipTest("No supported versions found.")
        
        venv_path = self.project_root / "data" / "_" / "test" / "tmp" / "test_venv"
        if venv_path.exists():
            import shutil
            shutil.rmtree(venv_path)
            
        result = subprocess.run([str(self.python_tool), "--py-version", version, "-m", "venv", str(venv_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        if sys.platform == "win32":
            self.assertTrue((venv_path / "Scripts" / "python.exe").exists())
        else:
            self.assertTrue((venv_path / "bin" / "python").exists())

if __name__ == "__main__":
    unittest.main()

