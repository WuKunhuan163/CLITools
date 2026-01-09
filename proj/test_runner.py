import os
import sys
import json
import time
import subprocess
import unittest
import threading
from pathlib import Path
import re

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        self.tool_dir = self.project_root / tool_name
        self.test_dir = self.tool_dir / "test"
        self.temp_dir = self.test_dir / "_TEMP"
        self.all_tests = []
        self._discover_tests()

    def _discover_tests(self):
        if not self.test_dir.exists():
            return
        
        # Discover all test_*.py files in the test directory
        test_files = sorted(list(self.test_dir.glob("test_*.py")))
        for test_file in test_files:
            self.all_tests.append(test_file.name)

    def list_tests(self):
        if not self.all_tests:
            print(f"No tests found for tool '{self.tool_name}' in {self.test_dir}")
            return
        
        print(f"📋 Test List for '{self.tool_name}' (ID: Test File)")
        print("=" * 60)
        for i, test_file in enumerate(self.all_tests):
            print(f"{i:2d}: {test_file}")
        print(f"\nTotal: {len(self.all_tests)} tests")

    def run_tests(self, start_id=None, end_id=None, max_concurrent=3):
        if not self.all_tests:
            print(f"No tests to run for {self.tool_name}")
            return

        if start_id is None:
            # If no range, run all tests one by one or in parallel?
            # User said: "如果你认为代码量过大，那就创建根目录的proj文件夹"
            # And "指定range时，可以根据测试id来创建worker并行"
            # So if no range, maybe just run them normally?
            for test_file in self.all_tests:
                self._run_single_test(test_file)
            return

        if start_id < 0 or end_id >= len(self.all_tests) or start_id > end_id:
            print(f"Invalid range: {start_id}-{end_id}. Valid range: 0-{len(self.all_tests)-1}")
            return

        selected_tests = self.all_tests[start_id:end_id+1]
        
        # Parallel execution
        self._run_parallel_tests(selected_tests, max_concurrent)

    def _run_single_test(self, test_file):
        test_path = self.test_dir / test_file
        print(f"\n🚀 Running test: {test_file}")
        print("-" * 40)
        
        # Command to run unittest for this file
        # Add tool_dir and project_root to PYTHONPATH
        pythonpath = f"{self.tool_dir}:{self.project_root}"
        cmd = [sys.executable, "-m", "unittest", str(test_path)]
        
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{pythonpath}:{env.get('PYTHONPATH', '')}"
        
        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"✅ {test_file} passed.")
        except subprocess.CalledProcessError:
            print(f"❌ {test_file} failed.")

    def _run_parallel_tests(self, test_files, max_concurrent):
        self.temp_dir.mkdir(exist_ok=True)
        
        # Clean old results
        for f in self.temp_dir.glob("*_output.txt"):
            f.unlink()

        print(f"🚀 Running {len(test_files)} tests in parallel (max concurrent: {max_concurrent})")
        print("=" * 60)

        test_queue = list(test_files)
        running_pids = {} # {pid: (test_file, output_file)}
        results = {} # {test_file: status}
        last_msg = ""

        while test_queue or running_pids:
            # Start new tests
            while len(running_pids) < max_concurrent and test_queue:
                test_file = test_queue.pop(0)
                pid, output_file = self._start_background_test(test_file)
                if pid:
                    running_pids[pid] = (test_file, output_file)
                else:
                    results[test_file] = "FAILED_TO_START"

            # Check status
            completed_pids = []
            for pid, (test_file, output_file) in running_pids.items():
                status = self._get_background_status(pid)
                if status == "completed":
                    completed_pids.append(pid)
                    test_status = self._parse_test_output(output_file)
                    results[test_file] = test_status
                    self._rename_output_file(test_file, output_file, test_status)
                    
                    icon = "✅" if test_status == "pass" else "❌"
                    print(f"{icon} {test_file} completed: {test_status.upper()}")

            for pid in completed_pids:
                del running_pids[pid]

            msg = f"Progress: {len(results)}/{len(test_files)} done, {len(running_pids)} running"
            if msg != last_msg:
                print(msg)
                last_msg = msg

            if test_queue or running_pids:
                time.sleep(2)

        # Final Report
        print("\n" + "=" * 60)
        print("Final Test Report")
        passed = [t for t, s in results.items() if s == "pass"]
        failed = [t for t, s in results.items() if s == "fail"]
        others = [t for t, s in results.items() if s not in ["pass", "fail"]]
        
        print(f"Total: {len(test_files)}")
        print(f"Passed: {len(passed)}")
        print(f"Failed: {len(failed)}")
        if others:
            print(f"Others: {len(others)}")
        
        print("\nAll output files are in:", self.temp_dir)

    def _start_background_test(self, test_file):
        test_short_name = Path(test_file).stem
        output_file = f"⏳{test_short_name}_output.txt"
        output_path = self.temp_dir / output_file
        
        pythonpath = f"{self.tool_dir}:{self.project_root}"
        test_abs_path = self.test_dir / test_file
        
        # Command should include setting PYTHONPATH
        cmd = f"export PYTHONPATH={pythonpath}:$PYTHONPATH && {sys.executable} -m unittest {test_abs_path} > {output_path} 2>&1"
        
        try:
            # Use BACKGROUND_CMD if available as a tool
            bg_cmd_tool = self.project_root / "bin" / "BACKGROUND_CMD"
            
            if not bg_cmd_tool.exists():
                # Fallback to direct python call
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return process.pid, output_file
                
            result = subprocess.run(
                [str(bg_cmd_tool), cmd],
                capture_output=True, text=True, cwd=str(self.project_root)
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "Process started: PID" in output:
                    pid_match = re.search(r"PID (\d+)", output)
                    if pid_match:
                        return int(pid_match.group(1)), output_file
        except Exception as e:
            print(f"Error starting background test: {e}")
        
        return None, None

    def _get_background_status(self, pid):
        try:
            bg_cmd_tool = self.project_root / "bin" / "BACKGROUND_CMD"
            
            if not bg_cmd_tool.exists():
                try:
                    os.kill(pid, 0)
                    return "running"
                except OSError:
                    return "completed"

            result = subprocess.run(
                [str(bg_cmd_tool), "--status", str(pid), "--json"],
                capture_output=True, text=True, cwd=str(self.project_root)
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                # Handle both success/fail if process finished
                status_info = data.get('status', {})
                if status_info.get('status') in ['completed', 'failed']:
                    return "completed"
            return "running"
        except Exception:
            return "running"

    def _parse_test_output(self, output_file):
        output_path = self.temp_dir / output_file
        if not output_path.exists():
            return "error"
        
        try:
            content = output_path.read_text(encoding='utf-8')
            if "OK" in content and "FAILED" not in content:
                return "pass"
            elif "FAILED" in content:
                return "fail"
        except Exception:
            return "error"
        return "unknown"

    def _rename_output_file(self, test_file, old_output_file, status):
        test_short_name = Path(test_file).stem
        status_emoji = "✅" if status == "pass" else "❌" if status == "fail" else "❓"
        new_name = f"{status_emoji}{test_short_name}_output.txt"
        
        old_path = self.temp_dir / old_output_file
        new_path = self.temp_dir / new_name
        
        try:
            if old_path.exists():
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)
        except Exception:
            pass

