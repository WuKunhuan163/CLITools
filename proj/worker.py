import sys
import os
import time
import threading
from typing import List, Callable, Generator, Any, Dict, Optional
from pathlib import Path

class MultiLineManager:
    """
    Manages multiple independent lines in the terminal.
    Allows for 'sticky' lines that stay when a task is finished.
    """
    def __init__(self):
        self.active_workers = {}  # worker_id -> current_line_index
        self.all_lines = []       # list of (text, is_final)
        self.lock = threading.Lock()

    def update(self, worker_id: str, text: str, is_final: bool = False):
        with self.lock:
            if worker_id not in self.active_workers:
                # Register new line for worker at the bottom
                line_idx = len(self.all_lines)
                self.active_workers[worker_id] = line_idx
                self.all_lines.append((text, is_final))
                sys.stdout.write(f"{text}\n")
                sys.stdout.flush()
            else:
                line_idx = self.active_workers[worker_id]
                self.all_lines[line_idx] = (text, is_final)
                
                # Calculate distance from current cursor (bottom) to the target line
                dist = len(self.all_lines) - line_idx
                
                # Move up, clear line, print new text, move back down
                sys.stdout.write(f"\033[{dist}A\r\033[K{text}\033[{dist}B\r")
                sys.stdout.flush()

            if is_final:
                # Line is now sticky. Next task from this worker will get a new line.
                del self.active_workers[worker_id]

class WorkerState:
    CONTINUE = "CONTINUE"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    EXIT = "EXIT"

class StepResult:
    def __init__(self, display_text: str, state: str = WorkerState.CONTINUE, is_final: bool = False):
        self.display_text = display_text
        self.state = state
        self.is_final = is_final

class TuringTask:
    def __init__(self, name: str, steps: List[Callable[..., Any]]):
        self.name = name
        self.steps = steps

class TuringWorker:
    def __init__(self, worker_id: str, manager: MultiLineManager):
        self.worker_id = worker_id
        self.manager = manager

    def execute(self, task: TuringTask, **kwargs):
        for step_func in task.steps:
            try:
                result_gen = step_func(**kwargs)
            except Exception as e:
                self.manager.update(self.worker_id, f"Step launch failed: {e}", is_final=True)
                return WorkerState.ERROR
            
            # A generator usually has __next__ and __iter__
            is_gen = hasattr(result_gen, '__next__') and hasattr(result_gen, '__iter__')
            if is_gen:
                try:
                    for update in result_gen:
                        self.manager.update(self.worker_id, update.display_text, is_final=update.is_final)
                        if update.state in [WorkerState.EXIT, WorkerState.ERROR]:
                            return update.state
                except Exception as e:
                    self.manager.update(self.worker_id, f"Step execution failed: {e}", is_final=True)
                    return WorkerState.ERROR
            else:
                # result_gen is a single StepResult
                if result_gen is None: continue
                self.manager.update(self.worker_id, result_gen.display_text, is_final=result_gen.is_final)
                if result_gen.state in [WorkerState.EXIT, WorkerState.ERROR]:
                    return result_gen.state
                    
        return WorkerState.SUCCESS
