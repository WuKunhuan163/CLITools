"""Basic help test for ATLASSIAN tool."""
import unittest
import subprocess
import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent


class TestHelp(unittest.TestCase):
    def test_help_runs(self):
        result = subprocess.run(
            [sys.executable, str(_r / "tool" / "ATLASSIAN" / "main.py"), "-h"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Atlassian", result.stdout)


if __name__ == "__main__":
    unittest.main()
