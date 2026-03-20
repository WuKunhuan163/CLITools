EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestShellManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path("/Applications/AITerminalTools")
        cls.gcs_bin = cls.project_root / "bin" / "GCS" / "GCS"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_gcs(self, args, timeout=15):
        cmd = [sys.executable, str(self.gcs_bin), "--no-warning"] + args
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_01_shell_list(self):
        """--shell list should show at least one shell."""
        res = self._run_gcs(["--shell", "list"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0, f"shell list failed: {res.stderr}")
        self.assertIn("Logical Shells", output)

    def test_02_shell_create_and_switch(self):
        """--shell create should create a new shell, --shell switch should switch to it."""
        res = self._run_gcs(["--shell", "create", "test_unit_shell"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0, f"shell create failed: {res.stderr}")
        self.assertIn("Created and switched to shell", output)

        res2 = self._run_gcs(["--shell", "list"])
        output2 = self._strip_ansi(res2.stdout)
        self.assertIn("test_unit_shell", output2)

    def test_03_shell_info(self):
        """--shell info should display shell details."""
        res = self._run_gcs(["--shell", "info"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0, f"shell info failed: {res.stderr}")
        self.assertIn("Shell Info", output)

    def test_04_shell_switch_invalid(self):
        """--shell switch with invalid ID should show error."""
        res = self._run_gcs(["--shell", "switch", "nonexistent_id_999"])
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertIn("not found", output.lower())

    def test_05_shell_type_show(self):
        """--shell type with no arg should show current shell type."""
        res = self._run_gcs(["--shell", "type"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0, f"shell type failed: {res.stderr}")
        self.assertIn("shell type", output.lower())

    def test_06_shell_type_switch(self):
        """--shell type zsh should switch shell type."""
        res = self._run_gcs(["--shell", "type", "zsh"])
        output = self._strip_ansi(res.stdout)
        self.assertEqual(res.returncode, 0)
        self.assertIn("zsh", output.lower())
        # Switch back
        self._run_gcs(["--shell", "type", "bash"])

    def test_07_shell_type_invalid(self):
        """--shell type with unsupported shell should show error."""
        res = self._run_gcs(["--shell", "type", "powershell"])
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertIn("unknown", output.lower())


if __name__ == "__main__":
    unittest.main()
