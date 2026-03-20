import unittest
import subprocess
import time
import os
import signal
from pathlib import Path

class TestUserInputKill(unittest.TestCase):
    def test_kill_and_retry(self):
        """Test USERINPUT retry logic when the subprocess is killed."""
        try:
            import psutil
        except ImportError:
            self.skipTest("psutil module not found, skipping kill test")

        # Use command directly
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        tool_cmd = str(project_root / "bin" / "USERINPUT" / "USERINPUT")
        
        # Start USERINPUT
        proc = subprocess.Popen([tool_cmd, "--timeout", "30"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        gui_pid = None
        try:
            # Wait for window to appear and capture its PID from stdout
            print("DEBUG: Waiting for GUI PID from stdout...")
            start_wait = time.time()
            while time.time() - start_wait < 10:
                line = proc.stdout.readline()
                if not line: break
                print(f"DEBUG: USERINPUT line: {line.strip()}")
                if "(PID: " in line:
                    import re
                    match = re.search(r"\(PID: (\d+)\)", line)
                    if match:
                        gui_pid = int(match.group(1))
                        print(f"DEBUG: Found GUI PID: {gui_pid}")
                        break
            
            if gui_pid:
                print(f"DEBUG: Killing GUI process PID {gui_pid}")
                try:
                    os.kill(gui_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                
                # Wait for retry mechanism to spawn new process
                print("DEBUG: Waiting for retry...")
                new_gui_pid = None
                start_retry = time.time()
                while time.time() - start_retry < 15:
                    line = proc.stdout.readline()
                    if not line: break
                    print(f"DEBUG: USERINPUT retry line: {line.strip()}")
                    if "(PID: " in line:
                        match = re.search(r"\(PID: (\d+)\)", line)
                        if match:
                            new_gui_pid = int(match.group(1))
                            if new_gui_pid != gui_pid:
                                print(f"DEBUG: Found NEW GUI PID: {new_gui_pid}")
                                break
                
                self.assertIsNotNone(new_gui_pid, "New GUI process was not spawned after kill")
                self.assertNotEqual(new_gui_pid, gui_pid, "New GUI process has the same PID")
            else:
                self.fail("Could not capture GUI PID from stdout")
        finally:
            # Full cleanup
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except: pass
                proc.kill()
            except: pass
            proc.wait()

if __name__ == '__main__':
    unittest.main()
