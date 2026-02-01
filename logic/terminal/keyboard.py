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
    """
    def __init__(self):
        self.captured_keys: List[bytes] = []
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._old_settings = None
        self._fd = sys.stdin.fileno() if sys.stdin.isatty() else None
        self._lock = threading.Lock()

    def start(self):
        if not self._fd or termios is None:
            return

        with self._lock:
            if self.running:
                return
            
            try:
                self._old_settings = termios.tcgetattr(self._fd)
                
                # Create new settings
                # 1. Disable ECHO (don't show typed characters)
                # 2. Disable ICANON (line buffering, get chars immediately)
                # 3. Keep ISIG enabled if we want Ctrl+C to still send SIGINT, 
                #    OR disable it to capture \x03 byte. 
                #    The user asked to suppress Ctrl+C visual effect but record it.
                #    Echoing '^C' is usually part of ECHO or ECHOCTL.
                new_settings = termios.tcgetattr(self._fd)
                new_settings[3] = new_settings[3] & ~termios.ECHO
                new_settings[3] = new_settings[3] & ~termios.ICANON
                
                # Optional: disable ECHOCTL to prevent '^C' showing up when ISIG is on
                if hasattr(termios, 'ECHOCTL'):
                    new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                
                termios.tcsetattr(self._fd, termios.TCSADRAIN, new_settings)
                
                self.running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._thread.start()
            except Exception:
                # If anything fails, don't leave the terminal in a broken state
                self.running = False

    def stop(self):
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            if self._thread:
                self._thread.join(timeout=0.5)
            
            if self._old_settings and self._fd:
                try:
                    termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_settings)
                except Exception:
                    pass
            self._old_settings = None

    def _capture_loop(self):
        """Background thread to read from stdin."""
        while self.running:
            try:
                # Use select to avoid blocking forever, allowing thread to exit
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
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

