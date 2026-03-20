import unittest
import subprocess
import os
import json
from pathlib import Path

class TestUserInputConfig(unittest.TestCase):
    def test_config_command(self):
        """Test USERINPUT config command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bin_path = project_root / "bin" / "USERINPUT" / "USERINPUT"
        
        # Set focus interval
        interval = 45
        env = os.environ.copy()
        env["TOOL_LANGUAGE"] = "en" # Force English for output check
        res = subprocess.run([str(bin_path), "--config", "--focus-interval", str(interval)], 
                            capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)
        # The output now contains the values in a multiple-config message
        self.assertIn(str(interval), res.stdout)
        
        # Verify config file - use logical path
        config_path = project_root / "tool" / "USERINPUT" / "logic" / "config.json"
        self.assertTrue(config_path.exists())
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.assertEqual(config.get("focus_interval"), interval)

if __name__ == '__main__':
    unittest.main()

