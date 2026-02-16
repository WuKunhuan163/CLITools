import unittest
import subprocess
import sys
from pathlib import Path

class TestHelp(unittest.TestCase):
    def test_help(self):
        """Test that the tool supports --help and returns success."""
        # Find the tool's main script or bin shortcut
        curr = Path(__file__).resolve().parent
        while curr != curr.parent:
            if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
                project_root = curr
                break
            curr = curr.parent
        else:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            
        bin_path = project_root / "bin" / "GCS"
        if not bin_path.exists():
            bin_path = project_root / "tool" / "GOOGLE.GCS" / "main.py"
            
        cmd = [sys.executable, str(bin_path), "--help"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Help command failed with code {res.returncode}: {res.stderr}")
        self.assertIn("usage:", res.stdout.lower() or res.stderr.lower())

if __name__ == "__main__":
    unittest.main()
