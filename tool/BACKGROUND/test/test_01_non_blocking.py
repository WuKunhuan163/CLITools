EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import time
from pathlib import Path

class TestBackgroundNonBlocking(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.bg_bin = self.project_root / "bin" / "BACKGROUND" / "BACKGROUND"
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_non_blocking(self):
        """Verify BACKGROUND run returns immediately."""
        start_time = time.time()
        # This sleep happens in the background
        subprocess.run([str(self.bg_bin), "run", "sleep", "5"], capture_output=True)
        elapsed = time.time() - start_time
        
        self.assertLess(elapsed, 1.0, "BACKGROUND run should be non-blocking and return quickly")

if __name__ == "__main__":
    unittest.main()


