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
                # ~ECHO: Turn off echoing
                # ~ICANON: Turn off canonical mode (line buffering)
                new_settings[3] = new_settings[3] & ~termios.ECHO
                new_settings[3] = new_settings[3] & ~termios.ICANON
                
                if hasattr(termios, 'ECHOCTL'):
                    new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                
                termios.tcsetattr(self._fd, termios.TCSANOW, new_settings)
                
                self.running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._thread.start()
            except Exception:
                self.running = False
                self._ref_count -= 1

    def _capture_loop(self):
        """Internal loop to read and discard input."""
        while self.running and self._fd is not None:
            try:
                # Use select to wait for data with a timeout
                r, _, _ = select.select([self._fd], [], [], 0.1)
                if r:
                    # Read available bytes and store them
                    data = os.read(self._fd, 1024)
                    if data:
                        with self._lock:
                            self.captured_keys.append(data)
            except (OSError, ValueError):
                break
            except Exception:
                break

    def stop(self, force: bool = False):
        thread_to_join = None
        with self._lock:
            if not self.running:
                # Still decrement ref count if we are not running but ref count > 0
                if not force and self._ref_count > 0:
                    self._ref_count -= 1
                return
            
            if not force:
                self._ref_count -= 1
                if self._ref_count > 0:
                    return # Still in use elsewhere
            else:
                self._ref_count = 0
            
            self.running = False
            thread_to_join = self._thread
            self._thread = None
            
        # Join outside the lock to avoid deadlock with _capture_loop
        if thread_to_join:
            try:
                # Use a small timeout to avoid hanging the main thread on exit
                thread_to_join.join(timeout=0.1)
            except:
                pass
        
        # Restore settings
        if self._old_settings and self._fd is not None:
            try:
                import termios
                # Ensure original settings are restored to the FD
                # Use TCSAFLUSH to discard any unread input buffered during suppression
                termios.tcsetattr(self._fd, termios.TCSAFLUSH, self._old_settings)
            except Exception:
                pass
        
        # Clear old settings to indicate we are done
        self._old_settings = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Always call stop on exit. Reference counting handles nesting.
        self.stop()

# Global instance for easy access if needed, but per-instance usage preferred
_global_suppressor = None

def get_global_suppressor() -> KeyboardSuppressor:
    global _global_suppressor
    if _global_suppressor is None:
        _global_suppressor = KeyboardSuppressor()
        # Register atexit handler for the global suppressor
        import atexit
        def _cleanup():
            if _global_suppressor:
                _global_suppressor.stop(force=True)
        atexit.register(_cleanup)
    return _global_suppressor
