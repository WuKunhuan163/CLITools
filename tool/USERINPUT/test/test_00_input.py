import unittest
import subprocess
import sys
from pathlib import Path

class TestUserInput(unittest.TestCase):
    def test_hint_timeout(self):
        """Test USERINPUT with --hint and a timeout."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        userinput_bin = project_root / "bin" / "USERINPUT"
        
        if not userinput_bin.exists():
            self.skipTest("USERINPUT bin not found")

        hint_text = "Automated test hint"
        cmd = [str(userinput_bin), "--hint", hint_text, "--timeout", "2"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn(hint_text, result.stdout)
