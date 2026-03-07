EXPECTED_CPU_LIMIT = 40.0
import unittest
import subprocess
import time
import os
from pathlib import Path

class TestFileDialogHistoryNav(unittest.TestCase):
    def test_history_navigation(self):
        """Test back/forward history navigation in FILEDIALOG."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # Test script to be injected into the GUI
        on_show_script = r'''
import os
from pathlib import Path

def run_test():
    try:
        # 1. Identify subfolders
        all_items = win.tree.get_children()
        subfolders = [item for item in all_items if "Folder" in win.tree.item(item, "values")[2]]

        if subfolders:
            target = subfolders[0]
            target_path = Path(target)
            original_path = win.current_dir
            
            # 2. Go into subfolder
            print(f"JUMPING_TO: {target_path}")
            win.jump_to(target_path)
            
            if str(win.current_dir) != str(target_path):
                print(f"FAILED_STEP: Could not jump to {target_path}. Current: {win.current_dir}")
                win.finalize("error", "Jump failed")
                return

            # 3. Go back
            print("GOING_BACK")
            win.go_back()
            if str(win.current_dir) != str(original_path):
                print(f"FAILED_STEP: Back failed. Current: {win.current_dir}, Original: {original_path}")
                win.finalize("error", "Back failed")
                return

            # 4. Go forward
            print("GOING_FORWARD")
            win.go_forward()
            if str(win.current_dir) != str(target_path):
                print(f"FAILED_STEP: Forward failed. Current: {win.current_dir}, Target: {target_path}")
                win.finalize("error", "Forward failed")
                return

            print("HISTORY_NAV_OK")
            win.finalize("success", "History test passed")
        else:
            print(f"SKIPPED: No subfolders found in {win.current_dir}. Items: {len(all_items)}")
            win.finalize("success", "Skipped")
    except Exception as e:
        print(f"TEST_ERROR: {e}")
        win.finalize("error", str(e))

# Delay test execution to allow UI to settle
win.root.after(1000, run_test)
'''
        env["FILEDIALOG_ON_SHOW_SCRIPT"] = on_show_script
        
        test_id = f"test_fd_history_{int(time.time())}_{os.getpid()}"
        proc = subprocess.Popen(["python3", str(main_py), "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            stdout, stderr = proc.communicate(timeout=30)
            all_out = stdout + stderr
            
            self.assertIn("History test passed", all_out)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

