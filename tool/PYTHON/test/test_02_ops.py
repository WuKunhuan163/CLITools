import unittest
import subprocess
import os
from pathlib import Path

import unittest
import subprocess
import sys
import os
from pathlib import Path

class TestPythonOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the command name directly
        cls.python_tool = "PYTHON"
        
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        if str(cls.project_root) not in sys.path:
            sys.path.insert(0, str(cls.project_root))
            
        from tool.PYTHON.logic.config import INSTALL_DIR
        cls.install_dir = INSTALL_DIR
        
        # Find an installed version
        cls.version = None
        if cls.install_dir.exists():
            installed = sorted([d.name for d in cls.install_dir.iterdir() if d.is_dir()], reverse=True)
            if installed:
                cls.version = installed[0]
        
        if not cls.version:
            # Try to install one
            v = "3.11.14"
            subprocess.run([cls.python_tool, "--py-install", v], capture_output=True)
            cls.version = v
        
        print(f"DEBUG: Using version '{cls.version}' for ops tests.")

    def test_python_c(self):
        """Test python -c execution."""
        code = "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}')"
        result = subprocess.run([self.python_tool, "--py-version", self.version, "-c", code], capture_output=True, text=True)
        # Should be Python 3.X
        self.assertIn("Python 3.", result.stdout)

    def test_python_executable_path(self):
        """Verify that the tool uses its own standalone executable, not the system one."""
        code = "import sys; print(sys.executable)"
        result = subprocess.run([self.python_tool, "--py-version", self.version, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        # Instead of hardcoding, we can check if sys.executable is NOT the system one
        system_py = sys.executable
        tool_py = result.stdout.strip()
        self.assertNotEqual(tool_py, system_py)
        
        # It should also NOT be /usr/bin/python3 or /usr/local/bin/python3 usually
        self.assertNotIn("/usr/bin/", tool_py)
        self.assertNotIn("/usr/local/bin/", tool_py)

    def test_pip_install(self):
        """Test pip install in the standalone environment."""
        result = subprocess.run([self.python_tool, "--py-version", self.version, "-m", "pip", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("pip", result.stdout)

    def test_venv_creation(self):
        """Test venv creation."""
        venv_path = self.project_root / "data" / "test" / "tmp" / "test_venv"
        if venv_path.exists():
            import shutil
            shutil.rmtree(venv_path)
            
        result = subprocess.run([self.python_tool, "--py-version", self.version, "-m", "venv", str(venv_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        # Check for bin/python or Scripts/python.exe
        if sys.platform == "win32":
            self.assertTrue((venv_path / "Scripts" / "python.exe").exists())
        else:
            self.assertTrue((venv_path / "bin" / "python").exists())

if __name__ == "__main__":
    unittest.main()

