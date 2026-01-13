import unittest
import subprocess
import time
import os
import json
from pathlib import Path

class TestUserInputConfig(unittest.TestCase):
    def test_config_command(self):
        """Test USERINPUT config command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        userinput_bin = project_root / "bin" / "USERINPUT"
        if not userinput_bin.exists():
            self.skipTest("USERINPUT bin not found")
            
        # Set focus interval
        interval = 45
        res = subprocess.run([str(userinput_bin), "config", "--focus-interval", str(interval)], 
                            capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn(str(interval), res.stdout)
        
        # Verify config file
        config_path = project_root / "tool" / "USERINPUT" / "proj" / "config.json"
        self.assertTrue(config_path.exists())
        with open(config_path, 'r') as f:
            config = json.load(f)
            self.assertEqual(config.get("focus_interval"), interval)

if __name__ == '__main__':
    unittest.main()

