#!/usr/bin/env python3
import threading
import sys
import time
from typing import List, Dict, Optional, Any, Set, Callable
from logic.turing.display.manager import truncate_to_width, _get_configured_width
from logic.config import get_color

class DynamicStatusBar:
    """
    Manages a single-line or multi-line dynamic status display.
    Used for parallel tasks where status updates frequently.
    """
    def __init__(self, label: str = "Processing", use_bold_blue: bool = True):
        from logic.terminal.keyboard import get_global_suppressor
        self.label = label
        self.active_items: Set[str] = set()
        self.lock = threading.Lock()
        self.suppressor = get_global_suppressor()
        self.is_suppressing = False
        self.total_count: Optional[int] = None
        self.completed_count: int = 0
        self.start_time: Optional[float] = None
        
        # New: Support for ignoring local/pre-completed tasks in ETA
        self.baseline_completed = 0
        self.baseline_time = 0.0
        
        self.BLUE = get_color("BLUE", "\033[34m") if use_bold_blue else ""
        self.BOLD = get_color("BOLD", "\033[1m") if use_bold_blue else ""
        self.RESET = get_color("RESET", "\033[0m") if use_bold_blue else ""

    def set_counts(self, total: int, completed: int = 0, is_remote: bool = False):
        """
        Set progress counts for the status display.
        If is_remote=True, the current completed count is treated as a baseline 
        (local copies) and ignored for speed/ETA calculation.
        """
        with self.lock:
            self.total_count = total
            self.completed_count = completed
            self.start_time = time.time()
            if is_remote:
                self.baseline_completed = completed
                self.baseline_time = 0.0 # Will be updated on first remote completion
            else:
                self.baseline_completed = 0
                self.baseline_time = 0.0
            self._render()

    def increment_completed(self):
        """Increment the completed count."""
        with self.lock:
            self.completed_count += 1
            # If we just finished the first remote task, we might want to adjust baseline_time
            # but calculate_eta handles elapsed_time=0.
            self._render()

    def update(self, item_id: str, action: str = "add"):
        """Add or remove an item from the active status."""
        with self.lock:
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
            
        status_msg = f"{self.BLUE}{self.label}{self.RESET} {progress_info}{items_str}..."
        
        width = _get_configured_width()
        sys.stdout.write(f"\r\033[K{truncate_to_width(status_msg, width)}")
        sys.stdout.flush()

    def clear(self):
        """Clear the status line."""
        with self.lock:
            if self.is_suppressing:
                self.suppressor.stop()
                self.is_suppressing = False
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def print_above(self, msg: str):
        """Print a message above the current status bar."""
        with self.lock:
            # Erase current line
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            # Print the message followed by newline
            print(msg)
            # Re-render status bar on the new current line
            self._render()

class ParallelWorkerPool:
    """
    Separated logic for managing parallel workers with integrated status display.
    """
    def __init__(self, max_workers: int = 4, status_label: str = "Processing", project_root: Optional[str] = None, tool_name: Optional[str] = None):
        self.max_workers = max_workers
        self.status_bar = DynamicStatusBar(label=status_label)
        from pathlib import Path
        self.project_root = Path(project_root) if project_root else None
        self.tool_name = tool_name

    def run(self, tasks: List[Dict[str, Any]], success_callback: Optional[Callable] = None) -> bool:
        """
        Run a list of tasks: [{"id": str, "action": callable, "args": tuple, "kwargs": dict}]
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from logic.terminal.keyboard import KeyboardSuppressor
        from logic.turing.logic import TuringStage, TuringError
        from logic.turing.utils import log_turing_error
        all_success = True
        
        def wrapper(task_id, func, *args, **kwargs):
            self.status_bar.update(task_id, "add")
            stage = TuringStage(name=f"Task {task_id}", action=func, bold_part="Running Task")
            try:
                # Support passing stage to func if it accepts it
                import inspect
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
                    log_path = log_turing_error(stage, self.project_root, self.tool_name)
                    res["log_path"] = log_path
                    res["error_brief"] = stage.error_brief or res.get("error", "Unknown error").split('\n')[0]
                    
                    if success_callback:
                        success_callback(task_id, res)
                    return False
                
                if success_callback:
                    success_callback(task_id, res)
                return res if res is not False else False
            except Exception as e:
                if isinstance(e, TuringError):
                    stage.error_brief = e.brief
                    stage.error_full = e.full
                
                log_path = log_turing_error(stage, self.project_root, self.tool_name, e if not isinstance(e, TuringError) else None)
                
                error_data = {
                    "success": False, 
                    "error": str(e),
                    "error_brief": stage.error_brief or str(e).split('\n')[0],
                    "log_path": log_path
                }
                if success_callback:
                    success_callback(task_id, error_data)
                return False
            finally:
                self.status_bar.update(task_id, "remove")

        from logic.terminal.keyboard import get_global_suppressor
        suppressor = get_global_suppressor()
        with suppressor:
            try:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(wrapper, t["id"], t["action"], *t.get("args", ()), **t.get("kwargs", {})): t 
                        for t in tasks
                    }
                    for future in as_completed(futures):
                        try:
                            if not future.result():
                                all_success = False
                        except:
                            all_success = False
            except KeyboardInterrupt:
                try: suppressor.stop(force=True)
                except: pass
                
                # Print cancellation status in Red
                BOLD = get_color("BOLD", "\033[1m")
                RED = get_color("RED", "\033[31m")
                RESET = get_color("RESET", "\033[0m")
                
                # Try to get translations if available, otherwise fallback
                try:
                    from logic.lang.utils import get_translation
                    from logic.utils import get_logic_dir, find_project_root
                    root = find_project_root(self.project_root) if self.project_root else None
                    if root:
                        logic_dir = str(get_logic_dir(root))
                        cancelled_label = get_translation(logic_dir, "msg_operation_cancelled", "Operation cancelled")
                        by_user_label = get_translation(logic_dir, "msg_cancelled_by_user", "by user.")
                    else: raise Exception()
                except:
                    cancelled_label, by_user_label = "Operation cancelled", "by user."
                
                sys.stdout.write(f"\r\033[K{BOLD}{RED}{cancelled_label}{RESET} {by_user_label}\n")
                sys.stdout.flush()
                sys.exit(130)
            except Exception:
                try: suppressor.stop(force=True)
                except: pass
                raise
            finally:
                self.status_bar.clear()
        
        return all_success
