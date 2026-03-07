import unittest
import subprocess
import os

class TestUserInputTimeout(unittest.TestCase):
    def test_timeout_retry(self):
        """Test USERINPUT retry logic on timeout."""
        # Determine language to check correct strings
        lang = os.environ.get("TOOL_LANGUAGE", "en").lower()
        if lang == "zh":
            # The tool now uses colored labels, but we check for text parts
            # "Failed: Attempt {index}"
            attempt_pattern = "Failed" 
            failed_pattern = "捕获用户输入失败"
        else:
            attempt_pattern = "Failed"
            failed_pattern = "Failed to capture user input"

        cmd = ["USERINPUT", "--timeout", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # We check for presence of patterns in stderr or stdout
        output = result.stdout + result.stderr
        self.assertIn(attempt_pattern, output)
        self.assertIn(failed_pattern, output)
        self.assertNotEqual(result.returncode, 0)
