import unittest
import subprocess
import time
import re
import os
from pathlib import Path

class TestBackgroundCleanup(unittest.TestCase):
    def test_cleanup_execution(self):
        """Verify cleanup stops record tracking but not necessarily the OS process (or verify record is gone)."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        if not bg_bin.exists(): self.skipTest("BACKGROUND bin not found")

        # Start task
        res = subprocess.run([str(bg_bin), "sleep 5"], capture_output=True, text=True)
        match = re.search(r"PID:?\s*(\d+)", res.stdout)
        pid = int(match.group(1))

        # Cleanup
        subprocess.run([str(bg_bin), "--cleanup"], check=True)

        # Verify status fails
        res = subprocess.run([str(bg_bin), "--status", str(pid), "--json"], capture_output=True, text=True)
        import json
        data = json.loads(res.stdout)
        self.assertFalse(data["success"])

if __name__ == "__main__":
    unittest.main()
