import unittest
import subprocess
import os
from pathlib import Path

class TestPythonOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON"

    def test_python_c(self):
        """Test python -c execution."""
        code = "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"
        result = subprocess.run([str(self.python_tool), "--py-version", "python3.10.19", "-c", code], capture_output=True, text=True)
        self.assertIn("Python 3.10", result.stdout)

    def test_python_executable_path(self):
        """Verify that the tool uses the standalone executable, not the system one."""
        version = "python3.10.19"
        code = "import sys; print(sys.executable)"
        result = subprocess.run([str(self.python_tool), "--py-version", version, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        # The output should contain our installations directory
        self.assertIn("tool/PYTHON/data/install/3.10.19", result.stdout)

    def test_pip_install(self):
        """Test pip install in the standalone environment."""
        # We'll try to install a very small package like 'requests' or 'six'
        # But to avoid network issues in tests, let's just check if pip is available
        result = subprocess.run([str(self.python_tool), "--py-version", "python3.10.19", "-m", "pip", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("pip", result.stdout)

    def test_venv_creation(self):
        """Test venv creation."""
        venv_path = self.project_root / "data" / "test" / "tmp" / "test_venv"
        if venv_path.exists():
            import shutil
            shutil.rmtree(venv_path)
            
        result = subprocess.run([str(self.python_tool), "--py-version", "python3.10.19", "-m", "venv", str(venv_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue((venv_path / "bin" / "python").exists())

if __name__ == "__main__":
    unittest.main()

