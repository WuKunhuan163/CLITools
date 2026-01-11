import os
import sys
import unittest
import subprocess
import time
from pathlib import Path
import json
import re

class TestRunner:
    def __init__(self, tool_name, project_root):
        self.tool_name = tool_name
        self.project_root = Path(project_root)
        self.tool_dir = self.project_root / "tool" / tool_name
        self.test_dir = self.tool_dir / "test"
        self.cache_file = self.test_dir / ".tests_cache.json"

    def get_test_files(self):
        """Find all test_*.py files and manage the cache."""
        if not self.test_dir.exists():
            return []
        
        # 1. Try to load from cache
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached_files = json.load(f)
                    # Verify files still exist
                    test_files = [self.test_dir / f for f in cached_files if (self.test_dir / f).exists()]
                    if len(test_files) == len(cached_files):
                        return test_files
            except Exception:
                pass

        # 2. Rescan and sort alphabetically
        test_files = sorted(list(self.test_dir.glob("test_*.py")), key=lambda p: p.name)
        
        # 3. Save to cache
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
            return
        
        print(f"Available tests for {self.tool_name} (Indices are 0-based):")
        for i, test_file in enumerate(test_files):
            print(f"  [{i}] {test_file.name}")

    def run_tests(self, start_id=None, end_id=None, max_concurrent=1):
        """Run tests with inclusive range indexing."""
        test_files = self.get_test_files()
        if not test_files:
            print(f"No tests found for {self.tool_name}")
            return

        # Filter by inclusive range if provided (0-indexed)
        if start_id is not None and end_id is not None:
            test_files = test_files[start_id : end_id + 1]
        
        if not test_files:
            print("No tests selected in the specified range.")
            return

        print(f"Running {len(test_files)} tests for {self.tool_name}...")
        
        if len(test_files) == 1 and max_concurrent == 1:
            # Run single test in foreground
            self._run_single_test(test_files[0])
        else:
            # Run multiple tests in parallel
            self._run_parallel_tests(test_files, max_concurrent)

    def _run_single_test(self, test_file):
        """Run a single test file using unittest."""
        print(f"\n--- Running {test_file.name} ---")
        
        # Use the tool's python executable if it depends on PYTHON
        python_exec = sys.executable
        
        python_tool_dir = self.project_root / "tool" / "PYTHON"
        python_utils_path = python_tool_dir / "proj" / "utils.py"
        
        # Check if tool depends on PYTHON
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
                spec = importlib.util.spec_from_file_location("python_utils_test", str(python_utils_path))
                python_utils_test = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(python_utils_test)
                python_exec = python_utils_test.get_python_exec()
            except Exception:
                pass

        env = os.environ.copy()
        # Add the project root (containing root 'proj') and tool's directory (containing 'proj') to PYTHONPATH
        env["PYTHONPATH"] = f"{self.project_root}:{self.tool_dir}:{env.get('PYTHONPATH', '')}"

        result = subprocess.run([python_exec, "-m", "unittest", str(test_file)], env=env)
        if result.returncode == 0:
            print(f"SUCCESS: {test_file.name}")
        else:
            print(f"FAILED: {test_file.name}")

    def _run_parallel_tests(self, test_files, max_concurrent):
        """Run multiple tests in parallel using BACKGROUND tool."""
        background_bin = self.project_root / "bin" / "BACKGROUND"
        if not background_bin.exists():
            # Fallback to sequential
            print("BACKGROUND tool not found. Falling back to sequential execution.")
            for test_file in test_files:
                self._run_single_test(test_file)
            return

        active_jobs = []
        remaining_files = list(test_files)
        
        print(f"Parallel execution enabled (max {max_concurrent} concurrent jobs)")

        while remaining_files or active_jobs:
            # Fill up slots
            while len(active_jobs) < max_concurrent and remaining_files:
                test_file = remaining_files.pop(0)
                cmd = f"{sys.executable} -m unittest {test_file}"
                
                try:
                    proc = subprocess.run([str(background_bin), cmd], capture_output=True, text=True)
                    output = proc.stdout
                    # Match "PID 12345" or "PID: 12345"
                    match = re.search(r"PID:?\s*(\d+)", output)
                    if match:
                        pid = match.group(1)
                        active_jobs.append({"pid": pid, "file": test_file})
                        print(f"Started {test_file.name} (PID: {pid})")
                    else:
                        print(f"Failed to start {test_file.name} via BACKGROUND. Output: {output}")
                        self._run_single_test(test_file)
                except Exception as e:
                    print(f"Error starting background job: {e}")
                    self._run_single_test(test_file)

            # Check for finished jobs
            finished_jobs = []
            for job in active_jobs:
                try:
                    os.kill(int(job["pid"]), 0)
                except OSError:
                    finished_jobs.append(job)
                except Exception:
                    pass
            
            for job in finished_jobs:
                active_jobs.remove(job)
                print(f"Finished {job['file'].name}")
            
            if remaining_files or active_jobs:
                time.sleep(1)

        print("\nAll tests completed.")
