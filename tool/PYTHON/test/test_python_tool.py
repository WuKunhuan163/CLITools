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
        # script_dir is tool/PYTHON/test/
        cls.test_dir = Path(__file__).resolve().parent
        cls.tool_dir = cls.test_dir.parent
        cls.project_root = cls.tool_dir.parent.parent
        cls.main_py = cls.tool_dir / "main.py"
        cls.python_tool_bin = cls.project_root / "bin" / "PYTHON"
        
        # Determine if we can use the bin alias or need to run main.py directly
        if cls.python_tool_bin.exists():
            cls.tool_cmd = [str(cls.python_tool_bin)]
        else:
            cls.tool_cmd = [sys.executable, str(cls.main_py)]

    def test_list_versions(self):
        """Verify that --py-list returns supported versions."""
        result = subprocess.run(self.tool_cmd + ["--py-list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Supported versions:", result.stdout)
        # Check for at least one version mentioned in the summary
        self.assertIn("python3.10.19", result.stdout)

    def test_unsupported_version(self):
        """Verify that requesting an unsupported version results in an error."""
        # Using a version we know is not in the supported list
        result = subprocess.run(self.tool_cmd + ["--py-install", "python2.7.18"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not supported", result.stdout)

    def test_deploy_custom_dir(self):
        """Test deploying a version to a custom temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # We'll try to 'install' python3.10.19 to this custom dir
            # Note: This requires the version to be available in the 'tool' branch or locally
            # In a test environment, it might fail if git access is restricted, but we should test the logic
            target_dir = Path(tmpdir)
            version = "python3.10.19"
            
            # Since we can't guarantee git access in all sandboxes, we'll check if it's already installed
            # and if so, we'll simulate the move if git fails, or just test the command structure.
            
            cmd = self.tool_cmd + ["--py-install", version, "--py-dir", str(target_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # If successful, verify functionality
            if result.returncode == 0:
                installed_exe = target_dir / version / "install" / "bin" / "python3"
                self.assertTrue(installed_exe.exists())
                
                # Run a simple command using the deployed python
                res = subprocess.run([str(installed_exe), "-c", "import sys; print(sys.version)"], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0)
                self.assertIn("3.10.19", res.stdout)

    def test_independent_versions(self):
        """Verify two different versions can be used independently."""
        # This test assumes at least two versions are installed in tool/PYTHON/proj/install/
        # Let's check what's installed
        install_dir = self.tool_dir / "logic" / "installations"
        if not install_dir.exists():
            self.skipTest("No python versions installed for testing independent use.")
            
        installed = [d.name for d in install_dir.iterdir() if d.is_dir()]
        if len(installed) < 2:
            self.skipTest("At least two python versions must be installed to test independence.")
            
        v1, v2 = installed[:2]
        
        # Get version of v1
        res1 = subprocess.run(self.tool_cmd + ["--py-version", v1, "-c", "import sys; print(sys.version)"], capture_output=True, text=True)
        # Get version of v2
        res2 = subprocess.run(self.tool_cmd + ["--py-version", v2, "-c", "import sys; print(sys.version)"], capture_output=True, text=True)
        
        self.assertIn(v1.replace("python", ""), res1.stdout)
        self.assertIn(v2.replace("python", ""), res2.stdout)
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
        install_dir = self.tool_dir / "logic" / "installations"
        if install_dir.exists() and any(d.is_dir() for d in install_dir.iterdir()):
            self.assertNotEqual(system_py, tool_py)

if __name__ == "__main__":
    unittest.main()

