#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
import subprocess
import json
import psutil
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color
from logic.utils import format_table

class BackgroundManager(ToolBase):
    def __init__(self):
        super().__init__("BACKGROUND")
        self.proc_file = self.get_data_dir() / "processes.json"
        self._ensure_files()

    def _ensure_files(self):
        self.get_data_dir().mkdir(parents=True, exist_ok=True)
        self.get_log_dir().mkdir(parents=True, exist_ok=True)
        if not self.proc_file.exists():
            with open(self.proc_file, 'w') as f:
                json.dump({}, f)

    def _load_processes(self):
        try:
            with open(self.proc_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_processes(self, procs):
        with open(self.proc_file, 'w') as f:
            json.dump(procs, f, indent=2)

    def run_cmd(self, cmd_list):
        cmd_str = " ".join(cmd_list)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_name = f"{timestamp}_{hash(cmd_str) & 0xFFFFFFFF:08x}.log"
        log_path = self.get_log_dir() / log_name
        
        # Start process
        with open(log_path, 'w') as log_file:
            process = subprocess.Popen(
                cmd_list,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True, # detached from parent
                text=True
            )
        
        pid = process.pid
        
        # Save to registry
        procs = self._load_processes()
        procs[str(pid)] = {
            "command": cmd_str,
            "start_time": datetime.now().isoformat(),
            "log": str(log_path),
            "status": "running"
        }
        self._save_processes(procs)
        
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RESET = get_color("RESET")
        started_label = self.get_translation("label_started", "Started")
        msg = self.get_translation("msg_started_background_pid", "Started background process with PID: ")
        print(f"{BOLD}{GREEN}{started_label}{RESET} {msg}{BOLD}{pid}{RESET}")
        log_label = self.get_translation("label_log_file", "Log file: ")
        print(f"{log_label}{log_path}")
        return pid

    def list_procs(self):
        procs = self._load_processes()
        if not procs:
            print(self.get_translation("msg_no_background_processes", "No background processes found."))
            return

        headers = [
            self.get_translation("label_pid", "PID"),
            self.get_translation("label_status", "Status"),
            self.get_translation("label_started_at", "Started"),
            self.get_translation("label_command", "Command")
        ]
        rows = []
        
        updated_procs = {}
        for pid_str, info in procs.items():
            pid = int(pid_str)
            status = "finished"
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    status = p.status()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            info["status"] = status
            updated_procs[pid_str] = info
            
            # Formatting
            start_dt = datetime.fromisoformat(info["start_time"]).strftime("%m-%d %H:%M:%S")
            rows.append([pid_str, status, start_dt, info["command"]])
            
        self._save_processes(updated_procs)
        table_str, _ = format_table(headers, rows)
        print(f"\n{table_str}")

    def stop_proc(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=5)
            print(self.get_translation("msg_process_stopped", "Process {pid} stopped.").format(pid=pid))
        except psutil.TimeoutExpired:
            p.kill()
            print(self.get_translation("msg_process_killed", "Process {pid} killed.").format(pid=pid))
        except Exception as e:
            print(self.get_translation("err_stopping_process", "Error stopping process {pid}: {error}").format(pid=pid, error=e))

    def wait_proc(self, pid):
        try:
            p = psutil.Process(pid)
            print(self.get_translation("msg_waiting_for_process", "Waiting for process {pid} to finish...").format(pid=pid))
            p.wait()
            print(self.get_translation("msg_process_completed", "Process {pid} completed.").format(pid=pid))
        except psutil.NoSuchProcess:
            print(self.get_translation("msg_process_not_found", "Process {pid} not found or already finished.").format(pid=pid))
        except Exception as e:
            print(self.get_translation("err_waiting_for_process", "Error waiting for process {pid}: {error}").format(pid=pid, error=e))

    def cleanup(self):
        procs = self._load_processes()
        for pid_str in procs.keys():
            try:
                self.stop_proc(int(pid_str))
            except: pass
        
        # Clear logs
        import shutil
        if self.get_log_dir().exists():
            shutil.rmtree(self.get_log_dir())
        self.get_log_dir().mkdir(parents=True, exist_ok=True)
        
        self._save_processes({})
        print(self.get_translation("label_cleanup_completed", "Cleanup completed."))

    def run_tests(self):
        """Finds and runs all test_xx_*.py files in the test/ directory."""
        test_dir = self.tool_dir / "test"
        test_files = sorted(list(test_dir.glob("test_*.py")))
        
        if not test_files:
            print("No test files found.")
            return

        BOLD = get_color("BOLD")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        GREEN = get_color("GREEN")
        RED = get_color("RED")

        print(f"{BOLD}{BLUE}Running BACKGROUND tests...{RESET}\n")
        
        all_passed = True
        for test_file in test_files:
            print(f"Executing {BOLD}{test_file.name}{RESET}...", end=" ", flush=True)
            res = subprocess.run([sys.executable, str(test_file)], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"{BOLD}{GREEN}PASSED{RESET}")
            else:
                print(f"{BOLD}{RED}FAILED{RESET}")
                print(f"\n{RED}Error output:{RESET}\n{res.stderr}")
                all_passed = False
        
        if all_passed:
            print(f"\n{BOLD}{GREEN}All tests passed!{RESET}")
        else:
            print(f"\n{BOLD}{RED}Some tests failed.{RESET}")
            sys.exit(1)

def main():
    manager = BackgroundManager()
    
    parser = argparse.ArgumentParser(description="Background Process Manager", add_help=False)
    parser.add_argument("command", choices=["run", "list", "stop", "wait", "cleanup", "test"], help="Command to execute")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the command")
    
    if manager.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if args.command == "run":
        if not args.args:
            print("Usage: BACKGROUND run <command>")
            return
        manager.run_cmd(args.args)
    elif args.command == "list":
        manager.list_procs()
    elif args.command == "stop":
        if not args.args:
            print("Usage: BACKGROUND stop <pid>")
            return
        manager.stop_proc(int(args.args[0]))
    elif args.command == "wait":
        if not args.args:
            print("Usage: BACKGROUND wait <pid>")
            return
        manager.wait_proc(int(args.args[0]))
    elif args.command == "cleanup":
        manager.cleanup()
    elif args.command == "test":
        manager.run_tests()

if __name__ == "__main__":
    main()

