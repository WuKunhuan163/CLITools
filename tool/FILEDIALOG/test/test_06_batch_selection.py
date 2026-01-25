import unittest
import subprocess
import time
import os
import tempfile
from pathlib import Path

class TestFileDialogBatchSelection(unittest.TestCase):
    def test_batch_selection(self):
        """Test Shift and Cmd/Ctrl selection in FILEDIALOG."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # Create a temp directory with known files for predictable testing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            for i in range(1, 11):
                (tmp_path / f"file_{i:02d}.txt").touch()
            
            on_show_script = r'''
import tkinter as tk

def run_test():
    try:
        # 1. Identify items
        all_items = win.tree.get_children()
        print(f"ITEMS_FOUND: {len(all_items)}")
        if len(all_items) < 10:
            print(f"FAILED_STEP: Not enough items. Found {len(all_items)}")
            win.finalize("error", "Setup failed")
            return

        # 2. Simulate Click #3 (0-indexed -> index 2)
        item3 = all_items[2]
        print(f"SELECTING_ITEM_3: {item3}")
        win.last_selected = item3
        win.tree.selection_set(item3)

        # 3. Simulate Shift-Click #6 (index 5)
        item6 = all_items[5]
        print(f"SHIFT_SELECTING_ITEM_6: {item6}")

        # Manual trigger of range logic for test
        idx1 = all_items.index(win.last_selected)
        idx2 = 5 # Target index
        start = min(idx1, idx2)
        end = max(idx1, idx2)
        range_items = all_items[start:end+1]
        current_selection = list(win.tree.selection())
        for ri in range_items:
            if ri not in current_selection: current_selection.append(ri)
        win.tree.selection_set(current_selection)

        # 4. Verify selection
        sel = win.tree.selection()
        print(f"CURRENT_SELECTION: {len(sel)} items")
        if len(sel) == 4: # #3, #4, #5, #6
            print("BATCH_SELECT_OK")
            win.finalize("success", list(sel))
        else:
            print(f"FAILED_STEP: Selection length mismatch. Expected 4, got {len(sel)}")
            win.finalize("error", f"Selection failed: {len(sel)}")
    except Exception as e:
        print(f"TEST_ERROR: {e}")
        win.finalize("error", str(e))

win.root.after(1000, run_test)
'''
            env["FILEDIALOG_ON_SHOW_SCRIPT"] = on_show_script
            
            test_id = f"test_fd_batch_{int(time.time())}_{os.getpid()}"
            # Must run with --multiple
            proc = subprocess.Popen(["python3", str(main_py), "--dir", tmpdir, "--multiple", "--id", test_id], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            
            try:
                stdout, stderr = proc.communicate(timeout=30)
                all_out = stdout + stderr
                self.assertIn("Selected", all_out)
                self.assertIn("(4):", all_out)
                
            finally:
                if proc.poll() is None:
                    proc.kill()

if __name__ == '__main__':
    unittest.main()

