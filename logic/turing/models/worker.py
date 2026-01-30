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
        self.label = label
        self.active_items: Set[str] = set()
        self.lock = threading.Lock()
        
        self.BLUE = get_color("BLUE", "\033[34m") if use_bold_blue else ""
        self.BOLD = get_color("BOLD", "\033[1m") if use_bold_blue else ""
        self.RESET = get_color("RESET", "\033[0m") if use_bold_blue else ""

    def update(self, item_id: str, action: str = "add"):
        """Add or remove an item from the active status."""
        with self.lock:
            if action == "add":
                self.active_items.add(item_id)
            elif action == "remove":
                if item_id in self.active_items:
                    self.active_items.remove(item_id)
            self._render()

    def _render(self):
        """Render the status line."""
        if not self.active_items:
            return
            
        try:
            sorted_items = sorted(list(self.active_items), key=lambda x: int(x) if x.isdigit() else x)
        except:
            sorted_items = sorted(list(self.active_items))
            
        items_str = ", ".join(map(str, sorted_items))
        status_msg = f"{self.BOLD}{self.BLUE}{self.label}{self.RESET} {items_str}..."
        
        width = _get_configured_width()
        sys.stdout.write(f"\r\033[K{truncate_to_width(status_msg, width)}")
        sys.stdout.flush()

    def clear(self):
        """Clear the status line."""
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

class ParallelWorkerPool:
    """
    Separated logic for managing parallel workers with integrated status display.
    """
    def __init__(self, max_workers: int = 4, status_label: str = "Processing"):
        self.max_workers = max_workers
        self.status_bar = DynamicStatusBar(label=status_label)

    def run(self, tasks: List[Dict[str, Any]], success_callback: Optional[Callable] = None) -> bool:
        """
        Run a list of tasks: [{"id": str, "action": callable, "args": tuple, "kwargs": dict}]
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        all_success = True
        
        def wrapper(task_id, func, *args, **kwargs):
            self.status_bar.update(task_id, "add")
            try:
                res = func(*args, **kwargs)
                if success_callback:
                    success_callback(task_id, res)
                return res
            except:
                if success_callback:
                    success_callback(task_id, False)
                return False
            finally:
                self.status_bar.update(task_id, "remove")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(wrapper, t["id"], t["action"], *t.get("args", ()), **t.get("kwargs", {})): t 
                for t in tasks
            }
            for future in as_completed(futures):
                if not future.result():
                    all_success = False
        
        self.status_bar.clear()
        return all_success
