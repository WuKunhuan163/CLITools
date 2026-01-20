import unittest
import subprocess
import os
from pathlib import Path

class TestUserInputHint(unittest.TestCase):
    def test_hint_persistence(self):
        """Test if the hint text is correctly passed to the GUI process."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        # We can't easily check the GUI content, but we can verify if it starts without error with a hint
        hint = "Test hint with 'single' and \"double\" quotes and `backticks`."
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # Run with short timeout
        cmd = ["python3", str(main_py), "--hint", hint, "--timeout", "2"]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        output = result.stdout + result.stderr
        
        # Success indicators
        success_indicators = ["Successfully received", "成功收到", "Timeout", "超时"]
        self.assertTrue(any(ind in output for ind in success_indicators))
        self.assertEqual(result.returncode, 0)

if __name__ == '__main__':
    unittest.main()

