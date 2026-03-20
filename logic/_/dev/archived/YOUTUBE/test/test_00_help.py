#!/usr/bin/env python3
"""Test that --help exits cleanly."""
import sys
import unittest
from pathlib import Path

_r = Path(__file__).resolve().parent.parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

EXPECTED_TIMEOUT = 300
EXPECTED_CPU_LIMIT = 40.0


class TestHelp(unittest.TestCase):
    def test_help_runs(self):
        import subprocess
        main_py = str(Path(__file__).resolve().parent.parent / "main.py")
        result = subprocess.run(
            [sys.executable, main_py, "--help"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("YOUTUBE", result.stdout.upper() + result.stderr.upper())


if __name__ == "__main__":
    unittest.main()
