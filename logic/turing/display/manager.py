import sys
import threading

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

