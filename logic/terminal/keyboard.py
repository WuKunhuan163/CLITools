import sys
import os
import threading
import select
import time
import signal
from typing import List, Optional

try:
    import termios
    import tty
except ImportError:
    termios = None
    tty = None

class KeyboardSuppressor:
    """
    Suppresses keyboard input echoing to the terminal.
    Uses reference counting to handle nested usage.
    """
    def __init__(self):
        self.running = False
        self._old_settings = None
        self._ref_count = 0
        self._fd = None
        
        # Try to get the terminal FD
        try:
            if sys.stdin and sys.stdin.isatty(): self._fd = sys.stdin.fileno()
            elif sys.stdout and sys.stdout.isatty(): self._fd = sys.stdout.fileno()
            elif sys.stderr and sys.stderr.isatty(): self._fd = sys.stderr.fileno()
        except: pass
        
        if self._fd is None:
            for name in ['/dev/tty', '/dev/console']:
                try:
                    f = open(name, 'rb+', buffering=0)
                    self._fd = f.fileno()
                    break
                except: continue
            
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
                new_settings = termios.tcgetattr(self._fd)
                
                # Keep ICANON ON and ISIG ON for standard Ctrl+C handling.
                # Just turn off ECHO and ECHOCTL to hide user input.
                new_settings[3] = new_settings[3] & ~termios.ECHO
                new_settings[3] = new_settings[3] | termios.ISIG
                if hasattr(termios, 'ECHOCTL'):
                    new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                
                termios.tcsetattr(self._fd, termios.TCSANOW, new_settings)
                self.running = True
            except Exception:
                self.running = False
                self._ref_count -= 1

    def stop(self, force: bool = False):
        with self._lock:
            if not self.running:
                if not force and self._ref_count > 0:
                    self._ref_count -= 1
                return
            
            if not force:
                self._ref_count -= 1
                if self._ref_count > 0:
                    return
            else:
                self._ref_count = 0
            
            self.running = False
            old_settings = self._old_settings
            self._old_settings = None
            
        if old_settings and self._fd is not None:
            try:
                # Use TCSAFLUSH to discard any unread input buffered during suppression
                termios.tcsetattr(self._fd, termios.TCSAFLUSH, old_settings)
            except Exception:
                pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

_global_suppressor = None

def get_global_suppressor() -> KeyboardSuppressor:
    global _global_suppressor
    if _global_suppressor is None:
        _global_suppressor = KeyboardSuppressor()
        import atexit
        def _cleanup():
            if _global_suppressor:
                _global_suppressor.stop(force=True)
        atexit.register(_cleanup)
    return _global_suppressor

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
