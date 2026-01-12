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
            if children:
                child_pid = children[0].pid
                os.kill(child_pid, signal.SIGTERM)
                time.sleep(3)
                new_children = parent.children(recursive=True)
                self.assertTrue(len(new_children) > 0, "New subprocess was not spawned after kill")
        finally:
            proc.terminate()
            try: proc.wait(timeout=2)
            except: proc.kill()
