import sys
import threading

class MultiLineManager:
    """
    Manages multiple lines in the terminal.
    A worker 'claims' a new line when it starts a task.
    Updates jump to that specific line.
    When a task finishes (is_final=True), the line becomes permanent 
    and the worker will claim a DIFFERENT line for its next task.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.active_slots = {}  # worker_id -> slot_index
        self.slot_heights = []  # list of int (height of each slot)
        self.total_logical_height = 0

    def update(self, worker_id: str, text: str, is_final: bool = False):
        with self.lock:
            # 1. Claim a new line if worker is starting a new task
            if worker_id not in self.active_slots:
                slot_idx = len(self.slot_heights)
                self.active_slots[worker_id] = slot_idx
                
                # Print the new content at the current bottom
                lines = text.split('\n')
                h = len(lines)
                self.slot_heights.append(h)
                self.total_logical_height += h
                
                for line in lines:
                    sys.stdout.write(f"\r\033[K{line}\n")
                
                # If it was a one-shot final update, immediately release the slot
                if is_final:
                    del self.active_slots[worker_id]
                
                sys.stdout.flush()
                return

            # 2. Update existing active task slot
            slot_idx = self.active_slots[worker_id]
            old_h = self.slot_heights[slot_idx]
            
            # Distance from logical bottom to the start of this task's slot
            dist_to_start = sum(self.slot_heights[slot_idx+1:])
            total_up = dist_to_start + old_h
            
            # Jump to slot
            sys.stdout.write(f"\033[{total_up}A\r")
            
            # Overwrite
            lines = text.split('\n')
            new_h = len(lines)
            
            for i in range(max(old_h, new_h)):
                if i < new_h:
                    sys.stdout.write(f"\033[K{lines[i]}\n")
                else:
                    sys.stdout.write("\033[K\n")
            
            # Adjust logical bottom if height changed
            if new_h != old_h:
                diff = new_h - old_h
                self.slot_heights[slot_idx] = new_h
                self.total_logical_height += diff
                dist_to_start = sum(self.slot_heights[slot_idx+1:])
            
            # Jump back to logical bottom
            if dist_to_start > 0:
                sys.stdout.write(f"\033[{dist_to_start}B\r")
            
            # 3. If finished, release this worker's claim on the slot
            # The slot stays in slot_heights so future workers claim lines ABOVE it (no, BELOW it).
            if is_final:
                del self.active_slots[worker_id]
            
            sys.stdout.flush()

    def finalize(self):
        """Cursor is already at the logical bottom."""
        pass
