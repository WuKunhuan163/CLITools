import sys
import threading
import shutil
import re
import time
import unicodedata
from logic.utils import get_display_width as get_visible_len, truncate_to_display_width
from logic.config import get_global_config

def truncate_to_width(text, max_width):
    """Truncate string to visible width, adding ellipsis and resetting color."""
    if get_visible_len(text) <= max_width:
        return text
    return truncate_to_display_width(text, max_width - 3) + "...\033[0m"

def _get_configured_width():
    """Get the configured terminal width or the actual terminal size."""
    config_width = get_global_config("terminal_width")
    if config_width and isinstance(config_width, int):
        return config_width
    return shutil.get_terminal_size((80, 20)).columns

class Slot:
    def __init__(self, worker_id, text, is_final=False):
        self.worker_id = worker_id
        self.text = text
        self.is_final = is_final
        self.height = 1 # Physical height in lines

    def calculate_height(self, width):
        if not self.is_final:
            return 1
        v_len = get_visible_len(self.text)
        if v_len == 0: return 0
        return (v_len + width - 1) // width

class MultiLineManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.slots = [] # List of Slot objects
        self.worker_to_slot_idx = {} # worker_id -> index in self.slots
        self.last_width = _get_configured_width()
        self.last_resize_time = 0

    def _get_current_width(self):
        return _get_configured_width()

    def update(self, worker_id: str, text: str, is_final: bool = False):
        # Enforce single-line for active workers, allow multi-line for finalized
        processed_text = " | ".join([line.strip() for line in text.splitlines() if line.strip()])
        
        with self.lock:
            curr_width = self._get_current_width()
            now = time.time()
            
            # 1. Handle resize
            if curr_width != self.last_width and now - self.last_resize_time > 1.0:
                self._reflow(curr_width)
                self.last_width = curr_width
                self.last_resize_time = now

            # 2. Get or create slot
            if worker_id not in self.worker_to_slot_idx:
                slot_idx = len(self.slots)
                self.worker_to_slot_idx[worker_id] = slot_idx
                new_slot = Slot(worker_id, processed_text, is_final)
                self.slots.append(new_slot)
                
                # Print new slot at bottom
                display_text = processed_text
                if not is_final:
                    display_text = truncate_to_width(processed_text, curr_width)
                
                new_slot.height = new_slot.calculate_height(curr_width)
                
                # If finalized, it might take multiple lines
                sys.stdout.write(f"\r\033[K{display_text}\n")
                if is_final:
                    del self.worker_to_slot_idx[worker_id]
                
                sys.stdout.flush()
                return

            # 3. Update existing slot
            slot_idx = self.worker_to_slot_idx[worker_id]
            slot = self.slots[slot_idx]
            
            old_height = slot.height
            slot.text = processed_text
            slot.is_final = is_final
            new_height = slot.calculate_height(curr_width)
            slot.height = new_height

            # If height changed or finalized, we might need to redraw everything below
            if new_height != old_height or is_final:
                self._redraw_from(slot_idx, curr_width)
            else:
                # Simple jump and overwrite
                dist_to_start = sum(s.height for s in self.slots[slot_idx+1:])
                total_up = dist_to_start + old_height
                
                display_text = truncate_to_width(processed_text, curr_width)
                
                sys.stdout.write(f"\033[{total_up}A\r")
                sys.stdout.write(f"\033[K{display_text}")
                sys.stdout.write(f"\033[{total_up}B\r")
            
            if is_final:
                del self.worker_to_slot_idx[worker_id]
            
            sys.stdout.flush()

    def _reflow(self, new_width):
        """Recalculate all heights and redraw from the first changed line."""
        if not self.slots: return
        
        # We redraw from the first slot that is still active or whose height changed
        # For simplicity and robustness on resize, we redraw from the first active slot
        first_active = min(self.worker_to_slot_idx.values()) if self.worker_to_slot_idx else len(self.slots)
        
        # Calculate new heights
        for slot in self.slots:
            slot.height = slot.calculate_height(new_width)
            
        self._redraw_from(0, new_width) # On resize, redraw everything to be sure

    def _redraw_from(self, start_idx, width):
        """Redraw all slots from start_idx to bottom."""
        # 1. Jump up to the start of start_idx
        total_height_below = sum(s.height for s in self.slots[start_idx:])
        if total_height_below > 0:
            sys.stdout.write(f"\033[{total_height_below}A\r")
        
        # 2. Redraw each slot
        for i in range(start_idx, len(self.slots)):
            slot = self.slots[i]
            # Clear old lines if height decreased? 
            # Actually \033[J clears everything below cursor.
            sys.stdout.write("\033[J") 
            
            display_text = slot.text
            if not slot.is_final:
                display_text = truncate_to_width(slot.text, width)
            
            sys.stdout.write(f"{display_text}\n")
            
        # Cursor is now at the logical bottom
        sys.stdout.flush()

    def finalize(self):
        """Ensure cursor is at the bottom and all active slots are closed."""
        pass
