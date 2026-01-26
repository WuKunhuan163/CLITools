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

    def run_tests(self, start_id=None, end_id=None, max_concurrent=3, timeout=60, quiet_if_no_tests=False) -> bool:
        # ... existing ...
        try:
            all_tests = self._get_test_files()
            if not all_tests:
                if not quiet_if_no_tests:
                    print(self._("test_no_tests", "No tests found for {tool}", tool=self.tool_name))
                return True # Technically no failures

            if start_id is not None or end_id is not None:
                start = start_id if start_id is not None else 0
                end = end_id if end_id is not None else len(all_tests) - 1
                selected_tests = all_tests[start:end+1]
            else:
                selected_tests = all_tests

            if not selected_tests:
                print(self._("test_no_selected", "No tests selected in the specified range."))
                return True

            print(self._("test_running", "Preparing to run {count} tests for {tool} tool (max {max} concurrent tests)...", count=len(selected_tests), tool=self.tool_name, max=max_concurrent))
            sys.stdout.flush()
            return success
            
        finally:
            if old_lang: os.environ["TOOL_LANGUAGE"] = old_lang
            else: os.environ.pop("TOOL_LANGUAGE", None)

    def _get_test_files(self):
        test_dir = self.tool_dir / "test"
        if not test_dir.exists():
            return []

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
            return str(filepath)
        except Exception:
            return None

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
            return f"{self.colors['BOLD']}{self.colors['GREEN']}{self._('label_success', 'Success')}{self.colors['RESET']}"
        elif status == "Failed":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('label_failed', 'Failed')}{self.colors['RESET']}"
        elif status == "Timeout":
            return f"{self.colors['BOLD']}{self.colors['RED']}{self._('label_timeout', 'Timeout')}{self.colors['RESET']}"
        return f"{self.colors['BOLD']}{self._('test_status_unknown', 'Unknown')}{self.colors['RESET']}"

    def _run_parallel_tests(self, test_files, max_concurrent, timeout=60):
        """Run multiple tests using TuringWorker mechanism for multi-line progress."""
        from logic.turing.display.manager import MultiLineManager
        from logic.worker import TuringWorker
        from logic.turing.logic import TuringTask, StepResult, WorkerState
        
        # 1. Config
        if max_concurrent == 3:
            from logic.config import get_setting
            max_concurrent = get_setting("test_default_concurrency", 3)

        manager = MultiLineManager()
        task_queue = Queue()
        stop_event = threading.Event()
        
        # Track all started test PIDs for surgical cleanup
        all_test_pids = set()
        pids_lock = threading.Lock()
        
        for f in test_files:
            task_queue.put(f)
        
        # Shared results counter
        success_count = [0]
        
        def test_step(test_file, worker_id):
            def logic():
                if stop_event.is_set(): return
                
                active_label = self.colors['BLUE'] + self.colors['BOLD'] + self._("test_running_status", "Running") + self.colors['RESET']
                timeout_msg = self._("label_timeout", "timeout")
                
                def get_running_msg(elapsed):
                    # Localizable running status message
                    # Default (en): "Running: file.py (10s / timeout: 60s)"
                    # Arabic (ar): "(10s / timeout: 60s) file.py :Running"
                    bold_file = f"{self.colors['BOLD']}{test_file.name}{self.colors['RESET']}"
                    return self._("test_running_line", "{status}: {file} ({elapsed}s / {timeout_label}: {timeout}s)", 
                                 status=active_label, file=bold_file, elapsed=int(elapsed), 
                                 timeout_label=timeout_msg, timeout=timeout)

                # Initial update
                yield StepResult(get_running_msg(0), state=WorkerState.CONTINUE)
                
                # Execution
                start_time = time.time()
                python_exec = self._get_python_exec()
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"
                
                try:
                    proc = subprocess.Popen([python_exec, "-u", str(test_file)], 
                                           env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    
                    with pids_lock:
                        all_test_pids.add(proc.pid)
                        
                    while proc.poll() is None:
                        if stop_event.is_set():
                            proc.kill()
                            status_raw, duration, error_msg, report_path = "Interrupted", time.time() - start_time, None, None
                            break
                        
                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            proc.kill()
                            status_raw, duration, error_msg, report_path = "Timeout", elapsed, None, None
                            break
                        # LIVE UPDATE
                        yield StepResult(get_running_msg(elapsed), state=WorkerState.CONTINUE)
                        time.sleep(0.5)
                    else:
                        if stop_event.is_set():
                             status_raw, duration, error_msg, report_path = "Interrupted", time.time() - start_time, None, None
                        else:
                            stdout, stderr = proc.communicate()
                            duration = time.time() - start_time
                            if proc.returncode == 0:
                                status_raw, error_msg, report_path = "Success", None, None
                                with pids_lock: success_count[0] += 1
                            else:
                                full_output = stdout + stderr
                                report_path = self._save_result(test_file.name, "Failed", full_output, python_info=python_exec)
                                reason = self._get_error_reason(full_output)
                                status_raw, error_msg = "Failed", f"(code {proc.returncode}) Reason: {reason}"
                except Exception as e:
                    status_raw, duration, error_msg, report_path = "Error", time.time() - start_time, str(e), None
                finally:
                    # Note: we don't remove from all_test_pids here as we need them for final cleanup
                    pass

                # Final result message
                if status_raw == "Interrupted":
                    # Don't update finalized message if interrupted, just stop
                    return
                
                status_label = self._get_status_label(status_raw)
                duration_label = self._("label_duration", "Duration")
                bold_file = f"{self.colors['BOLD']}{test_file.name}{self.colors['RESET']}"
                if error_msg:
                    msg = self._("test_finished_with_error", "{status}: {file} {error} ({duration_label}: {duration:.2f}s)", 
                                 status=status_label, file=bold_file, error=error_msg, duration_label=duration_label, duration=duration)
                else:
                    msg = self._("test_finished", "{status}: {file} ({duration_label}: {duration:.2f}s)", 
                                 status=status_label, file=bold_file, duration_label=duration_label, duration=duration)
                
                if report_path:
                    # Use | instead of \n to keep it single-line as requested
                    report_label = self._("test_full_report", "Full report: {path}", path=report_path)
                    msg += f" | {report_label}"

                yield StepResult(msg, state=WorkerState.SUCCESS if status_raw == "Success" else WorkerState.ERROR, is_final=True)
            return logic

        def worker_loop(worker_id):
            worker = TuringWorker(worker_id, manager)
            while not stop_event.is_set():
                try:
                    f = task_queue.get_nowait()
                except: break
                
                try:
                    task = TuringTask(f.name, [test_step(f, worker_id)])
                    worker.execute(task)
                finally:
                    task_queue.task_done()
        
        # Start threads
        threads = []
        for i in range(min(max_concurrent, len(test_files))):
            t = threading.Thread(target=worker_loop, args=(f"W{i+1}",), daemon=False)
            t.start()
            threads.append(t)
        
        try:
            # Wait for all
            task_queue.join()
        except KeyboardInterrupt:
            # Signal workers to stop
            stop_event.set()
            # Clear remaining tasks
            while not task_queue.empty():
                try: task_queue.get_nowait(); task_queue.task_done()
                except: break
            
            # Print interrupted message before finalization to avoid cursor jump
            print(f"\n{self.colors['BOLD']}{self.colors['RED']}{self._('test_interrupted_label', 'Tests Stopped')}{self.colors['RESET']}: {self._('test_interrupted_reason', 'User pressed Ctrl+C')}")

        for t in threads:
            t.join(timeout=1)
            
        manager.finalize()
        
        # Surgical cleanup of GUI instances started by our tests
        self._cleanup_resources(all_test_pids)
        
        if not stop_event.is_set():
            print(self._("test_all_completed", "\nAll tests completed."))
        sys.stdout.flush()
        return success_count[0] == len(test_files)

    def _cleanup_resources(self, test_pids=None):
        """Cleanup leftover processes and GUI windows surgicaly."""
        import psutil
        
        # 1. Surgical cleanup of GUI instances started by our tests
        if test_pids:
            instance_dir = self.project_root / "data" / "run" / "instances"
            if instance_dir.exists():
                for f in instance_dir.glob("gui_*.json"):
                    try:
                        with open(f, 'r') as info_file:
                            info = json.load(info_file)
                            gui_pid = info.get("pid")
                            if not gui_pid: continue
                            
                            # Check if this GUI's parent is one of our test processes
                            try:
                                p = psutil.Process(gui_pid)
                                ppid = p.ppid()
                                if ppid in test_pids:
                                    # Target this specific GUI
                                    userinput_bin = self.project_root / "bin" / "USERINPUT"
                                    if userinput_bin.exists():
                                        subprocess.run([str(userinput_bin), "stop", str(gui_pid)], capture_output=True)
                                    else:
                                        p.terminate()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    except: continue

        # 2. Existing logic to cleanup leftover test scripts
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(self.tool_name in part for part in cmdline) and any("test_" in part for part in cmdline):
                    if proc.info['pid'] != os.getpid():
                        if not test_pids or proc.info['pid'] in test_pids:
                            proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
