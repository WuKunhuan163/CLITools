import unittest
import subprocess
from pathlib import Path

class TestUserInputTimeout(unittest.TestCase):
    def test_timeout_retry(self):
        """Test USERINPUT retry logic on timeout."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        userinput_bin = project_root / "bin" / "USERINPUT"
        if not userinput_bin.exists():
            self.skipTest("USERINPUT bin not found")
        
        # Determine language to check correct strings
        lang = os.environ.get("TOOL_LANGUAGE", "en").lower()
        if lang == "zh":
            attempt_pattern = "尝试 {index} 失败"
            failed_pattern = "捕获用户输入失败"
        else:
            attempt_pattern = "Attempt {index} failed"
            failed_pattern = "Failed to capture user input"

        cmd = [str(userinput_bin), "--timeout", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        self.assertIn(attempt_pattern.format(index=1), result.stderr)
        self.assertIn(attempt_pattern.format(index=2), result.stderr)
        self.assertIn(failed_pattern, result.stderr)
        self.assertNotEqual(result.returncode, 0)
