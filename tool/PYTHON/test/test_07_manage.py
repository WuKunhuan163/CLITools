EXPECTED_CPU_LIMIT = 70.0
import unittest
import subprocess
import sys
import shutil
from pathlib import Path

class TestPythonManage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON" / "PYTHON"
        cls.tmp_dir = cls.project_root / "data" / "test" / "tmp" / "python_test"
        cls.tmp_dir.mkdir(parents=True, exist_ok=True)

    def test_list(self):
        """Test listing supported versions."""
        import re
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        plain = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        self.assertTrue(
            "Supported versions" in plain or "支持的版本" in plain,
            f"Expected version list header in output"
        )
        
    def test_install_custom_dir(self):
        """Test installing a supported version to a custom directory."""
        import re
        result = subprocess.run([str(self.python_tool), "--py-list"], capture_output=True, text=True)
        plain = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        versions = []
        for line in plain.splitlines():
            line = line.strip()
            if re.match(r'^\d+\.\d+\.\d+-\w', line):
                v = line.split()[0]
                versions.append(v)

        if not versions:
            self.skipTest("No supported versions found to test install.")

        # Prefer a known-good version for the current platform
        preferred = ["3.11.14-macos-arm64", "3.12.9-macos-arm64", "3.13.2-macos-arm64"]
        version = None
        for p in preferred:
            if p in versions:
                version = p
                break
        if version is None:
            version = versions[-1]

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

