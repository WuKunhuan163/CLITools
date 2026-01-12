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
        proc = subprocess.Popen([str(userinput_bin), "--timeout", "10"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            time.sleep(3)
            parent = psutil.Process(proc.pid)
            children = parent.children(recursive=True)
            if len(children) >= 2:
                # One is main.py, the other is tkinter_script
                # Let's find the one that is NOT the direct child if possible, or check cmdline
                target_child = None
                for child in children:
                    try:
                        if "-c" in " ".join(child.cmdline()):
                            target_child = child
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied): continue
                
                if not target_child:
                    # Fallback to the one with more depth or just the last one
                    target_child = children[-1]
                
                child_pid = target_child.pid
                os.kill(child_pid, signal.SIGKILL)
                # Wait longer for retry to spawn new process
                time.sleep(6)
                new_children = parent.children(recursive=True)
                if not new_children:
                    print(f"Parent PID: {parent.pid}, Status: {parent.status()}")
                self.assertTrue(len(new_children) > 0, "New subprocess was not spawned after kill")
        finally:
            proc.terminate()
            try: proc.wait(timeout=2)
            except: proc.kill()
