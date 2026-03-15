"""Pre-flight check utilities for validating conditions before risky operations.

Usage::

    from logic.utils.preflight import preflight, check_command_exists, check_path_exists

    ok, failures = preflight([
        ("Chrome running", lambda: check_command_exists("google-chrome")),
        ("Output dir", lambda: check_path_exists("/tmp/output")),
        ("API key set", lambda: bool(os.environ.get("API_KEY"))),
    ])
    if not ok:
        for f in failures:
            print(f"  FAIL: {f}")
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, List, Sequence, Tuple, Union


CheckItem = Tuple[str, Callable[[], bool]]


def preflight(
    checks: Sequence[CheckItem],
) -> Tuple[bool, List[str]]:
    """Run a sequence of named checks.  Returns ``(all_ok, failures)``.

    Each check is a ``(name, callable)`` pair.  The callable should
    return a truthy value on success.  Exceptions are caught and
    treated as failures.
    """
    failures: List[str] = []
    for name, check in checks:
        try:
            if not check():
                failures.append(name)
        except Exception as exc:
            failures.append(f"{name}: {exc}")
    return len(failures) == 0, failures


def check_command_exists(cmd: str) -> bool:
    """Return True if *cmd* is available on PATH."""
    return shutil.which(cmd) is not None


def check_path_exists(path: Union[str, Path]) -> bool:
    """Return True if *path* exists on disk."""
    return Path(path).exists()


def check_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Return True if *port* is free to bind."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False
