EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestShellInteractive(unittest.TestCase):
    """Test GCS --shell interactive mode entry and exit."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent.parent
        cls.gcs_bin = cls.project_root / "bin" / "GCS" / "GCS"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def test_01_shell_entry_and_exit(self):
        """--shell with 'exit' via stdin should start and stop cleanly."""
        proc = subprocess.Popen(
            [sys.executable, str(self.gcs_bin), "--no-warning", "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="exit\n", timeout=10)
        output = self._strip_ansi(stdout)
        self.assertIn("GCS Interactive Shell", output)
        self.assertIn("Exiting", output)
        self.assertEqual(proc.returncode, 0)

    def test_02_shell_help_command(self):
        """Typing 'help' in shell should show available commands."""
        proc = subprocess.Popen(
            [sys.executable, str(self.gcs_bin), "--no-warning", "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="help\nexit\n", timeout=10)
        output = self._strip_ansi(stdout)
        self.assertIn("GCS Shell Commands", output)
        self.assertIn("ls", output)
        self.assertIn("cd", output)
        self.assertIn("pwd", output)
        self.assertIn("exit", output)

    def test_03_shell_pwd_command(self):
        """Typing 'pwd' in shell should invoke GCS pwd and output a path."""
        proc = subprocess.Popen(
            [sys.executable, str(self.gcs_bin), "--no-warning", "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="pwd\nexit\n", timeout=15)
        output = self._strip_ansi(stdout)
        self.assertIn("GCS Interactive Shell", output)
        # pwd output may appear inline with the prompt (e.g., "GCS:~$ ~")
        self.assertIn("~", output, f"Expected '~' in pwd output, got:\n{output}")

    def test_04_shell_eof_exit(self):
        """Shell should exit cleanly on EOF (empty stdin)."""
        proc = subprocess.Popen(
            [sys.executable, str(self.gcs_bin), "--no-warning", "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="", timeout=10)
        output = self._strip_ansi(stdout)
        self.assertIn("Exiting", output)
        self.assertEqual(proc.returncode, 0)

    def test_05_shell_empty_input(self):
        """Empty lines in shell should be ignored (no error)."""
        proc = subprocess.Popen(
            [sys.executable, str(self.gcs_bin), "--no-warning", "--shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="\n\n\nexit\n", timeout=10)
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
