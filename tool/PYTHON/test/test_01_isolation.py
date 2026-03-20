EXPECTED_CPU_LIMIT = 70.0
import re
import sys
import unittest
import subprocess
from pathlib import Path


class TestPythonIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.python_tool = cls.project_root / "bin" / "PYTHON" / "PYTHON"
        cls.install_dir = cls.project_root / "tool" / "PYTHON" / "data" / "install"

    def test_isolation(self):
        """Test that two installed versions can be used independently."""
        if not self.install_dir.exists():
            self.skipTest("No install directory found.")

        installed = sorted([
            d.name for d in self.install_dir.iterdir()
            if d.is_dir() and (d / "install").exists()
        ])

        if len(installed) < 2:
            self.skipTest("Need at least 2 installed versions for isolation test.")

        v1, v2 = installed[0], installed[1]

        if sys.platform == "win32":
            exe1 = self.install_dir / v1 / "install" / "python.exe"
            exe2 = self.install_dir / v2 / "install" / "python.exe"
        else:
            exe1 = self.install_dir / v1 / "install" / "bin" / "python3"
            exe2 = self.install_dir / v2 / "install" / "bin" / "python3"

        if not exe1.exists():
            self.skipTest(f"Python executable not found for {v1}")
        if not exe2.exists():
            self.skipTest(f"Python executable not found for {v2}")

        res1 = subprocess.run([str(exe1), "--version"], capture_output=True, text=True)
        res2 = subprocess.run([str(exe2), "--version"], capture_output=True, text=True)

        self.assertEqual(res1.returncode, 0, f"{v1} --version failed: {res1.stderr}")
        self.assertEqual(res2.returncode, 0, f"{v2} --version failed: {res2.stderr}")
        self.assertNotEqual(str(exe1), str(exe2))

        ver1 = res1.stdout.strip()
        ver2 = res2.stdout.strip()
        self.assertIn("Python", ver1)
        self.assertIn("Python", ver2)
        self.assertNotEqual(ver1, ver2, "Both versions report the same Python version")


if __name__ == "__main__":
    unittest.main()
