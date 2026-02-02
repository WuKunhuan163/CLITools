import unittest
import subprocess
import time
import os
from pathlib import Path

class TestFileDialogHeaderSort(unittest.TestCase):
    def test_header_sorting(self):
        """Test column sorting in FILEDIALOG."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        on_show_script = r'''
def run_test():
    try:
        # 1. Click Name (should be descending if clicked again)
        print("CLICKING_NAME")
        win.on_header_click("name")
        if win.sort_column != "name" or win.sort_reverse != True:
            print(f"FAILED_STEP: Name toggle failed. {win.sort_column}/{win.sort_reverse}")
            win.finalize("error", "Sort failed")
            return

        # 2. Click Size
        print("CLICKING_SIZE")
        win.on_header_click("size")
        if win.sort_column != "size" or win.sort_reverse != False:
            print(f"FAILED_STEP: Size sort failed. {win.sort_column}/{win.sort_reverse}")
            win.finalize("error", "Sort failed")
            return

        print("HEADER_SORT_OK")
        win.finalize("success", "Sort test passed")
    except Exception as e:
        print(f"TEST_ERROR: {e}")
        win.finalize("error", str(e))

win.root.after(1000, run_test)
'''
        env["FILEDIALOG_ON_SHOW_SCRIPT"] = on_show_script
        
        test_id = f"test_fd_sort_{int(time.time())}_{os.getpid()}"
        proc = subprocess.Popen(["python3", str(main_py), "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            stdout, stderr = proc.communicate(timeout=30)
            all_out = stdout + stderr
            self.assertIn("Sort test passed", all_out)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

