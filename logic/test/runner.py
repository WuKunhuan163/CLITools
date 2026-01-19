import os
import sys
import json
import time
import subprocess
import re
import hashlib
import threading
from pathlib import Path
from queue import Queue
from datetime import datetime

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        if tool_name == "root":
            self.tool_dir = self.project_root
        else:
            self.tool_dir = self.project_root / "tool" / tool_name
        self.cache_file = self.tool_dir / "test" / ".tests_cache.json"
        
        # Import shared utils
        sys.path.append(str(self.project_root))
        from logic.lang.utils import get_translation
        from logic.config import get_color
        
        from logic.utils import get_logic_dir
        
        def lookup(key, default, **kwargs):
            # Try tool-specific first
            tool_internal = get_logic_dir(self.tool_dir)
            res = get_translation(str(tool_internal), key, None)
            if res is None:
                # Fallback to root
                res = get_translation(str(get_logic_dir(self.project_root)), key, default)
            return res.format(**kwargs)
        
        self._ = lookup
        self.colors = {
            "GREEN": get_color("GREEN", "\033[32m"),
            "BOLD": get_color("BOLD", "\033[1m"),
            "RED": get_color("RED", "\033[31m"),
            "BLUE": get_color("BLUE", "\033[34m"),
            "YELLOW": get_color("YELLOW", "\033[33m"),
            "RESET": get_color("RESET", "\033[0m")
        }

        self.dependencies = []
        tool_json_path = self.tool_dir / "tool.json"
        if tool_json_path.exists():
            try:
                with open(tool_json_path, 'r') as f:
                    self.dependencies = json.load(f).get("dependencies", [])
            except Exception: pass

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
        if "PYTHON" in self.dependencies:
            from logic.utils import get_logic_dir
            python_utils_path = get_logic_dir(self.project_root / "tool" / "PYTHON") / "utils.py"
            if python_utils_path.exists():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("python_tool_utils", str(python_utils_path))
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        return module.get_python_exec()
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

    def _cleanup_old_reports(self, result_dir, limit=1024, batch_size=None):
        reports = sorted(list(result_dir.glob("*.txt")), key=os.path.getmtime)
        if len(reports) > limit:
            batch_size = batch_size or limit // 2
            for i in range(min(len(reports), batch_size)):
                try:
                    os.remove(reports[i])
                except Exception: pass

    def _get_error_reason(self, output):
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return "No output"
        markers = ["AssertionError:", "ModuleNotFoundError:", "TypeError:", "ValueError:", "RuntimeError:"]
        for line in reversed(lines):
            for marker in markers:
                if marker in line:
                    idx = line.find(marker)
                    reason = line[idx:]
                    return reason[:100] + "..." if len(reason) > 100 else reason
        for line in reversed(lines):
            if "Error:" in line:
                return line[:100] + "..." if len(line) > 100 else line
        return lines[-1][:100] + "..." if len(lines[-1]) > 100 else lines[-1]

    def _get_status_label(self, status):
        if status == "Success":
            return f"{self.colors['BOLD']}{self.colors['GREEN']}{self._('test_status_success', 'Success')}{self.colors['RESET']}"
        elif status == "Failed":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('test_status_failed', 'Failed')}{self.colors['RESET']}"
        elif status == "Timeout":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('test_status_timeout', 'Timeout')}{self.colors['RESET']}"
        return f"{self.colors['BOLD']}{self._('test_status_unknown', 'Unknown')}{self.colors['RESET']}"

    def _run_parallel_tests(self, test_files, max_concurrent, timeout=60):
        """Run tests using custom MultiLineManager logic for results at top, active at bottom."""
        from logic.turing.display.manager import MultiLineManager
        
        # 1. Config
        if max_concurrent == 3:
            from logic.config import get_setting
            max_concurrent = get_setting("test_default_concurrency", 3)

        print(self._("test_parallel_enabled_simple", "Parallel execution enabled (max {max} concurrent jobs)", max=max_concurrent))
        sys.stdout.flush()

        manager = MultiLineManager()
        task_queue = Queue()
        for f in test_files:
            task_queue.put(f)
        
        active_label = self.colors['BLUE'] + self.colors['BOLD'] + self._("test_running_status", "Running") + self.colors['RESET']
        timeout_msg = self._("test_timeout_label", "timeout")

        def worker_loop(worker_id):
            while True:
                try:
                    test_file = task_queue.get_nowait()
                except: break
                
                # Start timer
                start_time = time.time()
                python_exec = self._get_python_exec()
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"
                
                def get_running_msg(elapsed):
                    return f"{active_label}: {test_file.name} ({int(elapsed)}s / {timeout_msg}: {timeout}s)"

                # Initial update
                manager.update(worker_id, get_running_msg(0))
                
                try:
                    proc = subprocess.Popen([python_exec, "-u", str(test_file)], 
                                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    while proc.poll() is None:
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            proc.kill()
                            status_raw, duration, error_msg, report_path = "Timeout", elapsed, None, None
                            break
                        # Update live status
                        manager.update(worker_id, get_running_msg(elapsed))
                        time.sleep(0.5)
                    else:
                        stdout, stderr = proc.communicate()
                        duration = time.time() - start_time
                        if proc.returncode == 0:
                            status_raw, error_msg, report_path = "Success", None, None
                        else:
                            full_output = stdout + stderr
                            report_path = self._save_result(test_file.name, "Failed", full_output, python_info=python_exec)
                            reason = self._get_error_reason(full_output)
                            status_raw, error_msg = "Failed", f"(code {proc.returncode}) Reason: {reason}"
                except Exception as e:
                    status_raw, duration, error_msg, report_path = "Error", time.time() - start_time, str(e), None

                # Finish result
                status_label = self._get_status_label(status_raw)
                if error_msg:
                    msg = self._("test_finished_with_error", "{status}: {file} {error} (Duration: {duration:.2f}s)", 
                                 status=status_label, file=test_file.name, error=error_msg, duration=duration)
                else:
                    msg = self._("test_finished", "{status}: {file} (Duration: {duration:.2f}s)", 
                                 status=status_label, file=test_file.name, duration=duration)
                
                if report_path:
                    msg += "\n" + self._("test_full_report", "  Full report: {path}", path=report_path)

                # Sticky final result (moves ABOVE active area)
                manager.update(worker_id, msg, is_final=True)
                task_queue.task_done()

        # Start threads
        threads = []
        for i in range(min(max_concurrent, len(test_files))):
            t = threading.Thread(target=worker_loop, args=(f"W{i+1}",), daemon=False)
            t.start()
            threads.append(t)
        
        # Wait for all workers
        for t in threads:
            t.join()
            
        manager.finalize()
        print(self._("test_all_completed", "\nAll tests completed."))
        sys.stdout.flush()

    def _cleanup_resources(self):
        """Cleanup leftover processes and GUI windows."""
        userinput_stop = self.project_root / "bin" / "USERINPUT"
        if userinput_stop.exists():
            subprocess.run([str(userinput_stop), "stop"], capture_output=True)
        else:
            if sys.platform != "win32":
                subprocess.run(["pkill", "-f", "USERINPUT"], capture_output=True)

        background_cleanup = self.project_root / "bin" / "BACKGROUND"
        if background_cleanup.exists():
            subprocess.run([str(background_cleanup), "--cleanup"], capture_output=True)
            
        try:
            import psutil
        except ImportError:
            return

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(self.tool_name in part for part in cmdline) and any("test_" in part for part in cmdline):
                    if proc.info['pid'] != os.getpid():
                        proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
