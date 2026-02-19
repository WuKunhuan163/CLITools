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
        
        # Priority list for finding a TTY
        sources = []
        try:
            if sys.stdin and sys.stdin.isatty(): sources.append(sys.stdin.fileno())
            if sys.stdout and sys.stdout.isatty(): sources.append(sys.stdout.fileno())
            if sys.stderr and sys.stderr.isatty(): sources.append(sys.stderr.fileno())
        except: pass
        
        for fd in sources:
            if fd is not None:
                self._fd = fd
                break
        
        if self._fd is None:
            for name in ['/dev/tty', '/dev/console']:
                try:
                    self._tty_f = open(name, 'rb+', buffering=0)
                    self._fd = self._tty_f.fileno()
                    break
                except: continue
            
        self._lock = threading.Lock()

    def start(self):
        if self._fd is None or termios is None:
            with open("/tmp/suppressor.log", "a") as f:
                f.write(f"[{time.time()}] START early return: fd={self._fd}, termios={termios is not None}, stdin_isatty={sys.stdin.isatty() if sys.stdin else 'N/A'}\n")
                f.flush()
            return

        with self._lock:
            self._ref_count += 1
            with open("/tmp/suppressor.log", "a") as f:
                f.write(f"[{time.time()}] START call. ref_count={self._ref_count}, running={self.running}\n")
                f.flush()
                
            if self.running:
                return
            
            try:
                self._old_settings = termios.tcgetattr(self._fd)
                
                # Create new settings
                new_settings = termios.tcgetattr(self._fd)
                # ~ECHO: Turn off echoing
                # ~ICANON: Turn off canonical mode (line buffering)
                # ~ISIG: Turn off signal generation (Ctrl+C becomes a normal byte 0x03)
                new_settings[3] = new_settings[3] & ~termios.ECHO
                new_settings[3] = new_settings[3] & ~termios.ICANON
                new_settings[3] = new_settings[3] & ~termios.ISIG
                
                if hasattr(termios, 'ECHOCTL'):
                    new_settings[3] = new_settings[3] & ~termios.ECHOCTL
                
                termios.tcsetattr(self._fd, termios.TCSANOW, new_settings)
                
                self.running = True
                self._thread = threading.Thread(target=self._capture_loop, daemon=True)
                self._thread.start()
                with open("/tmp/suppressor.log", "a") as f:
                    f.write(f"[{time.time()}] Suppressor actually STARTED on fd {self._fd}\n")
                    f.flush()
            except Exception as e:
                with open("/tmp/suppressor.log", "a") as f:
                    f.write(f"[{time.time()}] START ERROR: {str(e)}\n")
                    f.flush()
                self.running = False
                self._ref_count -= 1

    def _capture_loop(self):
        """Internal loop to read and discard input."""
        import signal
        while self.running and self._fd is not None:
            try:
                # Use select to wait for data with a timeout
                r, _, _ = select.select([self._fd], [], [], 0.1)
                if r:
                    # Read available bytes and store them
                    data = os.read(self._fd, 1024)
                    if data:
                        # If ISIG is off, we must manually detect Ctrl+C (0x03)
                        if b'\x03' in data:
                            with open("/tmp/suppressor.log", "a") as f:
                                f.write(f"[{time.time()}] MANUAL Ctrl+C DETECTED in capture loop\n")
                                f.flush()
                            # Trigger SIGINT in the main thread
                            os.kill(os.getpid(), signal.SIGINT)
                            
                        with self._lock:
                            self.captured_keys.append(data)
            except (OSError, ValueError):
                break
            except Exception:
                break

    def stop(self, force: bool = False):
        thread_to_join = None
        old_settings = None
        
        with self._lock:
            with open("/tmp/suppressor.log", "a") as f:
                f.write(f"[{time.time()}] STOP call. force={force}, ref_count={self._ref_count}, running={self.running}\n")
                f.flush()
                
            if not self.running:
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
            
            # Take the settings out so we only restore once
            old_settings = self._old_settings
            self._old_settings = None
            
        # Restore settings immediately to unlock the terminal
        if old_settings and self._fd is not None:
            try:
                import termios
                # Use TCSAFLUSH to discard any unread input buffered during suppression
                termios.tcsetattr(self._fd, termios.TCSAFLUSH, old_settings)
                with open("/tmp/suppressor.log", "a") as f:
                    f.write(f"[{time.time()}] Suppressor actually RESTORED settings on fd {self._fd}\n")
                    f.flush()
            except Exception as e:
                with open("/tmp/suppressor.log", "a") as f:
                    f.write(f"[{time.time()}] RESTORE ERROR: {str(e)}\n")
                    f.flush()
                pass
        else:
            with open("/tmp/suppressor.log", "a") as f:
                f.write(f"[{time.time()}] STOP skip restore: settings={old_settings is not None}, fd={self._fd}\n")
                f.flush()
        
        # Join thread afterwards
        if thread_to_join:
            try:
                # Use a larger timeout for force stop, but still don't block forever
                thread_to_join.join(timeout=0.5 if force else 0.1)
            except:
                pass

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
