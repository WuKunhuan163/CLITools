EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestPwd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.gcs_bin = cls.project_root / "bin" / "GDS" / "GDS"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_gcs(self, args, timeout=15):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_pwd_returns_path(self):
        """pwd should return a path string (default ~)."""
        res = self._run_gcs(["pwd"])
        output = self._strip_ansi(res.stdout).strip()
        self.assertEqual(res.returncode, 0, f"pwd failed: {res.stderr}")
        self.assertTrue(len(output) > 0, "pwd should produce output")
        self.assertTrue(output.startswith("~") or output.startswith("/"),
                        f"pwd output should be a path, got: {output}")

    def test_02_pwd_no_gui(self):
        """pwd must not open a GUI (should complete quickly)."""
        res = self._run_gcs(["pwd"])
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
