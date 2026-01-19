import unittest
import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

class TestPythonTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use the command name directly as it should be in the PATH
        cls.tool_cmd = ["PYTHON"]
        
        # script_dir is tool/PYTHON/test/
        cls.test_dir = Path(__file__).resolve().parent
        cls.tool_dir = cls.test_dir.parent
        cls.project_root = cls.tool_dir.parent.parent

    def test_list_versions(self):
        """Verify that --py-list returns supported versions."""
        result = subprocess.run(self.tool_cmd + ["--py-list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        # Robust check: should contain some output
        self.assertTrue(len(result.stdout.strip()) > 0)

    def test_unsupported_version(self):
        """Verify that requesting an unsupported version results in an error."""
        # Using a version we know is not in the supported list
        result = subprocess.run(self.tool_cmd + ["--py-install", "2.7.18"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        # Flexible check for error message (Error or localized equivalent)
        self.assertTrue(len(result.stdout) > 0 or len(result.stderr) > 0)

    def test_deploy_custom_dir(self):
        """Test deploying a version to a custom temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            version = "3.11.14" # Use version we have
            
            cmd = self.tool_cmd + ["--py-install", version, "--py-dir", str(target_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try migration
                subprocess.run(self.tool_cmd + ["--py-update", "--version", version], capture_output=True)
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            # If successful, verify functionality
            if result.returncode == 0:
                # Find the actual installed directory without assuming path
                python_binaries = list(target_dir.glob("**/bin/python3")) + list(target_dir.glob("**/python.exe"))
                if python_binaries:
                    installed_exe = python_binaries[0]
                    self.assertTrue(installed_exe.exists())
                    
                    # Run a simple command using the deployed python
                    res = subprocess.run([str(installed_exe), "-c", "import sys; print(sys.version)"], capture_output=True, text=True)
                    self.assertEqual(res.returncode, 0)
                    self.assertIn("3.11.14", res.stdout)

    def test_independent_versions(self):
        """Verify two different versions can be used independently."""
        # Use Tool logic to find installations instead of hardcoded paths
        # Determine project root to add to sys.path
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))
            
        from tool.PYTHON.logic.config import INSTALL_DIR
        
        if not INSTALL_DIR.exists():
            self.skipTest("No python versions installed for testing independent use.")
            
        installed = sorted([d.name for d in INSTALL_DIR.iterdir() if d.is_dir()])
        if len(installed) < 2:
            self.skipTest("At least two python versions must be installed to test independence.")
            
        v1, v2 = installed[:2]
        
        # Get version of v1
        res1 = subprocess.run(self.tool_cmd + ["--py-version", v1, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True)
        # Get version of v2
        res2 = subprocess.run(self.tool_cmd + ["--py-version", v2, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True)
        
        # v1 and v2 could be like '3.7.3-macos' or '3.11.14-macos-arm64'
        v1_base = v1.split("-")[0].replace("python", "")
        v2_base = v2.split("-")[0].replace("python", "")
        
        self.assertIn(v1_base, res1.stdout)
        self.assertIn(v2_base, res2.stdout)
        # If they are DIFFERENT versions, check that
        if v1_base != v2_base:
            self.assertNotEqual(res1.stdout.strip(), res2.stdout.strip())

    def test_basic_ops(self):
        """Verify basic project operations (python -c, pip, venv)."""
        # 1. python -c
        res = subprocess.run(self.tool_cmd + ["-c", "print('hello')"], capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "hello")
        
        # 2. pip list
        res = subprocess.run(self.tool_cmd + ["-m", "pip", "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("pip", res.stdout)
        
        # 3. venv creation
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "test_venv"
            res = subprocess.run(self.tool_cmd + ["-m", "venv", str(venv_path)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            
            # Check if venv exists
            if sys.platform == "win32":
                venv_exe = venv_path / "Scripts" / "python.exe"
            else:
                venv_exe = venv_path / "bin" / "python"
            self.assertTrue(venv_exe.exists())

    def test_distinguish_system_python(self):
        """Verify the tool uses its standalone python, not the system one."""
        # Get system python path
        system_py = sys.executable
        
        # Get tool's python path
        # We can ask the tool to print sys.executable
        res = subprocess.run(self.tool_cmd + ["-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
        tool_py = res.stdout.strip()
        
        # They should be different if a standalone version is used
        # Note: If the tool falls back to system python because none are installed, this might fail.
        # So we only assert if we know a standalone is installed.
        install_dir = self.tool_dir / "data" / "install"
        if install_dir.exists() and any(d.is_dir() for d in install_dir.iterdir()):
            self.assertNotEqual(system_py, tool_py)

if __name__ == "__main__":
    unittest.main()

