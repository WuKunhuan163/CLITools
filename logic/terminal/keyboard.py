import sys
import os
import threading
import select
import time
from typing import List, Optional

# Standard Unix terminal modules
try:
    import termios
    import tty
except ImportError:
    # Windows fallback (minimal)
    termios = None
    tty = None

class KeyboardSuppressor:
    """
    Suppresses keyboard input echoing to the terminal while recording it.
    Useful for protecting erasable status lines from being broken by user input.
    Uses reference counting to handle nested or concurrent usage.
    """
    def __init__(self):
        self.captured_keys: List[bytes] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._old_settings = None
        self._ref_count = 0
        
        # Try to get the terminal FD
        self._fd = None
        self._tty_f = None
        try:
            if sys.stdin.isatty():
                self._fd = sys.stdin.fileno()
            else:
                # Try opening /dev/tty directly
                self._tty_f = open('/dev/tty', 'rb', buffering=0)
                self._fd = self._tty_f.fileno()
        except:
            self._fd = None
            
        self._lock = threading.Lock()

    def start(self):
        if self._fd is None or termios is None:
            return

        with self._lock:
            self._ref_count += 1
            if self.running:
                return
            
            try:
                self._old_settings = termios.tcgetattr(self._fd)
                
                # Create new settings
                new_settings = termios.tcgetattr(self._fd)
                new_settings[3] = new_settings[3] & ~termios.ECHO
                new_settings[3] = new_settings[3] & ~termios.ICANON
                
                if hasattr(termios, 'ECHOCTL'):
                    new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                
                termios.tcsetattr(self._fd, termios.TCSADRAIN, new_settings)
                
                self.running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._thread.start()
            except Exception:
                self.running = False
                self._ref_count -= 1

    def stop(self):
        thread_to_join = None
        with self._lock:
            if not self.running:
                return
            
            self._ref_count -= 1
            if self._ref_count > 0:
                return # Still in use elsewhere
            
            self.running = False
            thread_to_join = self._thread
            self._thread = None
            
        # Join outside the lock to avoid deadlock with _capture_loop
        if thread_to_join:
            thread_to_join.join(timeout=0.5)
        
        # Restore settings
        if self._old_settings and self._fd is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass
        
        if hasattr(self, '_tty_f') and self._tty_f:
            try:
                self._tty_f.close()
            except:
                pass
                
        self._old_settings = None

    def _capture_loop(self):
        """Background thread to read from stdin or /dev/tty."""
        if self._fd is None:
            return

        while self.running:
            try:
                # Use select to avoid blocking forever, allowing thread to exit
                r, _, _ = select.select([self._fd], [], [], 0.1)
                if r:
                    # Read available bytes. We use os.read for raw bytes.
                    data = os.read(self._fd, 1024)
                    if data:
                        with self._lock:
                            self.captured_keys.append(data)
            except (IOError, EOFError):
                break
            except Exception:
                break

    def get_captured_raw(self) -> List[bytes]:
        with self._lock:
            return list(self.captured_keys)

    def get_captured_text(self) -> str:
        """Joins captured bytes into a single string if possible."""
        with self._lock:
            parts = []
            for b in self.captured_keys:
                try:
                    parts.append(b.decode('utf-8', errors='replace'))
                except:
                    parts.append(repr(b))
            return "".join(parts)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Global instance for easy access if needed, but per-instance usage preferred
_global_suppressor = None

def get_global_suppressor() -> KeyboardSuppressor:
    global _global_suppressor
    if _global_suppressor is None:
        _global_suppressor = KeyboardSuppressor()
    return _global_suppressor

