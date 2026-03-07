"""GCS API reconnection manager.

Tracks command execution count and duration. Triggers remount (API
reconnection) when thresholds are exceeded:
  1. Command count exceeds ``command_count_threshold``
  2. A single command exceeds ``duration_threshold_seconds``

The mechanism uses flag/lock files under ``data/run/`` to coordinate
between concurrent processes.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


_DEFAULT_COMMAND_COUNT_THRESHOLD = 50
_DEFAULT_DURATION_THRESHOLD_SECONDS = 300
_LOCK_EXPIRY_SECONDS = 300


def _run_dir(project_root: Path) -> Path:
    d = project_root / "tool" / "GOOGLE.GCS" / "data" / "run"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _counter_path(project_root: Path) -> Path:
    return _run_dir(project_root) / "reconnection_counter.json"


def _config_path(project_root: Path) -> Path:
    return _run_dir(project_root) / "reconnection_config.json"


def _flag_path(project_root: Path) -> Path:
    return _run_dir(project_root) / "remount_required.flag"


def _lock_path(project_root: Path) -> Path:
    return _run_dir(project_root) / "remount_in_progress.lock"


def get_thresholds(project_root: Path) -> Tuple[int, float]:
    """Return (command_count_threshold, duration_threshold_seconds)."""
    path = _config_path(project_root)
    if path.exists():
        try:
            with open(path, 'r') as f:
                cfg = json.load(f)
            return (
                cfg.get("command_count_threshold", _DEFAULT_COMMAND_COUNT_THRESHOLD),
                cfg.get("duration_threshold_seconds", _DEFAULT_DURATION_THRESHOLD_SECONDS),
            )
        except Exception:
            pass
    return _DEFAULT_COMMAND_COUNT_THRESHOLD, _DEFAULT_DURATION_THRESHOLD_SECONDS


def save_thresholds(project_root: Path, count: int, duration: float):
    path = _config_path(project_root)
    with open(path, 'w') as f:
        json.dump({"command_count_threshold": count,
                    "duration_threshold_seconds": duration}, f, indent=2)


def get_execution_counter(project_root: Path) -> Dict:
    path = _counter_path(project_root)
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"count": 0, "last_reset": None, "last_updated": None}


def increment_execution_counter(project_root: Path):
    counter = get_execution_counter(project_root)
    counter["count"] = counter.get("count", 0) + 1
    counter["last_updated"] = time.time()
    with open(_counter_path(project_root), 'w') as f:
        json.dump(counter, f, indent=2)


def reset_execution_counter(project_root: Path):
    counter = {"count": 0, "last_reset": time.time(), "last_updated": time.time()}
    with open(_counter_path(project_root), 'w') as f:
        json.dump(counter, f, indent=2)


def should_remount_before_command(project_root: Path) -> Tuple[bool, Optional[str]]:
    """Check if remount is needed BEFORE executing a command.

    Returns (needs_remount, reason).
    """
    if is_remount_flagged(project_root):
        flag = _read_flag(project_root)
        return True, flag.get("reason", "Remount flag set")

    count_thresh, _ = get_thresholds(project_root)
    counter = get_execution_counter(project_root)
    if counter.get("count", 0) >= count_thresh:
        return True, f"Command count ({counter['count']}) reached threshold ({count_thresh})"

    return False, None


def should_remount_after_command(project_root: Path, duration_seconds: float) -> Tuple[bool, Optional[str]]:
    """Check if remount is needed AFTER a command based on its duration.

    Returns (needs_remount, reason).
    """
    _, dur_thresh = get_thresholds(project_root)
    if duration_seconds > dur_thresh:
        return True, f"Command took {duration_seconds:.1f}s (threshold: {dur_thresh}s)"
    return False, None


def set_remount_required_flag(project_root: Path, reason: str):
    flag_data = {
        "created": time.time(),
        "reason": reason,
        "set_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(_flag_path(project_root), 'w') as f:
        json.dump(flag_data, f, indent=2)


def clear_remount_required_flag(project_root: Path):
    path = _flag_path(project_root)
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


def is_remount_flagged(project_root: Path) -> bool:
    return _flag_path(project_root).exists()


def _read_flag(project_root: Path) -> Dict:
    path = _flag_path(project_root)
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def acquire_remount_lock(project_root: Path, caller_info: str = "",
                         force: bool = False) -> bool:
    lock = _lock_path(project_root)
    if lock.exists() and not force:
        try:
            with open(lock, 'r') as f:
                data = json.load(f)
            acquired = data.get("acquired_at", 0)
            if time.time() - acquired > _LOCK_EXPIRY_SECONDS:
                lock.unlink()
            else:
                pid = data.get("pid")
                if pid and _pid_alive(pid):
                    return False
                lock.unlink()
        except Exception:
            pass

    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        data = json.dumps({
            "pid": os.getpid(),
            "caller": caller_info,
            "acquired_at": time.time(),
        })
        os.write(fd, data.encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def release_remount_lock(project_root: Path):
    lock = _lock_path(project_root)
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass


def is_remount_in_progress(project_root: Path) -> bool:
    lock = _lock_path(project_root)
    if not lock.exists():
        return False
    try:
        with open(lock, 'r') as f:
            data = json.load(f)
        acquired = data.get("acquired_at", 0)
        if time.time() - acquired > _LOCK_EXPIRY_SECONDS:
            lock.unlink()
            return False
        pid = data.get("pid")
        if pid and not _pid_alive(pid):
            lock.unlink()
            return False
        return True
    except Exception:
        return False


def wait_for_remount_completion(project_root: Path,
                                max_wait: float = 120) -> bool:
    """Block until remount completes or timeout. Returns True if completed."""
    start = time.time()
    while time.time() - start < max_wait:
        if not is_remount_in_progress(project_root):
            return True
        time.sleep(2)
    return False


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except ImportError:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
