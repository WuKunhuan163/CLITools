import unittest
import subprocess
import time
import os
import json
from pathlib import Path

class TestUserInputRemoteCancel(unittest.TestCase):
    def test_remote_cancel(self):
        """Test remote cancel command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        test_id = f"test_cancel_{int(time.time())}_{os.getpid()}"
        # Use -u for unbuffered output to ensure we capture PID/Status quickly if needed
        proc = subprocess.Popen(["python3", "-u", str(main_py), "--timeout", "30", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register with a more robust check
            start_wait = time.time()
            registered = False
            while time.time() - start_wait < 20:
                # Check if the instance file exists in data/run/instances/
                instance_dir = project_root / "data" / "run" / "instances"
                if instance_dir.exists():
                    for f in instance_dir.glob("gui_*.json"):
                        try:
                            with open(f, 'r') as info_file:
                                info = json.load(info_file)
                                if info.get("custom_id") == test_id:
                                    registered = True
                                    break
                        except: pass
                if registered: break
                time.sleep(1)
            
            if not registered:
                time.sleep(5) # Final buffer
            
            cancel_cmd = ["python3", str(main_py), "--gui-cancel", "--id", test_id]
            subprocess.run(cancel_cmd, env=env, capture_output=True)
            
            # Wait for exit with a generous timeout
            stdout, stderr = proc.communicate(timeout=30)
            
            all_out = stdout + stderr
            cancel_indicators = ["Cancelled", "已取消", "已终止", "Terminated", "terminated"]
            self.assertTrue(any(ind.lower() in all_out.lower() for ind in cancel_indicators), 
                            f"Expected cancellation indicator in output: {all_out}")
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()
