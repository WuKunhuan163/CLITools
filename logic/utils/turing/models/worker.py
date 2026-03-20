import threading
import sys
import os
import time
import inspect
from typing import List, Dict, Optional, Any, Set, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor
from logic.utils.turing.display.manager import truncate_to_width, _get_configured_width
from logic._.config import get_color
from logic.utils.turing.terminal.keyboard import get_global_suppressor
from logic.utils.turing.logic import TuringStage
from logic.utils.turing.utils import log_turing_error
from logic._.lang.utils import get_translation
from logic.utils import get_logic_dir, find_project_root

class DynamicStatusBar:
    """
    Manages a single-line or multi-line dynamic status display.
    Used for parallel tasks where status updates frequently.
    """
    def __init__(self, label: str = "Processing", use_bold_blue: bool = True, manager: Optional['MultiLineManager'] = None):
        from logic.utils.turing.terminal.keyboard import get_global_suppressor
        self.label = label
        self.active_items: Set[str] = set()
        self.lock = threading.Lock()
        self.suppressor = get_global_suppressor()
        self.is_suppressing = False
        self.total_count: Optional[int] = None
        self.completed_count: int = 0
        self.start_time: Optional[float] = None
        self.manager = manager
        
        # New: Support for ignoring local/pre-completed tasks in ETA
        self.baseline_completed = 0
        self.baseline_time = 0.0
        self.last_progress_time = time.time()
        
        self.BLUE = get_color("BLUE", "\033[34m") if use_bold_blue else ""
        self.BOLD = get_color("BOLD", "\033[1m") if use_bold_blue else ""
        self.RESET = get_color("RESET", "\033[0m") if use_bold_blue else ""

    def set_counts(self, total: int, completed: int = 0, baseline: int = 0):
        """
        Set progress counts for the status display.
        - total: Total number of items to process.
        - completed: Number of items already finished (on disk).
        - baseline: Number of items to ignore for speed/ETA calculation (e.g. local copies).
        """
        with self.lock:
            self.total_count = total
            self.completed_count = completed
            self.baseline_completed = baseline
            self.start_time = time.time()
            self.last_progress_time = time.time()
            self._render()

    def increment_completed(self):
        """Increment the completed count."""
        with self.lock:
            self.completed_count += 1
            self.last_progress_time = time.time()
            # If we just finished the first remote task, we might want to adjust baseline_time
            # but calculate_eta handles elapsed_time=0.
            self._render()

    def update(self, item_id: str, action: str = "add"):
        """Add or remove an item from the active status."""
        with self.lock:
            self.last_progress_time = time.time()
            if action == "add":
                if not self.is_suppressing:
                    self.suppressor.start()
                    self.is_suppressing = True
                self.active_items.add(item_id)
                if self.start_time is None:
                    self.start_time = time.time()
            elif action == "remove":
                if item_id in self.active_items:
                    self.active_items.remove(item_id)
                if not self.active_items and self.is_suppressing:
                    self.suppressor.stop()
                    self.is_suppressing = False
            self._render()

    def _render(self):
        """Render the status line."""
        if not self.active_items and self.completed_count == 0:
            return
            
        try:
            sorted_items = sorted(list(self.active_items), key=lambda x: int(x) if x.isdigit() else x)
        except:
            sorted_items = sorted(list(self.active_items))
            
        items_str = ", ".join(map(str, sorted_items))
        
        progress_info = ""
        if self.total_count is not None:
            from logic.utils import calculate_eta
            
            # ETA logic for remote tasks
            if self.baseline_completed > 0:
                remote_count = self.completed_count - self.baseline_completed
                remote_total = self.total_count - self.baseline_completed
                elapsed = time.time() - self.start_time if self.start_time else 0
                
                if remote_count <= 0:
                    # Not yet started any remote task, or all local
                    e_str = "00:00"
                    r_str = "??:??"
                else:
                    # Calculate ETA based ONLY on remote progress
                    _, r_str = calculate_eta(remote_count, remote_total, elapsed)
                    # For elapsed, we show the total elapsed time for the whole stage? 
                    # Or just the remote elapsed? User said "ETA only estimates remaining remote time".
                    # Usually elapsed means total time since the stage started.
                    from logic.utils import format_seconds
                    e_str = format_seconds(elapsed)
            else:
                elapsed = time.time() - self.start_time if self.start_time else 0
                e_str, r_str = calculate_eta(self.completed_count, self.total_count, elapsed)
                
            progress_info = f"({self.completed_count}/{self.total_count}) [{e_str}>{r_str}] "
            
        status_msg = f"{self.BLUE}{self.label}{self.RESET} {progress_info}{items_str}"
        
        if self.manager:
            self.manager.update("dynamic_status_bar", status_msg)
        else:
            width = _get_configured_width()
            sys.stdout.write(f"\r\033[K{truncate_to_width(status_msg, width)}")
            sys.stdout.flush()

    def clear(self):
        """Clear the status line."""
        with self.lock:
            if self.is_suppressing:
                self.suppressor.stop()
                self.is_suppressing = False
        
        if self.manager:
            self.manager.update("dynamic_status_bar", "", is_final=True)
        else:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

    def print_above(self, msg: str):
        """Print a message above the current status bar.
        When using MultiLineManager, removes the active status bar slot,
        prints the failure message, then re-creates the status bar at the bottom.
        This keeps the scrolling progress bar always below failure messages."""
        with self.lock:
            if self.manager:
                # 1. Remove active status bar to free up the bottom position
                self.manager.update("dynamic_status_bar", "remove")
                # 2. Print failure message as finalized content
                failure_id = f"worker_fail_{int(time.time() * 1000) % 10000}"
                self.manager.update(failure_id, msg, is_final=True, truncate=False)
                # 3. Re-create status bar at the bottom
                self._render()
            else:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                print(msg)
                self._render()

