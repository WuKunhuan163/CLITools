import unittest
import subprocess
import time
import os
import json
import sys
import random
import re
from pathlib import Path

class TestMultiWorkerDisplay(unittest.TestCase):
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

    def test_multi_worker_robustness(self):
        """
        Verify MultiLineManager with:
        1. Random width (10-20).
        2. Varying worker names (Short, Long, CJK, Arabic).
        3. Width constraint check (no line > width).
        4. Header and slot persistence checks.
        """
        # 1. Randomize width between 10 and 20
        test_width = random.randint(10, 20)
        self.run_tool(["config", "--terminal-width", str(test_width)])
        
        test_script = self.project_root / "tmp_ui_multi_test.py"
        log_file = self.project_root / "data" / "run" / "ui_frames.log"
        if log_file.exists(): log_file.unlink()

        test_script_content = """
import sys
import time
import json
from pathlib import Path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from logic.turing.display.manager import MultiLineManager
from logic.utils import get_display_width

# Mock terminal state capture
frames = []
def capture_frame():
    # Capture what would be displayed
    slots_data = []
    for s in manager.slots:
        from logic.turing.display.manager import wrap_text, truncate_to_width
        w = manager._get_current_width()
        if not s.is_final:
            display_text = truncate_to_width(s.text, w)
            lines = [display_text]
        else:
            lines = wrap_text(s.text, w)
        
        slots_data.append({
            "id": s.worker_id,
            "lines": lines,
            "h": s.height,
            "final": s.is_final
        })
        
    state = {
        "width": manager._get_current_width(),
        "slots": slots_data
    }
    frames.append(state)

manager = MultiLineManager()

print("--- UI ROBUSTNESS HEADER ---")

# Define workers including Arabic (RTL)
workers = [
    ("SHORT", 0.3),
    ("VERY_LONG_NAME_THAT_EXCEEDS_WIDTH", 0.6),
    ("CJK_中文", 0.4),
    ("ARABIC_العربية", 0.5), # Testing RTL compatibility
]

start_time = time.time()
active_workers = set()

for i in range(15):
    elapsed = time.time() - start_time
    for name, duration in workers:
        if elapsed < duration:
            active_workers.add(name)
            manager.update(name, f"{name}: {int(elapsed/duration*100)}%%", callback=capture_frame)
        elif name in active_workers:
            active_workers.remove(name)
            manager.update(name, f"{name}: DONE!", is_final=True, callback=capture_frame)
    time.sleep(0.1)

with open(%(log_file)r, "w") as f:
    json.dump(frames, f)
""" % {'log_file': str(log_file)}

        with open(test_script, "w") as f:
            f.write(test_script_content)
        
        try:
            res = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True, cwd=str(self.project_root))
            
            # 1. Header persistence
            self.assertIn("--- UI ROBUSTNESS HEADER ---", res.stdout)

            # 2. Width constraint verification
            if log_file.exists():
                with open(log_file, "r") as f:
                    frames = json.load(f)
                
                # We need get_display_width here too
                sys.path.append(str(self.project_root))
                from logic.utils import get_display_width
                
                for frame in frames:
                    w = frame["width"]
                    for slot in frame["slots"]:
                        for line in slot["lines"]:
                            actual_w = get_display_width(line)
                            # Check iv: no line width > specified width
                            self.assertLessEqual(actual_w, w, f"Line too wide: '{line}' ({actual_w} > {w})")
                        
                        # Verify height matches lines
                        self.assertEqual(len(slot["lines"]), slot["h"], f"Height mismatch for {slot['id']}")

            # 3. Final results presence
            self.assertIn("DONE!", res.stdout)
            # Check for Arabic presence in final output (even if wrapped)
            # Match part of the word to be safe against wrapping
            self.assertTrue(re.search(r"العرب|بية", res.stdout))
            
        finally:
            if test_script.exists(): test_script.unlink()
            if log_file.exists(): log_file.unlink()

if __name__ == "__main__":
    unittest.main()
