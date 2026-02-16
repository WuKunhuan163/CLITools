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
        tool_cmd = "USERINPUT"
        
        # Start USERINPUT
        proc = subprocess.Popen([tool_cmd, "--timeout", "30"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Wait for window to appear
            time.sleep(5)
            parent = psutil.Process(proc.pid)
            
            # Find the actual Tkinter process (usually a child of the wrapper or main.py)
            children = parent.children(recursive=True)
            print(f"DEBUG: Initial children: {[c.pid for c in children]}")
            for c in children:
                try: print(f"DEBUG: Child {c.pid} cmdline: {c.cmdline()}")
                except: pass

            target_child = None
            for child in children:
                try:
                    # Look for python process running the USERINPUT_gui_ script
                    cmdline = " ".join(child.cmdline())
                    if "USERINPUT_gui_" in cmdline:
                        target_child = child
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            
            if not target_child and children:
                # Fallback: look for any child that is a python process
                for child in children:
                    try:
                        name = child.name().lower()
                        if "python" in name:
                            target_child = child
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied): continue
                
            if target_child:
                child_pid = target_child.pid
                print(f"DEBUG: Killing target child PID {child_pid}")
                # Kill the child gracefully first
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                
                # Wait for retry mechanism to spawn new process
                # retry loop has 1s sleep
                print("DEBUG: Waiting for retry...")
                for i in range(10):
                    time.sleep(1)
                    new_children = parent.children(recursive=True)
                    print(f"DEBUG: Attempt {i+1}, new children: {[c.pid for c in new_children]}")
                    if len(new_children) > 0:
                        # Check if any new child is a python process
                        for c in new_children:
                            try:
                                if "python" in c.name().lower() and c.pid != child_pid:
                                    target_child = c
                                    break
                            except: continue
                        if target_child.pid != child_pid:
                            break
                
                if len(new_children) == 0:
                    stdout, stderr = proc.communicate(timeout=1)
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                self.assertTrue(len(new_children) > 0, "New subprocess was not spawned after kill")
            else:
                self.fail("Could not find Tkinter child process")
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
