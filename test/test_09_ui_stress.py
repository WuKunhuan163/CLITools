import unittest
import subprocess
import time
import os
import json
import sys
from pathlib import Path

class TestUIStress(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.bin_path = self.project_root / "bin" / "TOOL"
        # Ensure we have a clean config
        self.config_path = self.project_root / "data" / "config.json"
        self.original_config = None
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                self.original_config = json.load(f)

    def tearDown(self):
        # Restore original config
        if self.original_config is not None:
            with open(self.config_path, "w") as f:
                json.dump(self.original_config, f, indent=2)
        elif self.config_path.exists():
            self.config_path.unlink()

    def run_tool(self, args):
        cmd = [str(self.bin_path)] + args
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_root))

    def test_narrow_ui_truncation(self):
        """Test MultiLineManager with a forced narrow width (10 columns)"""
        # 1. No longer setting terminal width globally to avoid parallel test interference
        
        # 2. Run a command that uses MultiLineManager. 
        # Since we don't have a direct CLI for MultiLineManager yet, we can use a small python script
        # that imports it and runs some tasks.
        
        test_script = self.project_root / "tmp_ui_test.py"
        test_script_content = """
import sys
import time
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from logic.turing.display.manager import MultiLineManager

manager = MultiLineManager(width=10)

# Start 4 workers with long names and different status messages
# Terminal width is forced to 10 by config.json
manager.update("w1", "Worker 1: Starting...")
manager.update("w2", "Worker 2: Pending...")
time.sleep(0.2)
manager.update("w1", "Worker 1: Progressing 50%")
manager.update("w3", "Worker 3: Long name that should be truncated")
time.sleep(0.2)
manager.update("w2", "Worker 2: DONE", is_final=True)
manager.update("w4", "Worker 4: This is a very very long final message that should wrap if it were not truncated for active workers but allowed for final ones.")
manager.update("w4", "Worker 4: Final multiline\\nstatus message", is_final=True)
manager.update("w1", "Worker 1: DONE", is_final=True)
manager.update("w3", "Worker 3: DONE", is_final=True)
"""
        with open(test_script, "w") as f:
            f.write(test_script_content)
        
        try:
            res = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True, cwd=str(self.project_root))
            
            # 3. Verify output
            # With width 10, "Worker 1: Starting..." should be truncated to "Worke..." (10 chars)
            # Active workers should be truncated.
            # Final workers' multiline messages should be joined by " | " if they were multi-line input, 
            # but wait, MultiLineManager.update joins lines with " | " at the start.
            
            out = res.stdout
            err = res.stderr
            
            # Check for truncation indicators
            self.assertIn("...", out)
            
            # Check that final multi-line was joined
            self.assertIn(" | ", out)
            
        finally:
            if test_script.exists():
                test_script.unlink()

if __name__ == "__main__":
    unittest.main()

