import os
import sys
import json
import time
import subprocess
import re
import hashlib
from pathlib import Path
from datetime import datetime

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        self.tool_dir = self.project_root / "tool" / tool_name
        self.cache_file = self.tool_dir / "test" / ".tests_cache.json"
        
        # Try to import shared utils
        sys.path.append(str(self.project_root))
        try:
            from proj.language_utils import get_translation
            from proj.config import get_color
            self._ = lambda k, d, **kwargs: get_translation(str(self.project_root / "proj"), k, d).format(**kwargs)
            self.colors = {
                "GREEN": get_color("GREEN", "\033[32m"),
                "BOLD": get_color("BOLD", "\033[1m"),
                "RED": get_color("RED", "\033[31m"),
                "BLUE": get_color("BLUE", "\033[34m"),
                "YELLOW": get_color("YELLOW", "\033[33m"),
                "RESET": get_color("RESET", "\033[0m")
            }
        except ImportError:
            self._ = lambda k, d, **kwargs: d.format(**kwargs)
            self.colors = {k: "" for k in ["GREEN", "BOLD", "RED", "BLUE", "YELLOW", "RESET"]}

    def list_tests(self):
        tests = self._get_test_files()
        if not tests:
            print(self._("test_no_tests", "No tests found for {tool}", tool=self.tool_name))
            return

        print(f"\n{self.colors['BOLD']}{self.tool_name} {self._('test_list_header', 'Available Tests:')}{self.colors['RESET']}")
        for i, test in enumerate(tests):
            print(f"  [{i}] {test.name}")

    def run_tests(self, start_id=None, end_id=None, max_concurrent=3, timeout=60):
        all_tests = self._get_test_files()
        if not all_tests:
            print(self._("test_no_tests", "No tests found for {tool}", tool=self.tool_name))
            return

        if start_id is not None or end_id is not None:
            start = start_id if start_id is not None else 0
            end = end_id if end_id is not None else len(all_tests) - 1
            selected_tests = all_tests[start:end+1]
        else:
            selected_tests = all_tests

        if not selected_tests:
            print(self._("test_no_selected", "No tests selected in the specified range."))
            return

        print(f"\n{self._('test_running', 'Preparing to run {count} tests for {tool} tool...', count=len(selected_tests), tool=self.tool_name)}")
        
        # Parallel execution logic
        self._run_parallel_tests(selected_tests, max_concurrent, timeout)
        
        # Cleanup resources
        self._cleanup_resources()

    def _get_test_files(self):
        test_dir = self.tool_dir / "test"
        if not test_dir.exists():
            return []

        # Use cache for consistent ordering
        files = sorted([f for f in test_dir.glob("test_*.py")])
        
        # If no cache or files changed, update cache
        file_names = [f.name for f in files]
        if not self.cache_file.exists():
            self._save_cache(file_names)
        else:
            try:
                with open(self.cache_file, 'r') as f:
                    cached_names = json.load(f)
                if cached_names != file_names:
                    self._save_cache(file_names)
            except Exception:
                self._save_cache(file_names)
        
        return files

    def _save_cache(self, file_names):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(file_names, f, indent=2)
        except Exception:
            pass

    def _get_python_exec(self):
        # Check if the tool has a specific python environment
        tool_json = self.tool_dir / "tool.json"
        if tool_json.exists():
            try:
                with open(tool_json, 'r') as f:
                    data = json.load(f)
                if "PYTHON" in data.get("dependencies", []):
                    # Use the standalone python
                    sys.path.append(str(self.project_root / "tool" / "PYTHON"))
                    from proj.utils import get_python_exec
                    return get_python_exec()
            except Exception:
                pass
        return sys.executable

    def _save_result(self, test_name, status, full_output, python_info=None):
        result_dir = self.project_root / "data" / "test" / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(full_output.encode()).hexdigest()[:8]
        filename = f"{timestamp}_{self.tool_name}_{test_name}_{content_hash}.txt"
        filepath = result_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test: {test_name}\n")
                f.write(f"Tool: {self.tool_name}\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Status: {status}\n")
                if python_info:
                    f.write(f"Python: {python_info}\n")
                f.write("-" * 40 + "\n")
                f.write(full_output)
            
            self._cleanup_old_reports(result_dir)
            return str(filepath)
        except Exception:
            return None

    def _cleanup_old_reports(self, result_dir):
        # Default limit is 1024
        limit = 1024
        config_path = self.project_root / "data" / "global_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    limit = json.load(f).get("test_max_reports", 1024)
            except Exception: pass
            
        reports = sorted(list(result_dir.glob("*.txt")), key=os.path.getmtime)
        if len(reports) > limit:
            for i in range(len(reports) - limit):
                try:
                    os.remove(reports[i])
                except Exception: pass

    def _get_status_label(self, status):
        if status == "Success":
            return f"{self.colors['BOLD']}{self.colors['GREEN']}{self._('test_status_success', 'Success')}{self.colors['RESET']}"
        elif status == "Failed":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('test_status_failed', 'Failed')}{self.colors['RESET']}"
        elif status == "Timeout":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('test_status_timeout', 'Timeout')}{self.colors['RESET']}"
        return f"{self.colors['BOLD']}{self._('test_status_unknown', 'Unknown')}{self.colors['RESET']}"

    def _run_single_test_logic(self, test_file, timeout=60):
        """Internal logic to run a single test and return result."""
        start_time = time.time()
        python_exec = self._get_python_exec()
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"

        try:
            # Use Popen to get PID
            proc = subprocess.Popen([python_exec, str(test_file)], 
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            pid = proc.pid
            
            # Since we want to show PID in sequential mode, we don't print here, 
            # but the caller can access pid if needed.
            
            stdout, stderr = proc.communicate(timeout=timeout)
            duration = time.time() - start_time
            if proc.returncode == 0:
                return "Success", duration, None, None, python_exec, pid
            else:
                report_path = self._save_result(test_file.name, "Failed", stdout + stderr, python_info=python_exec)
                last_line = ""
                for line in stderr.splitlines():
                    if line.strip():
                        last_line = line.strip()
                return "Failed", duration, f"(code {proc.returncode}) Reason: {last_line}", report_path, python_exec, pid
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self._save_result(test_file.name, "Timeout", f"Test timed out after {timeout}s", python_info=python_exec)
            return "Timeout", duration, None, None, python_exec, None
        except Exception as e:
            duration = time.time() - start_time
            return "Error", duration, str(e), None, python_exec, None

    def _run_parallel_tests(self, test_files, max_concurrent, timeout=60):
        """Run multiple tests with status updates. Supports sequential if needed."""
        background_bin = self.project_root / "bin" / "BACKGROUND"
        is_background_test = self.tool_name == "BACKGROUND"
        
        if not background_bin.exists() or is_background_test:
            if is_background_test and max_concurrent > 1:
                print(self._("test_background_sequential", "Testing BACKGROUND tool: Parallel execution disabled to avoid self-cleanup issues."))
            elif not background_bin.exists():
                print("BACKGROUND tool not found. Falling back to sequential execution.")
            sys.stdout.flush()
            
            total_tests = len(test_files)
            for i, test_file in enumerate(test_files):
                # Print starting without PID first, then update it if possible
                # In sequential mode, we can get PID from Popen inside _run_single_test_logic
                # But to show it *while* running, we'd need to change the logic.
                # For sequential, let's just run it and show PID in finished message or similar.
                
                # Actually, let's just print it.
                print(self._("test_starting_sequential", "[{index}/{total}] Starting {file}...", index=i, total=total_tests, file=test_file.name), end="", flush=True)
                
                status_raw, duration, error_msg, report_path, python_exec, pid = self._run_single_test_logic(test_file, timeout=timeout)
                
                # Clear "Starting" and print finished
                print("\r" + " " * 80 + "\r", end="")
                status_label = self._get_status_label(status_raw)
                pid_str = f" (PID: {pid})" if pid else ""
                if error_msg:
                    print(self._("test_finished_with_error", "[{index}/{total}] {status}: {file}{pid} {error} (Duration: {duration:.2f}s)", 
                                 index=i+1, total=total_tests, status=status_label, file=test_file.name, pid=pid_str, error=error_msg, duration=duration))
                else:
                    print(self._("test_finished", "[{index}/{total}] {status}: {file}{pid} (Duration: {duration:.2f}s)", 
                                 index=i+1, total=total_tests, status=status_label, file=test_file.name, pid=pid_str, duration=duration))
                
                if report_path:
                    print(self._("test_full_report", "  Full report: {path}", path=report_path))
                sys.stdout.flush()
            
            print(self._("test_all_completed", "\nAll tests completed."))
            return

        active_jobs = []
        remaining_files = list(test_files)
        total_tests = len(test_files)
        started_count = 0
        finished_count = 0
        python_exec = self._get_python_exec()
        
        print(self._("test_parallel_enabled", "Parallel execution enabled (max {max} concurrent jobs, timeout {timeout}s)", max=max_concurrent, timeout=timeout))
        sys.stdout.flush()

        while remaining_files or active_jobs:
            while len(active_jobs) < max_concurrent and remaining_files:
                test_file = remaining_files.pop(0)
                
                started_count += 1
                start_time = time.time()
                python_path = f"{self.project_root}:{self.tool_dir}"
                cmd = f"export PYTHONPATH=\"{python_path}:$PYTHONPATH\" && {python_exec} {test_file}"
                
                try:
                    proc = subprocess.run([str(background_bin), cmd], capture_output=True, text=True)
                    output = proc.stdout
                    match = re.search(r"PID:?\s*(\d+)", output)
                    if match:
                        pid = match.group(1)
                        print(self._("test_started", "[{index}/{total}] Starting {file} (PID: {pid})", 
                                     index=finished_count, total=total_tests, file=test_file.name, pid=pid))
                        
                        active_jobs.append({
                            "pid": pid, 
                            "file": test_file, 
                            "index": started_count,
                            "start_time": start_time,
                            "python_exec": python_exec
                        })
                    else:
                        print(self._("test_started", "[{index}/{total}] Starting {file} (PID: {pid})", 
                                     index=finished_count, total=total_tests, file=test_file.name, pid="???"))
                        # If failed to start in background, run it here
                        status_raw, duration, error_msg, report_path, py_exec, pid = self._run_single_test_logic(test_file, timeout=timeout)
                        finished_count += 1
                        self._print_finished(finished_count, total_tests, test_file.name, status_raw, duration, error_msg, report_path, pid)
                except Exception:
                    print(self._("test_started", "[{index}/{total}] Starting {file} (PID: {pid})", 
                                 index=finished_count, total=total_tests, file=test_file.name, pid="ERR"))
                    status_raw, duration, error_msg, report_path, py_exec, pid = self._run_single_test_logic(test_file, timeout=timeout)
                    finished_count += 1
                    self._print_finished(finished_count, total_tests, test_file.name, status_raw, duration, error_msg, report_path, pid)

            finished_jobs = []
            for job in active_jobs:
                duration = time.time() - job["start_time"]
                
                if duration > timeout:
                    subprocess.run([str(background_bin), "--kill", job["pid"]], capture_output=True)
                    self._save_result(job["file"].name, "Timeout", f"Test timed out after {timeout}s", python_info=job["python_exec"])
                    job["status_raw"] = "Timeout"
                    job["duration"] = duration
                    finished_jobs.append(job)
                    continue

                try:
                    res = subprocess.run([str(background_bin), "--status", job["pid"], "--json"], 
                                       capture_output=True, text=True)
                    if res.returncode == 0:
                        data = json.loads(res.stdout)
                        if data.get("success") and not data["status"].get("is_running"):
                            ret_code = data["status"].get("return_code")
                            if ret_code == 0:
                                job["status_raw"] = "Success"
                            else:
                                job["status_raw"] = "Failed"
                                res_full = subprocess.run([str(background_bin), "--result", job["pid"]], capture_output=True, text=True)
                                report_path = self._save_result(job["file"].name, f"Failed (code {ret_code})", res_full.stdout, python_info=job["python_exec"])
                                last_line = ""
                                for line in res_full.stdout.splitlines():
                                    if line.strip():
                                        last_line = line.strip()
                                job["error_msg"] = f"(code {ret_code}) Reason: {last_line}"
                                job["report_path"] = report_path
                            
                            job["duration"] = duration
                            finished_jobs.append(job)
                except Exception:
                    pass

            for job in finished_jobs:
                active_jobs.remove(job)
                finished_count += 1
                self._print_finished(finished_count, total_tests, job["file"].name, 
                                    job.get("status_raw", "Unknown"), job.get("duration", 0), 
                                    job.get("error_msg"), job.get("report_path"), job["pid"])

            if active_jobs or remaining_files:
                time.sleep(0.5)

        print(self._("test_all_completed", "\nAll tests completed."))

    def _print_finished(self, index, total, file_name, status, duration, error_msg, report_path, pid=None):
        status_label = self._get_status_label(status)
        pid_str = f" (PID: {pid})" if pid else ""
        if error_msg:
            print(self._("test_finished_with_error", "[{index}/{total}] {status}: {file}{pid} {error} (Duration: {duration:.2f}s)", 
                         index=index, total=total, status=status_label, file=file_name, pid=pid_str, error=error_msg, duration=duration))
        else:
            print(self._("test_finished", "[{index}/{total}] {status}: {file}{pid} (Duration: {duration:.2f}s)", 
                         index=index, total=total, status=status_label, file=file_name, pid=pid_str, duration=duration))
        
        if report_path:
            print(self._("test_full_report", "  Full report: {path}", path=report_path))
        sys.stdout.flush()

    def _cleanup_resources(self):
        """Cleanup leftover processes and GUI windows."""
        try:
            import psutil
        except ImportError:
            return

        # 1. Stop USERINPUT instances
        userinput_stop = self.project_root / "bin" / "USERINPUT"
        if userinput_stop.exists():
            subprocess.run([str(userinput_stop), "stop"], capture_output=True)

        # 2. Cleanup BACKGROUND records
        background_cleanup = self.project_root / "bin" / "BACKGROUND"
        if background_cleanup.exists():
            subprocess.run([str(background_cleanup), "--cleanup"], capture_output=True)
            
        # 3. Final process sweep for leftover python tests
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(self.tool_name in part for part in cmdline) and any("test_" in part for part in cmdline):
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
