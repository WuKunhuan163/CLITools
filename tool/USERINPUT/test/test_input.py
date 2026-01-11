import unittest
import subprocess
import json
import sys
from pathlib import Path

class TestUserInput(unittest.TestCase):
    def test_hint_timeout(self):
        """Test USERINPUT with --hint and a short timeout."""
        # Project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        userinput_bin = project_root / "bin" / "USERINPUT"
        
        if not userinput_bin.exists():
            self.skipTest("USERINPUT bin not found")

        # Run USERINPUT with hint and 2s timeout
        # Expected behavior: it should capture the hint text as partial input
        hint_text = "Automated test hint"
        cmd = [str(userinput_bin), "--hint", hint_text, "--timeout", "2"]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check output for the captured hint
        # The output should contain the hint text since it was injected into the text box
        self.assertIn(hint_text, result.stdout)

if __name__ == '__main__':
    unittest.main()
