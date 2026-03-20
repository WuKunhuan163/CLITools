import unittest
import subprocess
import sys
from pathlib import Path

EXPECTED_TIMEOUT = 30

class TestBasic(unittest.TestCase):
    def test_no_args(self):
        """Test that the tool handles no arguments gracefully."""
        project_root = Path(__file__).resolve().parent.parent.parent
        bin_path = project_root / "bin" / "TODO"
        if not bin_path.exists():
            bin_path = project_root / "tool" / "TODO" / "main.py"

        cmd = [sys.executable, str(bin_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        # Should exit 0 (help) or 1 (error) but not crash
        self.assertIn(res.returncode, [0, 1],
            f"Unexpected exit code {res.returncode}: {res.stderr}")

if __name__ == "__main__":
    unittest.main()
