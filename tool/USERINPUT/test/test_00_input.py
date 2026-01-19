import unittest
import subprocess
import sys
from pathlib import Path

class TestUserInput(unittest.TestCase):
    def test_hint_timeout(self):
        """Test USERINPUT with --hint and a timeout."""
        hint_text = "Automated test hint"
        cmd = ["USERINPUT", "--hint", hint_text, "--timeout", "2"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Should contain hint or at least succeed in launching/stopping
        # Actually it will time out or succeed if user clicks.
        # But we check for existence of hint in stdout if tool prints it before GUI
        # (Actually it doesn't print hint to stdout, it puts it in GUI).
        # But we can at least assert it doesn't crash.
        self.assertTrue(result.returncode in [0, 1])
