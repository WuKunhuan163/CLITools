import sys
import threading

class MultiLineManager:
    """
    Manages a 'Results' area (top, permanent) and an 'Active' area (bottom, erasable).
    Every update clears the active area and redraws all current workers.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.active_workers = {}  # worker_id -> current text
        self.worker_order = []    # List of worker_ids to maintain stable order
        self.last_height = 0      # Height of the active area last drawn

    def _clear_active_area(self):
        """Erases the active area completely and leaves cursor at the start of it."""
        if self.last_height > 0:
            # Move up to the start of the active area
            sys.stdout.write(f"\033[{self.last_height}A")
            # Clear everything from cursor to end of screen
            sys.stdout.write("\033[J")
            self.last_height = 0

    def update(self, worker_id: str, text: str, is_final: bool = False):
        with self.lock:
            if is_final:
                # 1. Clear active area
                self._clear_active_area()
                
                # 2. Print the final result (permanent)
                # It now appears immediately below the previous results
                sys.stdout.write(text + "\n")
                
                # 3. Remove from active tracking
                if worker_id in self.active_workers:
                    del self.active_workers[worker_id]
                    if worker_id in self.worker_order:
                        self.worker_order.remove(worker_id)
                
                # 4. Redraw remaining active workers
                self._draw_active_area()
                sys.stdout.flush()
                return

            # Active update
            if worker_id not in self.active_workers:
                self.worker_order.append(worker_id)
            
            self.active_workers[worker_id] = text
            
            # Redraw everything in the active area
            self._clear_active_area()
            self._draw_active_area()
            sys.stdout.flush()

    def _draw_active_area(self):
        """Prints all active workers and updates last_height."""
        lines_printed = 0
        for wid in self.worker_order:
            text = self.active_workers[wid]
            # Print the line and ensure we move to the next line
            # \r\033[K ensures we start at col 0 and clear any leftover chars
            sys.stdout.write(f"\r\033[K{text}\n")
            lines_printed += 1
        
        # Move cursor back up to the top of the active area
        if lines_printed > 0:
            sys.stdout.write(f"\033[{lines_printed}A")
        
        self.last_height = lines_printed

    def finalize(self):
        """Clear the active area and leave cursor at the end of the results."""
        with self.lock:
            self._clear_active_area()
            # No redraw. Cursor is now at the end of results.
            sys.stdout.flush()
