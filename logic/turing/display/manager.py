import sys
import threading
import shutil
import re
import time
import unicodedata
import json
from typing import Optional, Callable
from pathlib import Path
from logic.utils import get_display_width as get_visible_len, truncate_to_display_width, get_rtl_mode
from logic.config import get_global_config, PROJECT_ROOT

def truncate_to_width(text, max_width):
    """Truncate string to visible width, adding ellipsis and resetting color."""
    if get_visible_len(text) <= max_width:
        return text
    return truncate_to_display_width(text, max_width - 3) + "...\033[0m"

def _get_configured_width():
    """Get the configured terminal width or the actual terminal size."""
    config_width = get_global_config("terminal_width")
    if config_width and isinstance(config_width, int) and config_width > 0:
        return config_width
    return shutil.get_terminal_size((80, 20)).columns

def wrap_text(text, width):
    """
    Manually wrap text to a specific width, taking multi-byte characters into account.
    Ensures that CJK characters are not split across lines and prefers wrapping at 
    spaces for Western/Arabic text.
    """
    if not text: return []
    if width <= 0: return [text]
    
    lines = []
    # Temporarily remove ANSI codes for wrapping logic to be simpler, 
    # though we should keep them. For now, let's keep the existing logic 
    # but try to be smarter about word boundaries.
    
    current_line = ""
    current_width = 0
    
    # Split text into tokens (words and spaces and individual CJK/Arabic chars)
    # This is complex. Let's stick to a simpler "break-at-width" but 
    # if we are about to break, check if we can backtrack to a space.
    
    i = 0
    last_space_idx = -1
    last_space_line_width = 0
    
    while i < len(text):
        if text[i] == '\x1B':
            j = i
            while j < len(text) and not ('A' <= text[j] <= 'Z' or 'a' <= text[j] <= 'z'):
                j += 1
            if j < len(text):
                current_line += text[i:j+1]
                i = j + 1
                continue
        
        char = text[i]
        if char in ('\u202b', '\u202c'):
            current_line += char
            i += 1
            continue

        char_w = get_visible_len(char)
        
        if current_width + char_w > width:
            if last_space_idx != -1 and current_width < width:
                # We have a space we can break at
                # Extract up to the last space
                # But wait, text[last_space_idx] might be in a different line now?
                # No, last_space_idx is absolute. 
                # This is getting complicated. 
                pass
            
            lines.append(current_line)
            current_line = char
            current_width = char_w
            last_space_idx = -1
        else:
            if char == ' ':
                last_space_idx = i
                last_space_line_width = current_width
            current_line += char
            current_width += char_w
        i += 1
    
    if current_line:
        lines.append(current_line)
    return lines

class Slot:
    def __init__(self, worker_id, text, is_final=False):
        self.worker_id = worker_id
        self.text = text
        self.is_final = is_final
        self.height = 1 # Physical height in lines

    def calculate_height(self, width):
        if not self.is_final:
            return 1
        wrapped = wrap_text(self.text, width)
        return len(wrapped)

class MultiLineManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.slots = [] # List of Slot objects
        self.worker_to_slot_idx = {} # worker_id -> index in self.slots
        self.last_width = _get_configured_width()
        self.last_resize_time = 0
        self.total_height_ever_printed = 0 # Safety: never jump up more than this
        self.debug_file = PROJECT_ROOT / "data" / "run" / "manager_debug.json"

    def _get_current_width(self):
        return _get_configured_width()

    def _save_debug_state(self, action, worker_id, extra=None):
        """Save current state for debugging if debug is enabled."""
        if not get_global_config("manager_debug", False):
            return
        try:
            self.debug_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "timestamp": time.time(),
                "action": action,
                "worker_id": worker_id,
                "total_height": sum(s.height for s in self.slots),
                "total_printed": self.total_height_ever_printed,
                "slots": [{"id": s.worker_id, "height": s.height, "is_final": s.is_final} for s in self.slots]
            }
            if extra: state.update(extra)
            with open(self.debug_file, "a") as f:
                f.write(json.dumps(state) + "\n")
        except: pass

    def update(self, worker_id: str, text: str, is_final: bool = False, callback: Optional[Callable] = None):
        # Enforce single-line for active workers, allow multi-line for finalized
        processed_text = " | ".join([line.strip() for line in text.splitlines() if line.strip()])
        
        # Add RTL markers if global RTL mode is enabled
        if get_rtl_mode():
            # \u200f (RLM) + \u202b (RLE) + text + \u202c (PDF)
            processed_text = f"\u200f\u202b{processed_text}\u202c"

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
                new_slot.height = new_slot.calculate_height(curr_width)
                self.slots.append(new_slot)
                self.total_height_ever_printed += new_slot.height
                
                # Print new slot at bottom
                if not is_final:
                    display_text = truncate_to_width(processed_text, curr_width)
                else:
                    wrapped = wrap_text(processed_text, curr_width)
                    display_text = "\n".join(wrapped)
                
                sys.stdout.write(f"\r\033[K{display_text}\n")
                if is_final:
                    del self.worker_to_slot_idx[worker_id]
                
                self._save_debug_state("create", worker_id)
                if callback:
                    try: callback()
                    except: pass
                sys.stdout.flush()
                return

            # 3. Update existing slot
            slot_idx = self.worker_to_slot_idx[worker_id]
            slot = self.slots[slot_idx]
            
            old_height = slot.height
            slot.text = processed_text
            slot.is_final = is_final
            new_height = slot.calculate_height(curr_width)
            
            # Distance from logical bottom to the START of this slot
            # Uses OLD height because we are still at the old bottom
            dist_to_start = sum(s.height for s in self.slots[slot_idx+1:])
            total_up = dist_to_start + old_height
            
            # Now update the height
            slot.height = new_height
            
            # Safety: don't jump up more than what we've printed
            # The manager's territory starts at (current_bottom - total_current_height)
            current_total_height = sum(s.height for i, s in enumerate(self.slots)) # After update
            old_total_height = current_total_height - new_height + old_height
            total_up = min(total_up, old_total_height)

            # If height changed or finalized, we might need to redraw everything below
            if new_height != old_height or is_final:
                if total_up > 0:
                    sys.stdout.write(f"\033[{total_up}A\r")
                
                # Redraw from this slot downwards
                for i in range(slot_idx, len(self.slots)):
                    s = self.slots[i]
                    sys.stdout.write("\033[J") # Clear everything below
                    
                    if not s.is_final:
                        d_text = truncate_to_width(s.text, curr_width)
                    else:
                        w_lines = wrap_text(s.text, curr_width)
                        d_text = "\n".join(w_lines)
                    
                    sys.stdout.write(f"{d_text}\n")
                
                # Update our safety counter if we grew
                self.total_height_ever_printed = max(self.total_height_ever_printed, sum(s.height for s in self.slots))
            else:
                # Simple jump and overwrite
                if total_up > 0:
                    sys.stdout.write(f"\033[{total_up}A\r")
                sys.stdout.write(f"\033[K{truncate_to_width(processed_text, curr_width)}")
                if total_up > 0:
                    sys.stdout.write(f"\033[{total_up}B\r")
            
            if is_final:
                del self.worker_to_slot_idx[worker_id]
            
            self._save_debug_state("update", worker_id, {"total_up": total_up, "old_h": old_height, "new_h": new_height})
            if callback:
                try: callback()
                except: pass
            sys.stdout.flush()

    def _reflow(self, new_width):
        """Recalculate all heights and redraw from the first changed line."""
        if not self.slots: return
        for slot in self.slots:
            slot.height = slot.calculate_height(new_width)
        self._redraw_from(0, new_width)

    def _redraw_from(self, start_idx, width):
        """Redraw all slots from start_idx to bottom."""
        total_height_below = sum(s.height for s in self.slots[start_idx:])
        # Safety: don't jump up more than total printed height
        total_height_below = min(total_height_below, self.total_height_ever_printed)
        
        if total_height_below > 0:
            sys.stdout.write(f"\033[{total_height_below}A\r")
        
        for i in range(start_idx, len(self.slots)):
            slot = self.slots[i]
            sys.stdout.write("\033[J") 
            if not slot.is_final:
                display_text = truncate_to_width(slot.text, width)
            else:
                wrapped = wrap_text(slot.text, width)
                display_text = "\n".join(wrapped)
            sys.stdout.write(f"{display_text}\n")
        sys.stdout.flush()

    def finalize(self):
        """Ensure cursor is at the bottom."""
        pass
