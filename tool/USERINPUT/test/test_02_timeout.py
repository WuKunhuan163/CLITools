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
        cmd = [str(userinput_bin), "--timeout", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn("Attempt 1/3 failed", result.stderr)
        self.assertIn("Attempt 2/3 failed", result.stderr)
        self.assertIn("Failed to capture user input", result.stderr)
        self.assertNotEqual(result.returncode, 0)
