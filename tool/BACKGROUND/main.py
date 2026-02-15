#!/usr/bin/env python3
import sys
import argparse
import subprocess
import os
import json
import time
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

from logic.tool.base import ToolBase
from logic.config import get_color
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
        print(f"{BOLD}{GREEN}Started{RESET} background process with PID: {BOLD}{pid}{RESET}")
        print(f"Log file: {log_path}")
        return pid

    def list_procs(self):
        procs = self._load_processes()
        if not procs:
            print("No background processes found.")
            return

        headers = ["PID", "Status", "Started", "Command"]
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
            print(f"Process {pid} stopped.")
        except psutil.TimeoutExpired:
            p.kill()
            print(f"Process {pid} killed.")
        except Exception as e:
            print(f"Error stopping process {pid}: {e}")

    def wait_proc(self, pid):
        try:
            p = psutil.Process(pid)
            print(f"Waiting for process {pid} to finish...")
            p.wait()
            print(f"Process {pid} completed.")
        except psutil.NoSuchProcess:
            print(f"Process {pid} not found or already finished.")
        except Exception as e:
            print(f"Error waiting for process {pid}: {e}")

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
        print("Cleanup completed.")

def main():
    manager = BackgroundManager()
    
    parser = argparse.ArgumentParser(description="Background Process Manager", add_help=False)
    parser.add_argument("command", choices=["run", "list", "stop", "wait", "cleanup"], help="Command to execute")
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

if __name__ == "__main__":
    main()

