"""Cross-platform utilities for OS-specific operations.

Provides a registry-based dispatch system for platform-specific code paths.
Supports macOS, Linux, Windows, with fallback for unknown platforms.

Usage::

    from logic.utils.platform import current_platform, find_chrome_binary, launch_chrome_cdp

    plat = current_platform()          # "darwin", "linux", "win32", "unknown"
    chrome = find_chrome_binary()      # str path or None
    ok = launch_chrome_cdp(port=9222)  # True if Chrome launched with CDP
"""
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Callable, Dict, Any


def current_platform() -> str:
    """Return normalized platform identifier: 'darwin', 'linux', 'win32', or 'unknown'."""
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "win32":
        return "win32"
    return "unknown"


# ---------------------------------------------------------------------------
# Platform dispatch registry
# ---------------------------------------------------------------------------

_registry: Dict[str, Dict[str, Callable]] = {}


def register_handler(operation: str, platform: str, handler: Callable):
    """Register a platform-specific handler for an operation.

    Parameters
    ----------
    operation : str
        Operation name (e.g. "find_chrome", "launch_chrome").
    platform : str
        Platform key: "darwin", "linux", "win32", or "fallback".
    handler : callable
        Function to call for this operation on this platform.
    """
    _registry.setdefault(operation, {})[platform] = handler


def dispatch(operation: str, *args, **kwargs) -> Any:
    """Dispatch an operation to the appropriate platform handler.

    Tries: current platform -> "fallback" -> raises NotImplementedError.
    """
    handlers = _registry.get(operation, {})
    plat = current_platform()
    handler = handlers.get(plat) or handlers.get("fallback")
    if handler is None:
        raise NotImplementedError(
            f"No handler for '{operation}' on platform '{plat}'"
        )
    return handler(*args, **kwargs)


# ---------------------------------------------------------------------------
# Chrome binary discovery (per-platform)
# ---------------------------------------------------------------------------

def _find_chrome_darwin() -> Optional[str]:
    app = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    return app if Path(app).exists() else None


def _find_chrome_linux() -> Optional[str]:
    for binary in ["google-chrome", "google-chrome-stable",
                   "chromium-browser", "chromium"]:
        path = shutil.which(binary)
        if path:
            return path
    return None


def _find_chrome_win32() -> Optional[str]:
    for template in [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
    ]:
        expanded = os.path.expandvars(template)
        if Path(expanded).exists():
            return expanded
    return None


def _find_chrome_fallback() -> Optional[str]:
    return shutil.which("google-chrome") or shutil.which("chromium")


register_handler("find_chrome", "darwin", _find_chrome_darwin)
register_handler("find_chrome", "linux", _find_chrome_linux)
register_handler("find_chrome", "win32", _find_chrome_win32)
register_handler("find_chrome", "fallback", _find_chrome_fallback)


def find_chrome_binary() -> Optional[str]:
    """Find Chrome executable on the current platform."""
    return dispatch("find_chrome")


# ---------------------------------------------------------------------------
# Chrome CDP launch (per-platform)
# ---------------------------------------------------------------------------

_CDP_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "chrome-cdp-profile")


def _launch_chrome_darwin(port: int = 9222, url: str = "") -> bool:
    os.makedirs(_CDP_PROFILE_DIR, exist_ok=True)
    chrome = find_chrome_binary()
    if not chrome:
        return False
    cmd = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={_CDP_PROFILE_DIR}",
        "--remote-allow-origins=*",
        "--no-first-run",
    ]
    if url:
        cmd.append(url)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def _launch_chrome_linux(port: int = 9222, url: str = "") -> bool:
    os.makedirs(_CDP_PROFILE_DIR, exist_ok=True)
    chrome = find_chrome_binary()
    if not chrome:
        return False
    cmd = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={_CDP_PROFILE_DIR}",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-sandbox",
    ]
    if url:
        cmd.append(url)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def _launch_chrome_win32(port: int = 9222, url: str = "") -> bool:
    os.makedirs(_CDP_PROFILE_DIR, exist_ok=True)
    chrome = find_chrome_binary()
    if not chrome:
        return False
    cmd = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={_CDP_PROFILE_DIR}",
        "--remote-allow-origins=*",
        "--no-first-run",
    ]
    if url:
        cmd.append(url)
    subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )
    return True


register_handler("launch_chrome", "darwin", _launch_chrome_darwin)
register_handler("launch_chrome", "linux", _launch_chrome_linux)
register_handler("launch_chrome", "win32", _launch_chrome_win32)


def launch_chrome_cdp(port: int = 9222, url: str = "") -> bool:
    """Launch Chrome with CDP enabled on the current platform.

    Returns True if the launch command was issued (not necessarily that CDP is ready).
    Caller should poll ``is_chrome_cdp_available()`` after this call.
    """
    try:
        return dispatch("launch_chrome", port=port, url=url)
    except NotImplementedError:
        return False


# ---------------------------------------------------------------------------
# Chrome cleanup (per-platform)
# ---------------------------------------------------------------------------

def _cleanup_chrome_darwin() -> dict:
    results = {"killed": 0, "locks_removed": 0, "errors": []}
    try:
        r = subprocess.run(["pkill", "-9", "-f", "Google Chrome"],
                           capture_output=True, timeout=10)
        if r.returncode == 0:
            results["killed"] += 1
    except Exception as e:
        results["errors"].append(str(e))

    import time
    time.sleep(2)

    lock_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = lock_dir / lock_name
        if lock_path.exists():
            try:
                lock_path.unlink()
                results["locks_removed"] += 1
            except Exception as e:
                results["errors"].append(f"Failed to remove {lock_name}: {e}")

    return results


def _cleanup_chrome_linux() -> dict:
    results = {"killed": 0, "locks_removed": 0, "errors": []}
    try:
        r = subprocess.run(["pkill", "-9", "-f", "chrome"],
                           capture_output=True, timeout=10)
        if r.returncode == 0:
            results["killed"] += 1
    except Exception as e:
        results["errors"].append(str(e))

    import time
    time.sleep(2)

    config_dir = Path.home() / ".config" / "google-chrome"
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        lock_path = config_dir / lock_name
        if lock_path.exists():
            try:
                lock_path.unlink()
                results["locks_removed"] += 1
            except Exception as e:
                results["errors"].append(f"Failed to remove {lock_name}: {e}")

    return results


def _cleanup_chrome_win32() -> dict:
    results = {"killed": 0, "locks_removed": 0, "errors": []}
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                       capture_output=True, timeout=10)
        results["killed"] += 1
    except Exception as e:
        results["errors"].append(str(e))
    return results


register_handler("cleanup_chrome", "darwin", _cleanup_chrome_darwin)
register_handler("cleanup_chrome", "linux", _cleanup_chrome_linux)
register_handler("cleanup_chrome", "win32", _cleanup_chrome_win32)


def cleanup_chrome() -> dict:
    """Kill all Chrome processes and remove lock files on the current platform.

    Returns dict with keys: killed, locks_removed, errors.
    """
    try:
        return dispatch("cleanup_chrome")
    except NotImplementedError:
        return {"killed": 0, "locks_removed": 0,
                "errors": [f"Unsupported platform: {current_platform()}"]}
