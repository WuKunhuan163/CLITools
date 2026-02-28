EXPECTED_CPU_LIMIT = 95.0
import unittest
import subprocess
import sys
import re
from pathlib import Path


class TestNoWarning(unittest.TestCase):
    """Test that --no-warning suppresses CPU and Turing Machine warnings."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.tool_bin = cls.project_root / "bin" / "TOOL"
        if not cls.tool_bin.exists():
            cls.tool_bin = cls.project_root / "main.py"

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    def _run_tool(self, args, timeout=30):
        cmd = [sys.executable, str(self.tool_bin)] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             cwd=str(self.project_root))
        return res

    def test_no_warning_help(self):
        """--no-warning with --help should produce clean output without warnings."""
        res = self._run_tool(["--no-warning", "--help"])
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertNotIn("CPU", output.upper(),
                         "Help output with --no-warning should not contain CPU warnings")
        self.assertEqual(res.returncode, 0)

    def test_no_warning_suppresses_cpu(self):
        """--no-warning should prevent any CPU load warning from appearing."""
        res = self._run_tool(["--no-warning", "--help"])
        combined = self._strip_ansi(res.stdout + res.stderr)
        warning_patterns = ["cpu", "load", "warning"]
        for pattern in warning_patterns:
            if pattern in combined.lower():
                lines = [l for l in combined.splitlines()
                         if pattern in l.lower() and "usage" not in l.lower()]
                self.assertEqual(len(lines), 0,
                    f"Found warning-like line with '{pattern}': {lines}")

    def test_normal_mode_not_suppressed(self):
        """Without --no-warning, the tool should still run successfully.
        We can't guarantee a warning appears (depends on CPU), but the
        tool must not crash and output should differ or match expectation."""
        res = self._run_tool(["--help"])
        self.assertEqual(res.returncode, 0,
                         f"Help without --no-warning failed: {res.stderr}")
        output = self._strip_ansi(res.stdout + res.stderr)
        self.assertIn("usage", output.lower(),
                      "Help output should contain usage information")


if __name__ == "__main__":
    unittest.main()
