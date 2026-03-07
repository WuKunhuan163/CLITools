EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestArgparseBehavior(unittest.TestCase):
    """Test command-line argument parsing and routing."""

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

    def test_01_no_args_shows_help(self):
        """Running GCS with no arguments should show help."""
        res = self._run_gcs([])
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertIn("usage", output.lower())

    def test_02_help_flag(self):
        """GCS --help should show help and exit 0."""
        res = self._run_gcs(["--help"])
        self.assertEqual(res.returncode, 0)
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertIn("usage", output.lower())

    def test_03_help_lists_subcommands(self):
        """Help should list recognized subcommands."""
        res = self._run_gcs(["--help"])
        output = self._strip_ansi(res.stdout)
        for cmd in ["ls", "cd", "pwd", "cat"]:
            self.assertIn(cmd, output, f"Help should mention '{cmd}' subcommand")

    def test_04_help_lists_options(self):
        """Help should list special --options."""
        res = self._run_gcs(["--help"])
        output = self._strip_ansi(res.stdout)
        for opt in ["--setup-tutorial", "--remount", "--shell"]:
            self.assertIn(opt, output, f"Help should mention '{opt}' option")

    def test_05_unrecognized_treated_as_remote(self):
        """Unrecognized commands should be treated as remote commands (not crash)."""
        # Use --no-warning to suppress CPU warning which might cause issues
        # The command won't execute (no GUI), but shouldn't crash argparse
        res = self._run_gcs(["some_random_command", "--no-warning"])
        # Should not crash with argparse error
        self.assertNotIn("unrecognized arguments", self._strip_ansi(res.stderr).lower())


if __name__ == "__main__":
    unittest.main()
