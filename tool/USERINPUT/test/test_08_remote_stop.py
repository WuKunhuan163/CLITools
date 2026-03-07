import unittest
import subprocess
import time
import os
import json
from pathlib import Path

EXPECTED_CPU_LIMIT = 40.0

class TestUserInputRemoteStop(unittest.TestCase):
    def test_remote_stop(self):
        """Test remote stop command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        test_id = f"test_08_{int(time.time())}"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        import sys
        python_exec = sys.executable
        
        # Use -u for unbuffered output
        proc = subprocess.Popen([python_exec, "-u", str(main_py), "--timeout", "60", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register by checking instance files
            gui_pid = None
            start_wait = time.time()
            while time.time() - start_wait < 40:
                instance_dir = project_root / "data" / "run" / "instances"
                if instance_dir.exists():
                    for f in instance_dir.glob("gui_*.json"):
                        try:
                            with open(f, 'r') as info_file:
                                info = json.load(info_file)
                                if info.get("custom_id") == test_id:
                                    gui_pid = info.get("pid")
                                    if gui_pid: break
                        except: pass
                if gui_pid: break
                time.sleep(1)
            
            if not gui_pid:
                self.fail("Could not find USERINPUT instance file with correct ID.")

            # Send remote stop using ID
            stop_cmd = [python_exec, str(main_py), "stop", "--id", test_id]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            # Wait for exit with generous timeout
            stdout, stderr = proc.communicate(timeout=40)
            
            all_out = stdout + stderr
            stop_indicators = ["Terminated", "已终止"]
            self.assertTrue(any(ind in all_out for ind in stop_indicators), f"Expected stop indicator in output: {all_out}")
            self.assertEqual(proc.returncode, 0)
            
        finally:
            if proc.poll() is None:
                try:
                    import psutil
                    parent = psutil.Process(proc.pid)
                    for child in parent.children(recursive=True):
                        try: child.kill()
                        except: pass
                    proc.kill()
                except:
                    proc.kill()

if __name__ == '__main__':
    unittest.main()