class ParallelWorkerPool:
    """
    Separated logic for managing parallel workers with integrated status display.
    """
    def __init__(self, max_workers: int = 4, status_label: str = "Processing", fail_label: Optional[str] = None, project_root: Optional[str] = None, tool_name: Optional[str] = None, manager: Optional['MultiLineManager'] = None, session_logger=None):
        self.max_workers = max_workers
        self.status_bar = DynamicStatusBar(label=status_label, manager=manager)
        self.fail_label = fail_label
        from pathlib import Path
        self.project_root = Path(project_root) if project_root else None
        self.tool_name = tool_name
        self.session_logger = session_logger

    def set_baseline(self, baseline: int):
        """Set baseline count for ETA calculation (already completed tasks)."""
        self.status_bar.baseline_completed = baseline

    def map(self, tasks: List[Tuple[Callable, str]], timeout: Optional[int] = None) -> List[bool]:
        """
        Backward compatibility for map interface used in some tools.
        tasks: List of (func, task_id)
        """
        formatted_tasks = [
            {"id": task_id, "action": func}
            for func, task_id in tasks
        ]
        
        # total = baseline + new_tasks
        total = self.status_bar.baseline_completed + len(formatted_tasks)
        self.status_bar.set_counts(total, baseline=self.status_bar.baseline_completed)
        
        results = {}
        def callback(tid, res):
            # res is the result from TuringStage.action
            # If it's False or a dict with success=False, it's a failure
            success = True
            if res is False:
                success = False
            elif isinstance(res, dict) and not res.get("success", True):
                success = False
            
            results[tid] = success
            self.status_bar.increment_completed()

        self.run(formatted_tasks, success_callback=callback, timeout=timeout)
        
        # Return results in the same order as input tasks
        return [results.get(tid, False) for _, tid in tasks]

    def run(self, tasks: List[Dict[str, Any]], success_callback: Optional[Callable] = None, timeout: Optional[int] = None) -> bool:
        """
        Run a list of tasks: [{"id": str, "action": callable, "args": tuple, "kwargs": dict}]
        """
        all_success = True
        
        def wrapper(task_id, func, *args, **kwargs):
            self.status_bar.update(task_id, "add")
            # Use name as the task identifier and a natural status
            stage = TuringStage(
                name=str(task_id), 
                action=func, 
                active_status="Running task", 
                success_status="Successfully executed task",
                fail_status="Failed to execute task",
                bold_part="Running task"
            )
            try:
                # Support passing stage to func if it accepts it
                sig = inspect.signature(func)
                if len(sig.parameters) > 0:
                    res = func(stage, *args, **kwargs)
                else:
                    res = func(*args, **kwargs)
                
                # Check for failure (False or dict with success=False)
                if res is False or (isinstance(res, dict) and not res.get("success", True)):
                    if not isinstance(res, dict):
                        res = {"success": False, "error": "Action returned False"}
                    
                    # Log error details
                    log_path = log_turing_error(stage, self.project_root, self.tool_name, session_logger=self.session_logger)
                    res["log_path"] = log_path
                    res["error_brief"] = stage.error_brief or res.get("error", "Unknown error").split('\n')[0]
                    
                    if success_callback:
                        success_callback(task_id, res)
                    
                    # Print failure above status bar with reason if available
                    from logic._.config import get_color
                    RED = get_color("RED", "\033[31m")
                    BOLD = get_color("BOLD", "\033[1m")
                    RESET = get_color("RESET", "\033[0m")
                    fail_label = self.fail_label or get_translation(self.project_root / "logic", "label_failed_to_install", "Failed to install")
                    
                    reason = res.get("error_brief", "")
                    reason_part = f" . {reason}" if reason else ""
                    self.status_bar.print_above(f"{BOLD}{RED}{fail_label}{RESET} {task_id}{reason_part}.")
                    
                    return False
                
                if success_callback:
                    success_callback(task_id, res)
                return res if res is not False else False
            except Exception as e:
                if isinstance(e, TuringError):
                    stage.error_brief = e.brief
                    stage.error_full = e.full
                
                log_path = log_turing_error(stage, self.project_root, self.tool_name, e if not isinstance(e, TuringError) else None, session_logger=self.session_logger)
                
                error_data = {
                    "success": False, 
                    "error": str(e),
                    "error_brief": stage.error_brief or str(e).split('\n')[0],
                    "log_path": log_path
                }
                if success_callback:
                    success_callback(task_id, error_data)
                
                # Print failure above status bar with reason if available
                from logic._.config import get_color
                RED = get_color("RED", "\033[31m")
                BOLD = get_color("BOLD", "\033[1m")
                RESET = get_color("RESET", "\033[0m")
                fail_label = self.fail_label or get_translation(self.project_root / "logic", "label_failed_to_install", "Failed to install")
                
                reason = error_data.get("error_brief", "")
                reason_part = f" . {reason}" if reason else ""
                self.status_bar.print_above(f"{BOLD}{RED}{fail_label}{RESET} {task_id}{reason_part}.")
                
                return False
            finally:
                self.status_bar.update(task_id, "remove")

        suppressor = get_global_suppressor()
        with suppressor:
            try:
                executor = ThreadPoolExecutor(max_workers=self.max_workers)
                try:
                    futures = {
                        executor.submit(wrapper, t["id"], t["action"], *t.get("args", ()), **t.get("kwargs", {})): t 
                        for t in tasks
                    }
                    
                    # Use wait() with timeout to detect stalls
                    from concurrent.futures import wait, FIRST_COMPLETED
                    stalled = False
                    while futures:
                        # Wait for at least one future to complete, with a short timeout to check for stalls
                        done, not_done = wait(futures, timeout=1.0, return_when=FIRST_COMPLETED)
                        
                        for future in done:
                            try:
                                if not future.result():
                                    all_success = False
                            except:
                                all_success = False
                            del futures[future]
                        
                        # Stall detection
                        if timeout and time.time() - self.status_bar.last_progress_time > timeout:
                            stalled = True
                            # Cancel all remaining futures
                            for future in futures:
                                future.cancel()
                            # Clear status bar
                            self.status_bar.clear()
                            
                            # Shut down executor without waiting for stalled threads
                            executor.shutdown(wait=False)
                            
                            from logic.utils.turing.logic import TuringError
                            raise TuringError(f"Stalled for {timeout}s", full=f"Stalled for {timeout}s")
                finally:
                    if not stalled:
                        executor.shutdown(wait=True)

            except KeyboardInterrupt:
                try: suppressor.stop(force=True)
                except: pass
                
                # Use hardcoded escape codes for reliability
                BOLD_RED = "\033[1;31m"
                RESET = "\033[0m"
                
                sys.stdout.write("\r\033[K")
                
                try:
                    root = find_project_root(self.project_root) if self.project_root else None
                    if root:
                        logic_dir = str(get_logic_dir(root))
                        cancelled_label = get_translation(logic_dir, "msg_operation_cancelled", "Operation cancelled")
                        by_user_label = get_translation(logic_dir, "msg_cancelled_by_user", "by user.")
                    else: raise Exception()
                except:
                    cancelled_label, by_user_label = "Operation cancelled", "by user."
                
                sys.stdout.write(f"{BOLD_RED}{cancelled_label}{RESET} {by_user_label}\n")
                sys.stdout.flush()
                os._exit(130)
            except Exception:
                try: suppressor.stop(force=True)
                except: pass
                raise
            finally:
                self.status_bar.clear()
        
        return all_success
