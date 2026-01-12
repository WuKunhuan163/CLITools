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

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        self.tool_dir = self.project_root / "tool" / tool_name
        self.test_dir = self.tool_dir / "test"
        self.cache_file = self.test_dir / ".tests_cache.json"
        self.results_dir = self.project_root / "data" / "test" / "result"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
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

    def get_test_files(self):
        """Find all test_*.py files and manage the cache."""
        if not self.test_dir.exists():
            return []
        
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_files = json.load(f)
                    test_files = [self.test_dir / f for f in cached_files if (self.test_dir / f).exists()]
                    if len(test_files) == len(cached_files):
                        return test_files
            except Exception:
                pass

        test_files = sorted(list(self.test_dir.glob("test_*.py")), key=lambda p: p.name)
        
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump([p.name for p in test_files], f, indent=2)
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

    def _save_result(self, test_name, status, content):
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
                spec = importlib.util.spec_from_file_location("python_utils_runner", str(python_utils_path))
                python_utils_runner = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(python_utils_runner)
                python_exec = python_utils_runner.get_python_exec()
            except Exception:
                pass
        return python_exec

    def run_tests(self, start_id=None, end_id=None, max_concurrent=1, timeout=60):
        """Run tests with inclusive range indexing and real-time progress."""
        test_files = self.get_test_files()
        if not test_files:
            print(f"No tests found for {self.tool_name}")
            sys.stdout.flush()
            return

        if start_id is not None and end_id is not None:
            test_files = test_files[start_id : end_id + 1]
        
        if not test_files:
            print("No tests selected in the specified range.")
            sys.stdout.flush()
            return

        total_count = len(test_files)
        print(f"Running {total_count} tests for {self.tool_name}...")
        sys.stdout.flush()
        
        if total_count == 1 and max_concurrent == 1:
            self._run_single_test(test_files[0], timeout=timeout)
        else:
            self._run_parallel_tests(test_files, max_concurrent, timeout=timeout)

    def _run_single_test(self, test_file, timeout=60):
        """Run a single test file using unittest."""
        print(f"\n--- Running {test_file.name} ---")
        sys.stdout.flush()
        
        start_time = time.time()
        python_exec = self._get_python_exec()
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"

        try:
            result = subprocess.run([python_exec, "-m", "unittest", str(test_file)], 
                                   env=env, timeout=timeout, capture_output=True, text=True)
            duration = time.time() - start_time
            if result.returncode == 0:
                status_str = f"{self.BOLD}{self.GREEN}Success{self.RESET}"
            else:
                status_str = f"{self.BOLD}{self.RED}Failed{self.RESET}"
                report_path = self._save_result(test_file.name, "Failed", result.stdout + result.stderr)
                # Short summary of failure from stderr
                last_line = ""
                for line in result.stderr.splitlines():
                    if line.strip():
                        last_line = line.strip()
                print(f"Reason: {last_line}")
                if report_path:
                    print(f"Full report: {report_path}")
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            status_str = f"{self.BOLD}{self.RED}Timeout{self.RESET}"
            self._save_result(test_file.name, "Timeout", f"Test timed out after {timeout}s")

        print(f"Result: {status_str} (Duration: {duration:.2f}s)")
        sys.stdout.flush()

    def _run_parallel_tests(self, test_files, max_concurrent, timeout=60):
        """Run multiple tests in parallel using BACKGROUND tool with progress updates."""
        background_bin = self.project_root / "bin" / "BACKGROUND"
        # Avoid nesting BACKGROUND if testing BACKGROUND itself, or if bin not found
        if not background_bin.exists() or self.tool_name == "BACKGROUND":
            if self.tool_name == "BACKGROUND":
                print("Testing BACKGROUND tool: Parallel execution disabled to avoid self-cleanup issues.")
            else:
                print("BACKGROUND tool not found. Falling back to sequential execution.")
            sys.stdout.flush()
            for i, test_file in enumerate(test_files, 1):
                # We still want to show progress
                print(f"[{i}/{len(test_files)}] ", end="")
                self._run_single_test(test_file, timeout=timeout)
            return

        active_jobs = []
        remaining_files = list(test_files)
        total_tests = len(test_files)
        started_count = 0
        finished_count = 0
        python_exec = self._get_python_exec()
        
        print(f"Parallel execution enabled (max {max_concurrent} concurrent jobs, timeout {timeout}s)")
        sys.stdout.flush()

        while remaining_files or active_jobs:
            while len(active_jobs) < max_concurrent and remaining_files:
                test_file = remaining_files.pop(0)
                started_count += 1
                start_time = time.time()
                # Use the correct python_exec and set PYTHONPATH
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
                            "start_time": start_time
                        })
                        print(f"[{started_count}/{total_tests}] Started {test_file.name} (PID: {pid})")
                        sys.stdout.flush()
                    else:
                        print(f"[{started_count}/{total_tests}] Failed to start {test_file.name} via BACKGROUND. Output: {output}")
                        sys.stdout.flush()
                        self._run_single_test(test_file, timeout=timeout)
                        finished_count += 1
                except Exception as e:
                    print(f"Error starting background job: {e}")
                    sys.stdout.flush()
                    self._run_single_test(test_file, timeout=timeout)
                    finished_count += 1

            finished_jobs = []
            for job in active_jobs:
                duration = time.time() - job["start_time"]
                
                if duration > timeout:
                    subprocess.run([str(background_bin), "--kill", job["pid"]], capture_output=True)
                    job["status_label"] = f"{self.BOLD}{self.RED}Timeout{self.RESET}"
                    job["duration"] = duration
                    self._save_result(job["file"].name, "Timeout", f"Test timed out after {timeout}s")
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
                                job["status_label"] = f"{self.BOLD}{self.GREEN}Success{self.RESET}"
                            else:
                                job["status_label"] = f"{self.BOLD}{self.RED}Failed{self.RESET}"
                                # Get full result
                                res_full = subprocess.run([str(background_bin), "--result", job["pid"]], capture_output=True, text=True)
                                report_path = self._save_result(job["file"].name, f"Failed (code {ret_code})", res_full.stdout)
                                
                                # Short summary of failure from stdout/stderr
                                last_line = ""
                                for line in res_full.stdout.splitlines():
                                    if line.strip():
                                        last_line = line.strip()
                                job["error_summary"] = f"(code {ret_code}) Reason: {last_line}"
                                if report_path:
                                    job["report_path"] = report_path
                            
                            job["duration"] = duration
                            finished_jobs.append(job)
                except Exception:
                    try:
                        os.kill(int(job["pid"]), 0)
                    except OSError:
                        job["status_label"] = f"{self.BOLD}{self.RED}Unknown{self.RESET}"
                        job["duration"] = duration
                        finished_jobs.append(job)
            
            for job in finished_jobs:
                active_jobs.remove(job)
                finished_count += 1
                msg = f"[{finished_count}/{total_tests}] Finished {job['file'].name}: {job['status_label']}"
                if "error_summary" in job:
                    msg += f" {job['error_summary']}"
                msg += f" (Duration: {job['duration']:.2f}s)"
                print(msg)
                if "report_path" in job:
                    print(f"  Full report: {job['report_path']}")
                sys.stdout.flush()
            
            if remaining_files or active_jobs:
                time.sleep(1)

        print("\nAll tests completed.")
        sys.stdout.flush()
