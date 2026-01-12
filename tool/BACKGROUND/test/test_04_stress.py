import unittest
import subprocess
import time
import os
from pathlib import Path

class TestBackgroundStress(unittest.TestCase):
    def test_stress_load(self):
        """Start many tasks and verify they are all listed."""
        project_root = Path(__file__).parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        
        # Cleanup first
        subprocess.run([str(bg_bin), "--cleanup"], capture_output=True)
        
        # Use 20 tasks for faster testing
        count = 20
        print(f"Starting {count} tasks...")
        for i in range(count):
            subprocess.run([str(bg_bin), f"sleep 1 # task {i}"], check=True, capture_output=True)
            
        # List all
        res = subprocess.run([str(bg_bin), "--list"], capture_output=True, text=True)
        
        # The list output contains lines starting with 'PID:'
        data_lines = [l for l in res.stdout.splitlines() if l.strip().startswith('PID:')]
        # Header also starts with 'PID:', so subtract 1
        found_count = len(data_lines) - 1
        self.assertGreaterEqual(found_count, count, f"Expected at least {count} processes in list, found {found_count}. Output: {res.stdout}")
        
if __name__ == '__main__':
    unittest.main()
