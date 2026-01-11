import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundStress(unittest.TestCase):
    def test_100_parallel(self):
        """Start 100 parallel tasks."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        if not bg_bin.exists(): self.skipTest("BACKGROUND bin not found")

        # Use 100 tasks
        count = 100
        print(f"Starting {count} tasks...")
        start_time = time.time()
        for i in range(count):
            subprocess.run([str(bg_bin), f"sleep 1 # task {i}"], check=True)
        
        duration = time.time() - start_time
        print(f"Started {count} tasks in {duration:.2f}s")

        # Verify list count
        res = subprocess.run([str(bg_bin), "--list", "--json"], capture_output=True, text=True)
        import json
        data = json.loads(res.stdout)
        # It might be MORE than 100 if previous tests left tasks, but at least 100
        self.assertGreaterEqual(data["total_count"], count)

if __name__ == "__main__":
    unittest.main()
