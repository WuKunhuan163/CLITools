import os
import sys
import unittest
import subprocess
import time
from pathlib import Path
import json
import re
import hashlib
from datetime import datetime

# Try to import psutil for resource cleanup
try:
    import psutil
except ImportError:
    psutil = None

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        self.tool_dir = self.project_root / "tool" / tool_name
        self.test_dir = self.tool_dir / "test"
        self.cache_file = self.test_dir / ".tests_cache.json"
        self.results_dir = self.project_root / "data" / "test" / "result"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.shared_proj_dir = self.project_root / "proj"
        
        # Load colors
        try:
            from proj.config import get_color
            self.GREEN = get_color("GREEN", "\033[32m")
            self.RED = get_color("RED", "\033[31m")
            self.BOLD = get_color("BOLD", "\033[1m")
            self.RESET = get_color("RESET", "\033[0m")
        except ImportError:
            self.GREEN = "\033[32m"
            self.RED = "\033[31m"
            self.BOLD = "\033[1m"
            self.RESET = "\033[0m"

    def _(self, key, default, **kwargs):
        try:
            from proj.language_utils import get_translation
            text = get_translation(str(self.shared_proj_dir), key, default)
            return text.format(**kwargs)
        except Exception:
            return default.format(**kwargs)

    def get_test_files(self):
        """Find all test_*.py files and manage the cache."""
        if not self.test_dir.exists():
            return []
        
        current_files = sorted([p.name for p in self.test_dir.glob("test_*.py")])
        
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_files = json.load(f)
                    if cached_files == current_files:
                        return [self.test_dir / f for f in cached_files]
            except Exception:
                pass

        test_files = [self.test_dir / f for f in current_files]
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(current_files, f, indent=2)
        except Exception:
            pass
            
        return test_files

    def list_tests(self):
        """List all available tests for the tool with 0-based indices."""
        test_files = self.get_test_files()
        if not test_files:
            print(f"No tests found for {self.tool_name} in {self.test_dir}")
            sys.stdout.flush()
            return
        
        print(f"Available tests for {self.tool_name} (Indices are 0-based):")
        for i, test_file in enumerate(test_files):
            print(f"  [{i}] {test_file.name}")
        sys.stdout.flush()

    def _save_result(self, test_name, status, content, python_info=None):
        """Save full test result to a file and perform cleanup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        filename = f"{timestamp}_{self.tool_name}_{test_name}_{content_hash}.txt"
        filepath = self.results_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test: {test_name}\n")
                f.write(f"Tool: {self.tool_name}\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Status: {status}\n")
                if python_info:
                    f.write(f"Python: {python_info}\n")
                f.write("-" * 40 + "\n")
                f.write(content)
            
            # Cleanup mechanism
            self._cleanup_reports()
            return filepath
        except Exception as e:
            print(f"Error saving test report: {e}")
            return None

    def _cleanup_reports(self):
        """Limit the number of test reports."""
        max_reports = 1024
        config_path = self.project_root / "data" / "global_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    max_reports = config.get("test_max_reports", 1024)
            except Exception:
                pass
        
        reports = sorted(list(self.results_dir.glob("*.txt")), key=os.path.getctime)
        while len(reports) > max_reports:
            try:
                old_report = reports.pop(0)
                old_report.unlink()
            except Exception:
                break

    def _get_python_exec(self):
        """Get the appropriate python executable for the tool."""
        python_exec = sys.executable
        python_tool_dir = self.project_root / "tool" / "PYTHON"
        python_utils_path = python_tool_dir / "proj" / "utils.py"
        
        depends_on_python = False
        tool_json_path = self.tool_dir / "tool.json"
        if tool_json_path.exists():
            with open(tool_json_path, 'r') as f:
                try:
                    tool_data = json.load(f)
                    if "PYTHON" in tool_data.get("dependencies", []) or self.tool_name == "PYTHON":
                        depends_on_python = True
                except Exception:
                    pass

        if depends_on_python and python_utils_path.exists():
            try:
                import importlib.util
                mod_name = f"python_utils_runner_{self.tool_name}"
                spec = importlib.util.spec_from_file_location(mod_name, str(python_utils_path))
                python_utils_runner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(python_utils_runner)
                standalone_exec = python_utils_runner.get_python_exec()
                if os.path.exists(standalone_exec):
                    python_exec = standalone_exec
            except Exception:
                pass
        return python_exec

    def run_tests(self, start_id=None, end_id=None, max_concurrent=1, timeout=60):
        """Run tests with inclusive range indexing and real-time progress."""
        test_files = self.get_test_files()
        if not test_files:
            print(self._("test_no_tests", "No tests found for {tool}", tool=self.tool_name))
            sys.stdout.flush()
            return

        if start_id is not None and end_id is not None:
            test_files = test_files[start_id : end_id + 1]
        
        if not test_files:
            print(self._("test_no_selected", "No tests selected in the specified range."))
            sys.stdout.flush()
            return

        total_count = len(test_files)
        print(self._("test_running", "Preparing to run {count} tests for {tool}...", count=total_count, tool=self.tool_name))
        sys.stdout.flush()
        
        try:
            self._run_parallel_tests(test_files, max_concurrent, timeout=timeout)
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        """Recycle resources (like GUI windows or leftover processes) after testing."""
        if not psutil:
            return
            
        print(f"\nRecycling resources for {self.tool_name}...")
        sys.stdout.flush()
        
        current_pid = os.getpid()
        count = 0
        
        # 1. Graceful cleanup via tool interfaces if available
        if self.tool_name == "USERINPUT":
            userinput_bin = self.project_root / "bin" / "USERINPUT"
            if userinput_bin.exists():
                subprocess.run([str(userinput_bin), "stop"], capture_output=True)
        elif self.tool_name == "BACKGROUND":
            background_bin = self.project_root / "bin" / "BACKGROUND"
            if background_bin.exists():
                subprocess.run([str(background_bin), "--cleanup"], capture_output=True)

        # 2. General process sweep
        # We look for processes running from our project directory that are not us
        for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue
                
                # Check if process is running from within our project
                proc_cwd = proc.info.get('cwd')
                if proc_cwd and str(self.project_root) in proc_cwd:
                    # Double check it's related to the current tool or general test artifacts
                    cmdline = proc.info.get('cmdline')
                    if cmdline and (self.tool_name in " ".join(cmdline) or "unittest" in " ".join(cmdline)):
                        # Kill children first
                        for child in proc.children(recursive=True):
                            try:
                                child.terminate()
                                child.wait(timeout=1)
                            except:
                                try: child.kill()
                                except: pass
                        
                        proc.terminate()
                        try: proc.wait(timeout=2)
                        except: proc.kill()
                        count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if count > 0:
            print(f"Cleaned up {count} leftover processes.")
        sys.stdout.flush()

    def _run_single_test_logic(self, test_file, timeout=60):
        """Internal logic to run a single test and return result."""
        start_time = time.time()
        python_exec = self._get_python_exec()
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"

        try:
            result = subprocess.run([python_exec, "-m", "unittest", str(test_file)], 
                                   env=env, timeout=timeout, capture_output=True, text=True)
            duration = time.time() - start_time
            if result.returncode == 0:
                return "Success", duration, None, None, python_exec
            else:
                report_path = self._save_result(test_file.name, "Failed", result.stdout + result.stderr, python_info=python_exec)
                last_line = ""
                for line in result.stderr.splitlines():
                    if line.strip():
                        last_line = line.strip()
                return "Failed", duration, f"(code {result.returncode}) Reason: {last_line}", report_path, python_exec
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self._save_result(test_file.name, "Timeout", f"Test timed out after {timeout}s", python_info=python_exec)
            return "Timeout", duration, None, None, python_exec

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
                print(self._("test_starting_sequential", "[{index}/{total}] Starting {file}...", index=i, total=total_tests, file=test_file.name))
                sys.stdout.flush()
                
                status_raw, duration, error_msg, report_path, python_exec = self._run_single_test_logic(test_file, timeout=timeout)
                
                status_label = self._get_status_label(status_raw)
                if error_msg:
                    print(self._("test_finished_with_error", "[{index}/{total}] {status}: {file} {error} (Duration: {duration:.2f}s)", 
                                 index=i+1, total=total_tests, status=status_label, file=test_file.name, error=error_msg, duration=duration))
                else:
                    print(self._("test_finished", "[{index}/{total}] {status}: {file} (Duration: {duration:.2f}s)", 
                                 index=i+1, total=total_tests, status=status_label, file=test_file.name, duration=duration))
                
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
                print(self._("test_started", "[{index}/{total}] Starting {file} (PID: {pid})", 
                             index=finished_count, total=total_tests, file=test_file.name, pid="..."))
                
                started_count += 1
                start_time = time.time()
                python_path = f"{self.project_root}:{self.tool_dir}"
                cmd = f"export PYTHONPATH=\"{python_path}:$PYTHONPATH\" && {python_exec} -m unittest {test_file}"
                
                try:
                    proc = subprocess.run([str(background_bin), cmd], capture_output=True, text=True)
                    output = proc.stdout
                    match = re.search(r"PID:?\s*(\d+)", output)
                    if match:
                        pid = match.group(1)
                        active_jobs.append({
                            "pid": pid, 
                            "file": test_file, 
                            "index": started_count,
                            "start_time": start_time,
                            "python_exec": python_exec
                        })
                    else:
                        status_raw, duration, error_msg, report_path, py_exec = self._run_single_test_logic(test_file, timeout=timeout)
                        finished_count += 1
                        self._print_finished(finished_count, total_tests, test_file.name, status_raw, duration, error_msg, report_path)
                except Exception:
                    status_raw, duration, error_msg, report_path, py_exec = self._run_single_test_logic(test_file, timeout=timeout)
                    finished_count += 1
                    self._print_finished(finished_count, total_tests, test_file.name, status_raw, duration, error_msg, report_path)

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
                    try:
                        os.kill(int(job["pid"]), 0)
                    except OSError:
                        job["status_raw"] = "Unknown"
                        job["duration"] = duration
                        finished_jobs.append(job)
            
            for job in finished_jobs:
                active_jobs.remove(job)
                finished_count += 1
                self._print_finished(finished_count, total_tests, job["file"].name, job["status_raw"], 
                                     job["duration"], job.get("error_msg"), job.get("report_path"))
            
            if remaining_files or active_jobs:
                time.sleep(1)

        print(self._("test_all_completed", "\nAll tests completed."))
        sys.stdout.flush()

    def _get_status_label(self, status_raw):
        if status_raw == "Success":
            label = self._("test_status_success", "SUCCESS")
            return f"{self.BOLD}{self.GREEN}{label.upper()}{self.RESET}"
        elif status_raw == "Failed":
            label = self._("test_status_failed", "FAILED")
            return f"{self.BOLD}{self.RED}{label.upper()}{self.RESET}"
        elif status_raw == "Timeout":
            label = self._("test_status_timeout", "TIMEOUT")
            return f"{self.BOLD}{self.RED}{label.upper()}{self.RESET}"
        else:
            label = self._("test_status_unknown", status_raw)
            return f"{self.BOLD}{self.RED}{label.upper()}{self.RESET}"

    def _print_finished(self, index, total, file_name, status_raw, duration, error_msg, report_path):
        status_label = self._get_status_label(status_raw)
        if error_msg:
            print(self._("test_finished_with_error", "[{index}/{total}] {status}: {file} {error} (Duration: {duration:.2f}s)", 
                         index=index, total=total, status=status_label, file=file_name, error=error_msg, duration=duration))
        else:
            print(self._("test_finished", "[{index}/{total}] {status}: {file} (Duration: {duration:.2f}s)", 
                         index=index, total=total, status=status_label, file=file_name, duration=duration))
        
        if report_path:
            print(self._("test_full_report", "  Full report: {path}", path=report_path))
        sys.stdout.flush()
