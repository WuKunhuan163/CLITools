import unittest
import subprocess
import time
import os
import signal
import psutil
from pathlib import Path

class TestUserInputKill(unittest.TestCase):
    def test_kill_and_retry(self):
        """Test USERINPUT retry logic when the subprocess is killed."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        userinput_bin = project_root / "bin" / "USERINPUT"
        if not userinput_bin.exists():
            self.skipTest("USERINPUT bin not found")
            
        # Start USERINPUT
        proc = subprocess.Popen([str(userinput_bin), "--timeout", "30"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Wait for window to appear
            time.sleep(5)
            parent = psutil.Process(proc.pid)
            
            # Find the actual Tkinter process (usually a child of the wrapper or main.py)
            children = parent.children(recursive=True)
            target_child = None
            for child in children:
                try:
                    # Look for python process running with -c (the injected tkinter script)
                    cmdline = " ".join(child.cmdline())
                    if "-c" in cmdline and "import tkinter" in cmdline:
                        target_child = child
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            
            if not target_child and children:
                target_child = children[-1]
                
            if target_child:
                child_pid = target_child.pid
                # Kill the child gracefully first
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                
                # Wait for retry mechanism to spawn new process
                time.sleep(8)
                new_children = parent.children(recursive=True)
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
