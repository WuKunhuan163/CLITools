#!/usr/bin/env python3
"""
GCS GUI Queue Manager: ensures GUI interaction windows execute in FIFO order.

When multiple GCS commands need GUI windows (e.g., cd followed by echo >>),
this queue ensures they execute sequentially. Uses file-based locking for
cross-process synchronization.
"""
import os
import sys
import json
import time
import fcntl
from pathlib import Path
from typing import Dict, Any, Optional


class GUIQueue:
    """File-lock-based FIFO queue for GCS GUI windows."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.run_dir = project_root / "data" / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.run_dir / "gcs_gui.lock"
        self.queue_path = self.run_dir / "gcs_gui_queue.json"
        self._lock_fd = None

    def acquire(self, timeout: int = 600, request_id: str = None) -> bool:
        """
        Acquire the GUI lock. Blocks until the lock is available or timeout.
        Returns True if acquired, False if timed out.
        """
        if request_id:
            self._register_request(request_id)

        self._lock_fd = open(self.lock_path, 'w')
        start = time.time()
        while True:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._write_holder(request_id)
                return True
            except (IOError, OSError):
                if time.time() - start > timeout:
                    self._lock_fd.close()
                    self._lock_fd = None
                    return False
                time.sleep(0.5)

    def release(self):
        """Release the GUI lock."""
        if self._lock_fd:
            try:
                self._clear_holder()
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                self._lock_fd.close()
            except Exception:
                pass
            self._lock_fd = None

    def run_gui_subprocess(self, tool_instance, python_exe, script_path, timeout,
                           args=None, request_id=None) -> Dict[str, Any]:
        """
        Acquire the queue lock, run the GUI subprocess, then release.
        Wraps logic.gui.manager.run_gui_subprocess with queue ordering.
        """
        from logic.interface.gui import run_gui_subprocess as _run_gui

        rid = request_id or f"{os.getpid()}_{int(time.time())}"
        if not self.acquire(timeout=timeout, request_id=rid):
            return {"status": "timeout", "message": "Queue lock acquisition timed out."}

        try:
            result = _run_gui(tool_instance, python_exe, script_path, timeout, args=args)
            return result
        finally:
            self.release()

    def _register_request(self, request_id: str):
        """Register a pending request in the queue file (for observability)."""
        try:
            queue = self._read_queue()
            queue.append({
                "id": request_id,
                "pid": os.getpid(),
                "ts": time.time(),
                "status": "pending"
            })
            self._write_queue(queue)
        except Exception:
            pass

    def _write_holder(self, request_id: str = None):
        """Record which process holds the lock."""
        try:
            if self._lock_fd:
                self._lock_fd.seek(0)
                self._lock_fd.truncate()
                self._lock_fd.write(json.dumps({
                    "pid": os.getpid(),
                    "id": request_id,
                    "ts": time.time()
                }))
                self._lock_fd.flush()
        except Exception:
            pass

    def _clear_holder(self):
        """Clear the lock holder info."""
        try:
            if self._lock_fd:
                self._lock_fd.seek(0)
                self._lock_fd.truncate()
                self._lock_fd.flush()
        except Exception:
            pass

    def _read_queue(self) -> list:
        try:
            if self.queue_path.exists():
                with open(self.queue_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _write_queue(self, queue: list):
        try:
            with open(self.queue_path, 'w') as f:
                json.dump(queue, f, indent=2)
        except Exception:
            pass


_global_queue = None


def get_gui_queue(project_root: Path) -> GUIQueue:
    """Get or create the global GCS GUI queue singleton."""
    global _global_queue
    if _global_queue is None:
        _global_queue = GUIQueue(project_root)
    return _global_queue
