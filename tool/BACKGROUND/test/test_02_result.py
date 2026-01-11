import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundResult(unittest.TestCase):
    def test_result_match(self):
        """Verify result matches standard execution."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        if not bg_bin.exists(): self.skipTest("BACKGROUND bin not found")

        # Execute echo "Hello World"
        cmd = 'echo "Hello World"'
        res = subprocess.run([str(bg_bin), cmd], capture_output=True, text=True)
        match = re.search(r"PID:?\s*(\d+)", res.stdout)
        pid = int(match.group(1))

        # Wait for finish
        time.sleep(2)

        # Get result
        res = subprocess.run([str(bg_bin), "--result", str(pid)], capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "Hello World")

if __name__ == "__main__":
    unittest.main()
