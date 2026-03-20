"""Session logging and debug logging utilities."""
import os
import sys
import time
from pathlib import Path
from logic.utils.cleanup import cleanup_old_files


class SessionLogger:
    """Per-invocation log file that accumulates timestamped entries.
    
    Creates one log file per tool session (log_YYYYMMDD_HHMMSS.log) in the
    given directory. Runs cleanup_old_files on initialization to cap total
    log files at `limit` (default 64, deleting half when exceeded).
    
    Usage:
        logger = SessionLogger(Path("tool/FOO/data/log"))
        logger.write("Download started", extra="url=https://...")
        logger.write("Download complete")
    """
    def __init__(self, log_dir: Path, limit: int = 64, prefix: str = "log"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        pid = os.getpid()
        self.log_file = self.log_dir / f"{prefix}_{ts}_{pid}.log"
        self._started = False
        cleanup_old_files(self.log_dir, f"{prefix}_*.log", limit=limit)

    def write(self, message: str, extra: str = None, include_stack: bool = True):
        """Append a timestamped entry to the session log file."""
        try:
            import traceback as tb
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            parts = [f"[{ts}] {message}"]
            if extra:
                parts.append(f"  detail: {extra}")
            if include_stack:
                frames = tb.extract_stack()
                relevant = [f for f in frames[:-1]
                            if "/logic/tool/base.py" not in f.filename
                            and "/logic/utils/" not in f.filename][-3:]
                if relevant:
                    brief = " -> ".join(
                        f"{Path(f.filename).name}:{f.lineno}({f.name})"
                        for f in relevant
                    )
                    parts.append(f"  stack: {brief}")
            entry = "\n".join(parts) + "\n"
            with open(self.log_file, "a", encoding="utf-8") as f:
                if not self._started:
                    f.write(f"# Session started at {ts}\n")
                    f.write(f"# Command: {' '.join(sys.argv)}\n\n")
                    self._started = True
                f.write(entry)
                f.flush()
        except Exception:
            pass

    def write_exception(self, error: Exception, context: str = ""):
        """Write a full exception traceback to the session log."""
        try:
            import traceback as tb
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"[{ts}] EXCEPTION: {context or type(error).__name__}: {error}"]
            lines.append(f"  traceback:\n{''.join(tb.format_exception(type(error), error, error.__traceback__))}")
            with open(self.log_file, "a", encoding="utf-8") as f:
                if not self._started:
                    f.write(f"# Session started at {ts}\n")
                    f.write(f"# Command: {' '.join(sys.argv)}\n\n")
                    self._started = True
                f.write("\n".join(lines) + "\n")
                f.flush()
        except Exception:
            pass

    @property
    def path(self) -> Path:
        return self.log_file


def log_debug(msg):
    """Log a message with a timestamp to /tmp/ait_debug.log."""
    try:
        with open("/tmp/ait_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.time()}] {msg}\n")
            f.flush()
    except:
        pass
