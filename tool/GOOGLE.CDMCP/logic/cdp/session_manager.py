"""CDMCP Session Manager — Manages named sessions with lifetime tabs.

Each session:
  - Has a unique name and a boot URL
  - Opens a dedicated Chrome tab as its "lifetime" anchor
  - Automatically re-opens the tab if it's closed
  - Times out after a configurable period of inactivity (default 24h)
  - Tracks its CDP session for overlay and interaction operations
"""

import json
import time
import threading
import datetime
import uuid
import importlib.util
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from logic.chrome.session import (
    CDPSession, CDP_PORT, is_chrome_cdp_available, list_tabs, find_tab, open_tab, close_tab,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_SESSION_DIR = _TOOL_DIR / "data" / "sessions"
_REPORT_DIR = _TOOL_DIR / "data" / "report"
_PROJECT_ROOT = _TOOL_DIR.parent.parent

DEFAULT_TIMEOUT_SEC = 86400  # 24 hours


def _find_project_python() -> str:
    """Find the project's default Python with dependencies installed."""
    import sys as _sys
    tool_json = _PROJECT_ROOT / "tool" / "PYTHON" / "tool.json"
    if tool_json.exists():
        try:
            with open(tool_json) as f:
                cfg = json.load(f)
            default_ver = cfg.get("default_version", "")
            if default_ver:
                candidate = _PROJECT_ROOT / "tool" / "PYTHON" / "data" / "install" / default_ver / "install" / "bin" / "python3"
                if candidate.exists():
                    return str(candidate)
        except Exception:
            pass
    install_dir = _PROJECT_ROOT / "tool" / "PYTHON" / "data" / "install"
    for py in sorted(install_dir.glob("*/install/bin/python3")):
        return str(py)
    return _sys.executable


def _now_ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log_session(action: str, session_name: str, detail: str = ""):
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _REPORT_DIR / "session_log.txt"
    line = f"[{_now_ts()}] {action} | session={session_name}"
    if detail:
        line += f" | {detail}"
    try:
        with open(log_file, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


_CHROME_DOWNLOAD_URL = "https://www.google.com/chrome/"
_CHROME_PROFILE_DIR = Path.home() / "ChromeDebugProfile"


def _find_chrome_binary() -> Optional[str]:
    """Find the Chrome executable path, or None if not installed."""
    import sys as _sys
    if _sys.platform == "darwin":
        app = "/Applications/Google Chrome.app"
        if Path(app).exists():
            return app
    elif _sys.platform.startswith("linux"):
        import shutil
        for binary in ["google-chrome", "google-chrome-stable",
                       "chromium-browser", "chromium"]:
            path = shutil.which(binary)
            if path:
                return path
    elif _sys.platform == "win32":
        import os
        for template in [
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
        ]:
            expanded = os.path.expandvars(template)
            if Path(expanded).exists():
                return expanded
    return None


def _launch_chrome(port: int = CDP_PORT, timeout: int = 20) -> bool:
    """Launch Chrome with CDP debugging enabled.

    Returns True if Chrome CDP becomes available within timeout seconds.
    """
    import subprocess, sys as _sys

    chrome_bin = _find_chrome_binary()
    if not chrome_bin:
        return False

    profile_dir = str(_CHROME_PROFILE_DIR)
    _log_session("chrome_launch", "system", f"port={port} profile={profile_dir}")

    if _sys.platform == "darwin":
        subprocess.Popen([
            "open", "-na", "Google Chrome", "--args",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--remote-allow-origins=*",
        ])
    elif _sys.platform.startswith("linux"):
        subprocess.Popen([
            chrome_bin,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--remote-allow-origins=*",
        ])
    elif _sys.platform == "win32":
        subprocess.Popen([
            chrome_bin,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--remote-allow-origins=*",
        ])
    else:
        return False

    for _ in range(timeout):
        time.sleep(1)
        if is_chrome_cdp_available(port):
            _log_session("chrome_ready", "system", f"port={port}")
            return True
    return False


def _prompt_chrome_install():
    """Open Chrome download page in the system's default browser."""
    import webbrowser
    _log_session("chrome_missing", "system",
                 f"Opening download page: {_CHROME_DOWNLOAD_URL}")
    webbrowser.open(_CHROME_DOWNLOAD_URL)


def ensure_chrome(port: int = CDP_PORT) -> Dict[str, Any]:
    """Ensure Chrome is running with CDP. Launch if closed, prompt install if missing.

    Returns:
        {"ok": bool, "action": str, "error": str (if failed)}
    """
    if is_chrome_cdp_available(port):
        return {"ok": True, "action": "already_running"}

    chrome_bin = _find_chrome_binary()
    if not chrome_bin:
        _prompt_chrome_install()
        return {"ok": False, "action": "chrome_not_installed",
                "error": "Google Chrome is not installed. "
                         "Opened download page in default browser."}

    _log_session("chrome_reboot", "system", "Chrome CDP unavailable, relaunching...")
    launched = _launch_chrome(port)
    if launched:
        return {"ok": True, "action": "relaunched"}
    return {"ok": False, "action": "launch_failed",
            "error": "Chrome launched but CDP did not become available within timeout"}


class CDMCPSession:
    """A named CDMCP session with a lifetime tab."""

    def __init__(self, name: str, timeout_sec: int = DEFAULT_TIMEOUT_SEC,
                 idle_timeout_sec: int = 3600,
                 port: int = CDP_PORT):
        self.name = name
        self.session_id = str(uuid.uuid4())[:8]
        self.port = port
        self.timeout_sec = timeout_sec
        self.idle_timeout_sec = idle_timeout_sec
        self.created_at = time.time()
        self.last_activity = time.time()
        self.lifetime_tab_id: Optional[str] = None
        self.lifetime_tab_url: Optional[str] = None
        self._cdp: Optional[CDPSession] = None
        self._booted = False
        self.tab_was_recovered = False
        self.window_id: Optional[int] = None
        self._tabs: Dict[str, Dict[str, Any]] = {}  # tab_label -> {id, url, ws, state}
        self._demo_pid: Optional[int] = None
        self._http_port: Optional[int] = None
        self.mcp_count: int = 0

    def boot(self, url: str, new_window: bool = True) -> Dict[str, Any]:
        """Boot the session by opening a new tab as the lifetime anchor.

        Args:
            url: The URL to open in the lifetime tab.
            new_window: If True, open in a brand new Chrome window (not alongside
                        existing tabs). Uses Target.createTarget with newWindow=true.
        """
        self.lifetime_tab_url = url
        _log_session("boot", self.name, f"url={url} new_window={new_window}")

        if not is_chrome_cdp_available(self.port):
            return {"ok": False, "error": "Chrome CDP not available"}

        if new_window:
            tab_id = self._open_in_new_window(url)
        else:
            tab_id = self._open_in_existing_window(url)

        if not tab_id:
            return {"ok": False, "error": "Failed to open tab"}

        time.sleep(1.5)

        # Find the tab by ID first, then by domain
        tab = None
        for t in list_tabs(self.port):
            if t.get("id") == tab_id:
                tab = t
                break

        if not tab:
            domain = url.split("//")[-1].split("/")[0] if "//" in url else url
            tab = find_tab(domain, port=self.port)

        if not tab:
            return {"ok": False, "error": f"Tab not found after opening: {url}"}

        self.lifetime_tab_id = tab.get("id")
        self._connect(tab)
        self._booted = True
        self.touch()

        # Capture the window ID for this session
        self._capture_window_id(tab)
        _log_session("booted", self.name,
                     f"tabId={self.lifetime_tab_id} windowId={self.window_id}")
        _save_state()

        return {
            "ok": True,
            "session_id": self.session_id,
            "name": self.name,
            "tabId": self.lifetime_tab_id,
            "windowId": self.window_id,
            "url": url,
        }

    def _open_in_new_window(self, url: str) -> Optional[str]:
        """Open a URL in a completely new Chrome window via browser-level CDP."""
        import urllib.request
        try:
            ver_url = f"http://localhost:{self.port}/json/version"
            with urllib.request.urlopen(ver_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                return None
            bs = CDPSession(browser_ws, timeout=10)
            result = bs.send_and_recv("Target.createTarget", {
                "url": url,
                "newWindow": True,
            })
            bs.close()
            if not result:
                return None
            # CDP response: {"id": N, "result": {"targetId": "..."}}
            inner = result.get("result", result)
            return inner.get("targetId")
        except Exception:
            return None

    def _open_in_existing_window(self, url: str) -> Optional[str]:
        """Open a URL as a new tab in an existing window."""
        if open_tab(url, self.port):
            time.sleep(1)
            domain = url.split("//")[-1].split("/")[0] if "//" in url else url
            tab = find_tab(domain, port=self.port)
            return tab.get("id") if tab else None
        return None

    def _capture_window_id(self, tab: Dict[str, Any]):
        """Discover and store the Chrome window ID for this session's tab."""
        ws = tab.get("webSocketDebuggerUrl")
        if not ws:
            return
        try:
            s = CDPSession(ws, timeout=5)
            result = s.send_and_recv("Browser.getWindowForTarget", {})
            wid = (result or {}).get("result", {}).get("windowId")
            if wid:
                self.window_id = wid
            s.close()
        except Exception:
            pass

    def _is_tab_in_window(self, tab: Dict[str, Any]) -> bool:
        """Check if a Chrome tab belongs to this session's window."""
        if not self.window_id:
            return True
        ws = tab.get("webSocketDebuggerUrl")
        if not ws:
            return False
        try:
            s = CDPSession(ws, timeout=5)
            result = s.send_and_recv("Browser.getWindowForTarget", {})
            s.close()
            wid = (result or {}).get("result", {}).get("windowId")
            return wid == self.window_id
        except Exception:
            return False

    def open_tab_in_session(self, url: str) -> Optional[str]:
        """Open a new tab inside this session's window (not a new window).

        Uses chrome.tabs.create API via extension for reliable window targeting.
        Falls back to CDP Target.createTarget + verification + move.

        Returns the CDP target ID of the new tab, or None on failure.
        """
        self.touch()
        if not self.window_id:
            return self._open_in_existing_window(url)

        # Primary: use chrome.tabs.create with explicit windowId
        try:
            overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
            spec = importlib.util.spec_from_file_location("cdmcp_ov_tab", str(overlay_path))
            ov = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ov)

            result = ov.create_tab_in_window(url, self.window_id, self.port)
            if result and result.get("cdp_target_id"):
                _log_session("open_tab:chrome_api", self.name,
                             f"url={url} tabId={result['cdp_target_id']}")
                return result["cdp_target_id"]
        except Exception:
            pass

        # Fallback: CDP Target.createTarget + verify window + move if needed
        import urllib.request
        try:
            ver_url = f"http://localhost:{self.port}/json/version"
            with urllib.request.urlopen(ver_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                return None
            bs = CDPSession(browser_ws, timeout=10)
            result = bs.send_and_recv("Target.createTarget", {
                "url": url,
                "newWindow": False,
                "windowId": self.window_id,
            })
            bs.close()
            if not result:
                return None
            inner = result.get("result", result)
            tab_id = inner.get("targetId")
            if not tab_id:
                return None

            # Verify the tab is in the correct window; move if not
            time.sleep(0.5)
            for t in list_tabs(self.port):
                if t.get("id") == tab_id:
                    ws_url = t.get("webSocketDebuggerUrl")
                    if ws_url:
                        try:
                            s = CDPSession(ws_url, timeout=5)
                            win_res = s.send_and_recv("Browser.getWindowForTarget", {})
                            s.close()
                            actual_win = (win_res or {}).get("result", {}).get("windowId")
                            if actual_win and actual_win != self.window_id:
                                _log_session("open_tab:wrong_window", self.name,
                                             f"expected={self.window_id} actual={actual_win}, moving...")
                                try:
                                    ov.move_tab_to_window(tab_id, self.window_id, self.port)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    break
            return tab_id
        except Exception:
            return self._open_in_existing_window(url)

    def _connect(self, tab: Dict[str, Any]) -> bool:
        """Establish a CDP WebSocket connection to the lifetime tab."""
        ws = tab.get("webSocketDebuggerUrl")
        if not ws:
            return False
        try:
            if self._cdp:
                try:
                    self._cdp.close()
                except Exception:
                    pass
            self._cdp = CDPSession(ws)
            return True
        except Exception:
            self._cdp = None
            return False

    def ensure_tab(self) -> bool:
        """Ensure the lifetime tab is still alive; reopen if needed.

        Returns True if the tab exists (either already or after reopening).
        Sets self.tab_was_recovered to True when a reopen was needed.
        """
        self.tab_was_recovered = False
        if not self.lifetime_tab_url:
            return False

        if self.lifetime_tab_id:
            for tab in list_tabs(self.port):
                if tab.get("id") == self.lifetime_tab_id:
                    if not self._cdp:
                        self._connect(tab)
                    return True

        recovery_url = self.lifetime_tab_url
        if recovery_url and "127.0.0.1" in recovery_url and "/welcome" in recovery_url:
            # Try to start the HTTP server for a proper welcome URL
            try:
                server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
                _spec = importlib.util.spec_from_file_location("cdmcp_srv_recover", str(server_path))
                _mod = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                srv_url, srv_port = _mod.start_server(
                    preferred_port=getattr(self, "_http_port", None))
                self._http_port = srv_port
                import re
                recovery_url = re.sub(r'127\.0\.0\.1:\d+', f'127.0.0.1:{srv_port}', recovery_url)
                self.lifetime_tab_url = recovery_url
            except Exception:
                welcome_html = _TOOL_DIR / "data" / "welcome.html"
                if welcome_html.exists():
                    query = recovery_url.split("?", 1)[1] if "?" in recovery_url else ""
                    recovery_url = f"file://{welcome_html}?{query}" if query else f"file://{welcome_html}"
                    self.lifetime_tab_url = recovery_url

        _log_session("tab_lost", self.name, f"Reopening in new window (url={recovery_url[:60]})")
        tab_id = self._open_in_new_window(recovery_url)
        if not tab_id:
            if not open_tab(self.lifetime_tab_url, self.port):
                return False

        time.sleep(1.5)

        tab = None
        if tab_id:
            for t in list_tabs(self.port):
                if t.get("id") == tab_id:
                    tab = t
                    break
        if not tab:
            domain = self.lifetime_tab_url.split("//")[-1].split("/")[0] if "//" in self.lifetime_tab_url else self.lifetime_tab_url
            tab = find_tab(domain, port=self.port)

        if tab:
            self.lifetime_tab_id = tab.get("id")
            self._connect(tab)
            self._capture_window_id(tab)
            self.tab_was_recovered = True
            _log_session("tab_reopened", self.name,
                         f"tabId={self.lifetime_tab_id} windowId={self.window_id}")
            _save_state()
            return True
        return False

    def full_reboot(self, skip_demo: bool = False) -> bool:
        """Perform a full session reboot: new window, pin, overlays, demo.

        Called when recovery detects the session window is gone. Mirrors
        the boot flow from api.boot_session() so the user gets the same
        experience as a fresh session.

        Args:
            skip_demo: If True, skip opening the demo tab and starting the
                       demo subprocess.  Used by require_tab() recovery so
                       only the session tab is reopened.

        Returns True if the reboot succeeded.
        """
        import importlib.util
        import subprocess

        _log_session("full_reboot", self.name, "Starting full reboot...")

        # 0. Kill old demo subprocess if any
        old_pid = getattr(self, "_demo_pid", None)
        if old_pid:
            try:
                import signal, os
                os.kill(old_pid, signal.SIGTERM)
                _log_session("full_reboot:demo_killed", self.name, f"pid={old_pid}")
            except (ProcessLookupError, OSError):
                pass
            self._demo_pid = None
        self._tabs.clear()

        # 1. Start HTTP server and build welcome URL
        try:
            server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
            _srv_spec = importlib.util.spec_from_file_location("cdmcp_srv_reboot", str(server_path))
            _srv_mod = importlib.util.module_from_spec(_srv_spec)
            _srv_spec.loader.exec_module(_srv_mod)
            _srv_url, _srv_port = _srv_mod.start_server(
                preferred_port=getattr(self, "_http_port", None))
            self._http_port = _srv_port
        except Exception:
            _srv_url = None

        created_ts = int(self.created_at)
        idle_sec = getattr(self, "timeout_sec", 3600)
        last_act = int(self.last_activity)
        if _srv_url:
            welcome_url = (
                f"{_srv_url}/welcome?session_id={self.session_id}"
                f"&port={self.port}&timeout_sec={self.timeout_sec}"
                f"&created_at={created_ts}"
                f"&idle_timeout_sec={idle_sec}&last_activity={last_act}"
            )
        else:
            welcome_html = _TOOL_DIR / "data" / "welcome.html"
            welcome_url = (
                f"file://{welcome_html}?session_id={self.session_id}"
                f"&port={self.port}&timeout_sec={self.timeout_sec}"
                f"&created_at={created_ts}"
                f"&idle_timeout_sec={idle_sec}&last_activity={last_act}"
            )
        self.lifetime_tab_url = welcome_url

        # 2. Open new window with welcome page
        tab_id = self._open_in_new_window(welcome_url)
        if not tab_id:
            _log_session("full_reboot:fail", self.name, "Failed to open new window")
            return False

        time.sleep(1.5)

        tab = None
        for t in list_tabs(self.port):
            if t.get("id") == tab_id:
                tab = t
                break
        if not tab:
            return False

        self.lifetime_tab_id = tab.get("id")
        self._connect(tab)
        self._capture_window_id(tab)
        self._booted = True
        self.tab_was_recovered = True
        self.register_tab("welcome", self.lifetime_tab_id,
                          url=welcome_url, state="active")
        _save_state()

        # 3. Load overlay module and apply overlays + pin
        try:
            overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
            spec = importlib.util.spec_from_file_location("cdmcp_ov", str(overlay_path))
            ov = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ov)

            cdp = self._cdp
            if cdp:
                ov.pin_tab_by_target_id(self.lifetime_tab_id, pinned=True, port=self.port)
                ov.activate_tab(self.lifetime_tab_id, self.port)
                ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
                ov.inject_badge(cdp, text=f"CDMCP [{self.session_id}]", color="#1a73e8")
                ov.inject_focus(cdp, color="#1a73e8")
        except Exception:
            pass

        # 4. Open demo tab in the same window (skipped on require_tab recovery)
        if not skip_demo:
            try:
                server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
                spec = importlib.util.spec_from_file_location("cdmcp_srv", str(server_path))
                srv = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(srv)

                server_url, _srv_port = srv.start_server(
                    preferred_port=getattr(self, "_http_port", None))
                self._http_port = _srv_port
                chat_url = f"{server_url}/chat?session_id={self.session_id}"
                demo_tab_id = self.open_tab_in_session(chat_url)
                demo_ws = None

                if demo_tab_id:
                    time.sleep(1.5)
                    for t in list_tabs(self.port):
                        if t.get("id") == demo_tab_id:
                            ws = t.get("webSocketDebuggerUrl", "")
                            if ws:
                                demo_ws = ws
                                self.register_tab("demo", demo_tab_id,
                                                  url=chat_url, ws=ws, state="active")
                                try:
                                    demo_cdp = CDPSession(ws, timeout=10)
                                    ov.inject_favicon(demo_cdp, svg_color="#1a73e8", letter="C")
                                    ov.inject_badge(demo_cdp, text=f"Demo [{self.session_id}]",
                                                    color="#34a853")
                                    demo_cdp.close()
                                except Exception:
                                    pass
                            break

                # 5. Start continuous demo in background
                if demo_ws:
                    project_root = str(_TOOL_DIR.parent.parent)
                    demo_py = str(_TOOL_DIR / "logic" / "cdp" / "demo.py")
                    inline_code = (
                        f"import sys, os; os.chdir({project_root!r}); "
                        f"sys.path.insert(0, {project_root!r}); "
                        "import importlib.util; "
                        f"spec = importlib.util.spec_from_file_location('demo', {demo_py!r}); "
                        "mod = importlib.util.module_from_spec(spec); "
                        "spec.loader.exec_module(mod); "
                        f"mod.run_demo_on_tab({demo_ws!r}, port={self.port})"
                    )
                    py_path = _find_project_python()
                    demo_log = _REPORT_DIR / "demo_subprocess.log"
                    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
                    log_f = open(demo_log, "a")
                    proc = subprocess.Popen(
                        [py_path, "-c", inline_code],
                        stdout=log_f,
                        stderr=log_f,
                        start_new_session=True,
                    )
                    self._demo_pid = proc.pid
            except Exception:
                pass

        _log_session("full_reboot:done", self.name,
                     f"windowId={self.window_id} tabId={self.lifetime_tab_id}")
        return True

    def get_cdp(self) -> Optional[CDPSession]:
        """Get a live CDP session, reconnecting if necessary."""
        self.touch()
        if self.ensure_tab():
            return self._cdp
        return None

    def touch(self):
        """Update last activity time."""
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        """Check if the session has expired by idle or absolute timeout."""
        now = time.time()
        idle = (now - self.last_activity) > self.idle_timeout_sec
        absolute = (now - self.created_at) > self.timeout_sec if self.timeout_sec else False
        return idle or absolute

    def expiry_info(self) -> Dict[str, Any]:
        """Return detailed expiry information."""
        now = time.time()
        idle_remaining = max(0, self.idle_timeout_sec - (now - self.last_activity))
        abs_remaining = max(0, self.timeout_sec - (now - self.created_at)) if self.timeout_sec else None
        return {
            "idle_remaining_sec": int(idle_remaining),
            "absolute_remaining_sec": int(abs_remaining) if abs_remaining is not None else None,
            "idle_expired": idle_remaining <= 0,
            "absolute_expired": abs_remaining is not None and abs_remaining <= 0,
            "expired": self.is_expired(),
        }

    def close(self):
        """Close the session: kill demo, stop HTTP server, close window, clean state."""
        _log_session("close", self.name)

        # 1. Kill demo subprocess to prevent reconnection
        demo_pid = getattr(self, "_demo_pid", None)
        if demo_pid:
            try:
                import signal, os
                os.kill(demo_pid, signal.SIGTERM)
                _log_session("close:demo_killed", self.name, f"pid={demo_pid}")
            except (ProcessLookupError, OSError):
                pass
            self._demo_pid = None

        # 2. Stop the HTTP server for this session
        self._stop_http_server()

        # 3. Close CDP connection
        if self._cdp:
            try:
                self._cdp.close()
            except Exception:
                pass
            self._cdp = None

        # 4. Close the entire Chrome window (not just tracked tabs)
        #    This ensures stray untracked tabs in the session window are also closed.
        window_closed = False
        if self.window_id:
            window_closed = self._close_window()

        if not window_closed:
            # Fallback: close individual tracked tabs
            all_tab_ids = set()
            for label, info in self._tabs.items():
                tid = info.get("id")
                if tid:
                    all_tab_ids.add(tid)
            if self.lifetime_tab_id:
                all_tab_ids.add(self.lifetime_tab_id)

            for tab_id in all_tab_ids:
                try:
                    close_tab(tab_id, self.port)
                except Exception:
                    pass
            _log_session("close:tabs", self.name, f"closed {len(all_tab_ids)} tabs")

        # 5. Clean up state file for this session
        self._tabs.clear()
        self.lifetime_tab_id = None
        self._booted = False
        self._http_port = None

    def _close_window(self) -> bool:
        """Close the entire Chrome window that belongs to this session.

        Returns True if the window was closed successfully.
        """
        if not self.window_id:
            return False
        try:
            import urllib.request
            ver_url = f"http://localhost:{self.port}/json/version"
            with urllib.request.urlopen(ver_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                return False

            # Find all tabs belonging to this window and close them
            tabs_in_window = []
            for t in list_tabs(self.port):
                ws_url = t.get("webSocketDebuggerUrl")
                if not ws_url:
                    continue
                try:
                    s = CDPSession(ws_url, timeout=3)
                    win_res = s.send_and_recv("Browser.getWindowForTarget", {})
                    s.close()
                    wid = (win_res or {}).get("result", {}).get("windowId")
                    if wid == self.window_id:
                        tabs_in_window.append(t.get("id"))
                except Exception:
                    pass

            for tab_id in tabs_in_window:
                try:
                    close_tab(tab_id, self.port)
                except Exception:
                    pass

            _log_session("close:window", self.name,
                         f"windowId={self.window_id} tabs_closed={len(tabs_in_window)}")
            self.window_id = None
            return len(tabs_in_window) > 0
        except Exception:
            return False

    def _stop_http_server(self):
        """Stop the persistent HTTP server process."""
        try:
            server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
            spec = importlib.util.spec_from_file_location(
                "cdmcp_srv_cleanup", str(server_path))
            srv_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(srv_mod)
            srv_mod.stop_server()
            _log_session("close:http_stopped", self.name,
                         f"port={getattr(self, '_http_port', 'unknown')}")
        except Exception:
            pass
        self._http_port = None

    # --- Multi-tab tracking ---

    def register_tab(self, label: str, tab_id: str, url: str = "",
                     ws: str = "", state: str = "active") -> None:
        """Register a tab in this session by label (e.g., 'welcome', 'demo', 'youtube')."""
        self._tabs[label] = {
            "id": tab_id, "url": url, "ws": ws, "state": state,
        }
        self.touch()
        _log_session("register_tab", self.name, f"label={label} id={tab_id}")

    def get_tab(self, label: str) -> Optional[Dict[str, Any]]:
        """Get tab info by label, or None if not found."""
        return self._tabs.get(label)

    def get_tab_cdp(self, label: str) -> Optional[CDPSession]:
        """Get a live CDP session for a specific tab by label."""
        info = self._tabs.get(label)
        if not info:
            return None
        ws = info.get("ws")
        if not ws:
            for t in list_tabs(self.port):
                if t.get("id") == info["id"]:
                    ws = t.get("webSocketDebuggerUrl", "")
                    info["ws"] = ws
                    break
        if not ws:
            return None
        try:
            return CDPSession(ws, timeout=10)
        except Exception:
            return None

    def list_tabs_in_session(self) -> List[Dict[str, Any]]:
        """List all tracked tabs in this session."""
        result = []
        for label, info in self._tabs.items():
            alive = False
            for t in list_tabs(self.port):
                if t.get("id") == info["id"]:
                    alive = True
                    break
            result.append({
                "label": label,
                "id": info["id"],
                "url": info.get("url", ""),
                "state": info.get("state", "unknown"),
                "alive": alive,
            })
        return result

    def set_tab_state(self, label: str, state: str) -> bool:
        """Update the state of a tracked tab."""
        if label in self._tabs:
            self._tabs[label]["state"] = state
            return True
        return False

    def require_tab(self, label: str, url_pattern: str = "",
                    open_url: str = "", auto_open: bool = True,
                    wait_sec: float = 10.0,
                    auto_lock: bool = True) -> Optional[Dict[str, Any]]:
        """Find or open a tab in this session by label/URL pattern.

        Lookup order:
          1. Check registered tabs (by label) — if still alive, return it.
          2. Scan all Chrome tabs for *url_pattern* substring match.
          3. If not found and *auto_open* is True, open *open_url* in the
             session window, wait up to *wait_sec*, register, and return.
          4. If not found and *auto_open* is False, return None.

        Args:
            label:       Unique label for this tab (e.g. "colab", "youtube").
            url_pattern: Substring to match in tab URLs (e.g. "colab.research.google.com").
            open_url:    Full URL to open when the tab is missing.
            auto_open:   Open the tab automatically when not found.
            wait_sec:    Seconds to wait for a newly opened tab to appear.
            auto_lock:   Inject lock overlay on acquired tab (default True).

        Returns:
            Dict ``{id, url, ws, label, recovered}`` or None.
        """
        self.touch()

        def _maybe_lock(tab_info):
            if not auto_lock or not tab_info or not tab_info.get("ws"):
                return tab_info
            try:
                overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
                if overlay_path.exists():
                    spec = importlib.util.spec_from_file_location(
                        "cdmcp_overlay_lock", overlay_path)
                    _ov = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(_ov)
                    _cdp = CDPSession(tab_info["ws"], timeout=5)
                    _ov.inject_lock(_cdp, tool_name="CDMCP")
                    _cdp.close()
            except Exception:
                pass
            return tab_info

        # 1. Previously registered and still alive
        existing = self._tabs.get(label)
        if existing:
            for t in list_tabs(self.port):
                if t.get("id") == existing["id"]:
                    ws = t.get("webSocketDebuggerUrl", "")
                    existing["ws"] = ws
                    existing["url"] = t.get("url", existing.get("url", ""))
                    _log_session("require_tab:found_registered", self.name,
                                 f"label={label} id={existing['id']}")
                    return _maybe_lock({"id": existing["id"], "url": existing["url"],
                            "ws": ws, "label": label, "recovered": False})

        # 2. Scan tabs by URL pattern, restricted to session window
        if url_pattern:
            for t in list_tabs(self.port):
                if url_pattern.lower() in (t.get("url", "") or "").lower() and t.get("type") == "page":
                    if not self._is_tab_in_window(t):
                        continue
                    tab_id = t.get("id")
                    ws = t.get("webSocketDebuggerUrl", "")
                    self.register_tab(label, tab_id, url=t.get("url", ""), ws=ws)
                    _log_session("require_tab:found_by_url", self.name,
                                 f"label={label} id={tab_id}")
                    _save_state()
                    return _maybe_lock({"id": tab_id, "url": t.get("url", ""),
                            "ws": ws, "label": label, "recovered": False})

        if not auto_open or not open_url:
            _log_session("require_tab:not_found", self.name,
                         f"label={label} auto_open={auto_open}")
            return None

        # 3. Ensure the session window is alive before opening a tab in it.
        #    If the window was closed, perform a full reboot (pin, overlays,
        #    demo) so the user gets the same experience as a fresh session.
        if self.lifetime_tab_url:
            window_alive = False
            if self.lifetime_tab_id:
                for t in list_tabs(self.port):
                    if t.get("id") == self.lifetime_tab_id:
                        window_alive = True
                        break
            if not window_alive:
                _log_session("require_tab:window_lost", self.name,
                             "Triggering full reboot (session + demo)...")
                self.full_reboot(skip_demo=False)

                if url_pattern:
                    for t in list_tabs(self.port):
                        if url_pattern.lower() in (t.get("url", "") or "").lower() and t.get("type") == "page":
                            if not self._is_tab_in_window(t):
                                continue
                            tab_id = t.get("id")
                            ws = t.get("webSocketDebuggerUrl", "")
                            self.register_tab(label, tab_id, url=t.get("url", ""), ws=ws)
                            _log_session("require_tab:found_after_reboot", self.name,
                                         f"label={label} id={tab_id}")
                            _save_state()
                            return _maybe_lock({"id": tab_id, "url": t.get("url", ""),
                                    "ws": ws, "label": label, "recovered": True})

        _log_session("require_tab:opening", self.name,
                     f"label={label} url={open_url} windowId={self.window_id}")
        new_tab_id = self.open_tab_in_session(open_url)
        if not new_tab_id:
            return None

        # Wait for the tab to appear
        deadline = time.time() + wait_sec
        while time.time() < deadline:
            time.sleep(1)
            for t in list_tabs(self.port):
                tid = t.get("id")
                if tid == new_tab_id or (url_pattern and url_pattern.lower() in (t.get("url", "") or "").lower()):
                    ws = t.get("webSocketDebuggerUrl", "")
                    self.register_tab(label, t["id"], url=t.get("url", ""), ws=ws)
                    _log_session("require_tab:opened", self.name,
                                 f"label={label} id={t['id']}")
                    _save_state()
                    return _maybe_lock({"id": t["id"], "url": t.get("url", ""),
                            "ws": ws, "label": label, "recovered": True})

        return None

    # --- Serialization ---

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "session_id": self.session_id,
            "booted": self._booted,
            "lifetime_tab_id": self.lifetime_tab_id,
            "lifetime_tab_url": self.lifetime_tab_url,
            "window_id": self.window_id,
            "timeout_sec": self.timeout_sec,
            "idle_timeout_sec": self.idle_timeout_sec,
            "last_activity": self.last_activity,
            "age_sec": int(time.time() - self.created_at),
            "http_port": self._http_port,
            "demo_pid": self._demo_pid,
            "tabs": self.list_tabs_in_session(),
            **self.expiry_info(),
        }


# ---------------------------------------------------------------------------
# Persistent state file
# ---------------------------------------------------------------------------

_STATE_FILE = _SESSION_DIR / "state.json"


def _save_state():
    """Persist all session metadata to disk for cross-process sharing."""
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    sessions_data = {}
    for name, s in _sessions.items():
        sessions_data[name] = {
            "session_id": s.session_id,
            "window_id": s.window_id,
            "lifetime_tab_id": s.lifetime_tab_id,
            "lifetime_tab_url": s.lifetime_tab_url,
            "created_at": s.created_at,
            "last_activity": s.last_activity,
            "timeout_sec": s.timeout_sec,
            "idle_timeout_sec": getattr(s, "idle_timeout_sec", 3600),
            "port": s.port,
            "tabs": {label: {"id": info["id"], "url": info.get("url", ""),
                              "state": info.get("state", "unknown")}
                     for label, info in s._tabs.items()},
            "demo_pid": getattr(s, "_demo_pid", None),
            "http_port": getattr(s, "_http_port", None),
            "mcp_count": s.mcp_count,
        }
    state = {
        "_config": {
            "max_sessions": _max_sessions,
            "overflow_policy": _overflow_policy,
        },
        "sessions": sessions_data,
    }
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except OSError:
        pass


def _load_state():
    """Restore sessions and config from disk."""
    global _max_sessions, _overflow_policy
    if not _STATE_FILE.exists():
        return
    try:
        with open(_STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        return

    # Load config
    cfg = state.get("_config", {})
    _max_sessions = cfg.get("max_sessions", 0)
    _overflow_policy = cfg.get("overflow_policy", "fail")

    # Support both old format (flat dict of sessions) and new format
    sessions_data = state.get("sessions", {})
    if not sessions_data and "_config" not in state:
        sessions_data = state  # old format: top-level keys are session names

    for name, info in sessions_data.items():
        if name.startswith("_") or name in _sessions:
            continue
        s = CDMCPSession(name, timeout_sec=info.get("timeout_sec", DEFAULT_TIMEOUT_SEC),
                         idle_timeout_sec=info.get("idle_timeout_sec", 3600),
                         port=info.get("port", CDP_PORT))
        s.session_id = info.get("session_id", s.session_id)
        s.window_id = info.get("window_id")
        s.lifetime_tab_id = info.get("lifetime_tab_id")
        s.lifetime_tab_url = info.get("lifetime_tab_url")
        s.created_at = info.get("created_at", s.created_at)
        s.last_activity = info.get("last_activity", s.last_activity)
        s._booted = bool(s.lifetime_tab_id)
        for label, tab_info in info.get("tabs", {}).items():
            s._tabs[label] = {
                "id": tab_info["id"],
                "url": tab_info.get("url", ""),
                "state": tab_info.get("state", "unknown"),
            }
        s._demo_pid = info.get("demo_pid")
        s._http_port = info.get("http_port")
        s.mcp_count = info.get("mcp_count", 0)
        if not s.is_expired():
            _sessions[name] = s
        else:
            _log_session("load:already_expired", name, "Cleaning up on load")
            s.close()


# ---------------------------------------------------------------------------
# Session Registry (module-level singleton)
# ---------------------------------------------------------------------------

_sessions: Dict[str, CDMCPSession] = {}
_max_sessions: int = 0  # 0 = unlimited
_overflow_policy: str = "fail"  # "fail" | "kill_oldest_boot" | "kill_oldest_activity"
_load_state()  # restores sessions + max_sessions config from disk

# ---------------------------------------------------------------------------
# Max sessions limit & overflow policy
# ---------------------------------------------------------------------------


def set_max_sessions(limit: int, policy: str = "fail"):
    """Configure the maximum number of concurrent sessions.

    Args:
        limit: Maximum number of sessions (0 = unlimited).
        policy: What to do when limit is reached:
            - "fail": Refuse to create, return None (caller sees error + active list).
            - "kill_oldest_boot": Close the session that was created earliest.
            - "kill_oldest_activity": Close the session that was idle longest.
    """
    global _max_sessions, _overflow_policy
    if policy not in ("fail", "kill_oldest_boot", "kill_oldest_activity"):
        raise ValueError(f"Unknown overflow policy: {policy!r}")
    _max_sessions = max(0, limit)
    _overflow_policy = policy
    _log_session("config", "max_sessions",
                 f"limit={_max_sessions} policy={_overflow_policy}")
    _save_state()


def get_max_sessions_config() -> Dict[str, Any]:
    """Return the current max sessions configuration."""
    return {
        "max_sessions": _max_sessions,
        "overflow_policy": _overflow_policy,
        "active_count": len(_sessions),
    }


class SessionLimitError(Exception):
    """Raised when session creation is refused due to the limit."""
    def __init__(self, message: str, active_sessions: List[Dict[str, Any]]):
        super().__init__(message)
        self.active_sessions = active_sessions


def _enforce_session_limit(exclude_name: str = "") -> Optional[str]:
    """Enforce max_sessions limit before creating a new session.

    Returns:
        None if creation is allowed.
        If policy="fail", raises SessionLimitError.
        Otherwise returns the name of the evicted session.
    """
    if _max_sessions <= 0:
        return None
    _cleanup_expired()
    active = {n: s for n, s in _sessions.items() if n != exclude_name}
    if len(active) < _max_sessions:
        return None

    if _overflow_policy == "fail":
        summaries = []
        for n, s in active.items():
            summaries.append({
                "name": n, "session_id": s.session_id,
                "created_at": s.created_at, "last_activity": s.last_activity,
                "age_sec": int(time.time() - s.created_at),
                "idle_sec": int(time.time() - s.last_activity),
            })
        raise SessionLimitError(
            f"Session limit reached ({_max_sessions}). "
            f"Active sessions: {[s['name'] for s in summaries]}",
            summaries,
        )

    if _overflow_policy == "kill_oldest_boot":
        victim = min(active, key=lambda n: active[n].created_at)
    else:  # kill_oldest_activity
        victim = min(active, key=lambda n: active[n].last_activity)

    _log_session("evict", victim,
                 f"policy={_overflow_policy} to make room (limit={_max_sessions})")
    _sessions[victim].close()
    del _sessions[victim]
    _save_state()
    return victim


def create_session(name: str, timeout_sec: int = DEFAULT_TIMEOUT_SEC,
                   idle_timeout_sec: int = 3600,
                   port: int = CDP_PORT) -> CDMCPSession:
    """Create a new named session (replaces any existing session with the same name).

    Raises SessionLimitError if max_sessions is reached and policy is 'fail'.
    """
    _enforce_session_limit(exclude_name=name)
    if name in _sessions:
        _sessions[name].close()
    session = CDMCPSession(name, timeout_sec=timeout_sec,
                           idle_timeout_sec=idle_timeout_sec, port=port)
    _sessions[name] = session
    _log_session("create", name, f"timeout={timeout_sec}s idle={idle_timeout_sec}s")
    _save_state()
    start_watchdog()
    return session


def get_session(name: str) -> Optional[CDMCPSession]:
    """Get a session by name, or None if not found / expired."""
    session = _sessions.get(name)
    if session and session.is_expired():
        _log_session("expired", name)
        session.close()
        del _sessions[name]
        _save_state()
        return None
    return session


def list_sessions() -> List[Dict[str, Any]]:
    _cleanup_expired()
    return [s.to_dict() for s in _sessions.values()]


def close_session(name: str) -> bool:
    session = _sessions.pop(name, None)
    if session:
        session.close()
        _save_state()
        return True
    return False


def close_all_sessions():
    for s in _sessions.values():
        s.close()
    _sessions.clear()
    _save_state()


def get_any_active_session() -> Optional[CDMCPSession]:
    """Return the first non-expired booted session, or None."""
    _cleanup_expired()
    for s in _sessions.values():
        if s._booted and not s.is_expired():
            return s
    return None


def require_tab(label: str, url_pattern: str = "",
                open_url: str = "", auto_open: bool = True,
                session_name: str = "",
                wait_sec: float = 10.0) -> Optional[Dict[str, Any]]:
    """Module-level convenience: find/open a tab in the current session.

    If *session_name* is empty, uses the first active session.
    Returns the same dict as CDMCPSession.require_tab(), or None.
    """
    if session_name:
        s = get_session(session_name)
    else:
        s = get_any_active_session()
    if not s:
        return None
    return s.require_tab(label, url_pattern=url_pattern,
                         open_url=open_url, auto_open=auto_open,
                         wait_sec=wait_sec)


def _ensure_demo_tab(session: "CDMCPSession", server_url: str, port: int = CDP_PORT):
    """Check if demo tab exists in session; create it if missing."""
    demo_info = session._tabs.get("demo")
    if demo_info:
        tab_id = demo_info.get("id")
        if tab_id:
            for t in list_tabs(port):
                if t.get("id") == tab_id:
                    return

    chat_pattern = f"/chat?session_id={session.session_id}"
    for t in list_tabs(port):
        if t.get("type") == "page" and chat_pattern in t.get("url", ""):
            session.register_tab("demo", t["id"],
                                 url=t.get("url", ""),
                                 ws=t.get("webSocketDebuggerUrl", ""),
                                 state="active")
            _save_state()
            return
    try:
        chat_url = f"{server_url}/chat?session_id={session.session_id}"
        demo_tab_id = session.open_tab_in_session(chat_url)
        if demo_tab_id:
            time.sleep(1.5)
            for t in list_tabs(port):
                if t.get("id") == demo_tab_id:
                    ws = t.get("webSocketDebuggerUrl", "")
                    if ws:
                        session.register_tab("demo", demo_tab_id,
                                             url=chat_url, ws=ws, state="active")
                        sid_short = session.session_id[:8]
                        try:
                            overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
                            spec = importlib.util.spec_from_file_location(
                                "cdmcp_ov_demo", str(overlay_path))
                            ov = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(ov)
                            demo_cdp = CDPSession(ws, timeout=10)
                            ov.inject_favicon(demo_cdp, svg_color="#1a73e8", letter="C")
                            ov.inject_badge(demo_cdp, text=f"Demo [{sid_short}]",
                                            color="#34a853")
                            demo_cdp.close()
                        except Exception:
                            pass

                        project_root = str(_TOOL_DIR.parent.parent)
                        demo_py = str(_TOOL_DIR / "logic" / "cdp" / "demo.py")
                        inline_code = (
                            f"import sys, os; os.chdir({project_root!r}); "
                            f"sys.path.insert(0, {project_root!r}); "
                            "import importlib.util; "
                            f"spec = importlib.util.spec_from_file_location('demo', {demo_py!r}); "
                            "mod = importlib.util.module_from_spec(spec); "
                            "spec.loader.exec_module(mod); "
                            f"mod.run_demo_on_tab({ws!r}, port={port})"
                        )
                        py_path = _find_project_python()
                        demo_log = _REPORT_DIR / "demo_subprocess.log"
                        _REPORT_DIR.mkdir(parents=True, exist_ok=True)
                        log_f = open(demo_log, "a")
                        proc = subprocess.Popen(
                            [py_path, "-c", inline_code],
                            stdout=log_f,
                            stderr=log_f,
                            start_new_session=True,
                        )
                        session._demo_pid = proc.pid
                    break
    except Exception:
        pass


def restore_stale_session_tabs(port: int = CDP_PORT,
                               keep_session_id: Optional[str] = None,
                               ) -> Dict[str, Any]:
    """Fix or close stale localhost session tabs after Chrome restart.

    When Chrome restores tabs from a previous profile, tabs pointing to an
    old (dead) HTTP server show "This site can't be reached".  For tabs
    belonging to the current session (matched by *keep_session_id* or any
    session in the active registry), this navigates them to the new port.
    Tabs from **unknown / expired sessions** are closed automatically so
    they don't accumulate across restarts.

    Returns: {"fixed": int, "closed": int, "session_id": str|None, "server_port": int}
    """
    import re
    result = {"fixed": 0, "closed": 0, "session_id": None, "server_port": 0}

    try:
        server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
        spec = importlib.util.spec_from_file_location("cdmcp_srv_restore", str(server_path))
        srv_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(srv_mod)

        server_url, srv_port = srv_mod.start_server()
        result["server_port"] = srv_port

        known_sids = set()
        for s in _sessions.values():
            known_sids.add(s.session_id[:8])
        if keep_session_id:
            known_sids.add(keep_session_id[:8])

        all_tabs = list_tabs(port)
        page_tabs = [t for t in all_tabs if t.get("type") == "page"]

        fixed = 0
        closed = 0
        session_id = None
        newtab_ws = None

        for tab in page_tabs:
            tab_url = tab.get("url", "")
            ws = tab.get("webSocketDebuggerUrl")
            if not ws:
                continue

            is_stale_http = (
                "127.0.0.1" in tab_url
                and ("/welcome" in tab_url or "/chat" in tab_url)
                and f":{srv_port}" not in tab_url
            )
            is_stale_file = (
                tab_url.startswith("file://")
                and ("session_id=" in tab_url or "welcome" in tab_url)
            )

            if is_stale_http or is_stale_file:
                m = re.search(r'session_id=([^&]+)', tab_url)
                tab_sid = m.group(1) if m else None

                if tab_sid and tab_sid not in known_sids:
                    try:
                        close_tab(tab.get("id", ""), port=port)
                        closed += 1
                    except Exception:
                        pass
                    continue

                new_url = re.sub(r'127\.0\.0\.1:\d+', f'127.0.0.1:{srv_port}', tab_url)
                try:
                    s = CDPSession(ws, timeout=10)
                    s.send_and_recv("Page.navigate", {"url": new_url})
                    s.close()
                    fixed += 1
                except Exception:
                    pass

                if tab_sid:
                    session_id = tab_sid

            elif tab_url in ("chrome://newtab/", "chrome://new-tab-page/"):
                newtab_ws = ws

            elif not tab_url or tab_url == "chrome://chromewebdata/":
                # Empty/error tabs from failed loads (dead server or stale session).
                # These provide no value — close them to avoid accumulation.
                try:
                    close_tab(tab.get("id", ""), port=port)
                    closed += 1
                except Exception:
                    pass

        if newtab_ws and session_id:
            chat_url = f"http://127.0.0.1:{srv_port}/chat?session_id={session_id}"
            try:
                s = CDPSession(newtab_ws, timeout=10)
                s.send_and_recv("Page.navigate", {"url": chat_url})
                s.close()
                fixed += 1
            except Exception:
                pass

        result["fixed"] = fixed
        result["closed"] = closed
        result["session_id"] = session_id
    except Exception:
        pass

    return result


def close_orphan_newtabs(session_window_id: Optional[int] = None,
                         port: int = CDP_PORT) -> int:
    """Close chrome://newtab/ tabs not in the given session window.

    Returns the number of tabs closed.
    """
    closed = 0
    if not session_window_id:
        return closed
    try:
        import urllib.request
        for t in list_tabs(port):
            url = t.get("url", "")
            ws = t.get("webSocketDebuggerUrl")
            if ws and url in ("chrome://newtab/", "chrome://new-tab-page/"):
                try:
                    s = CDPSession(ws, timeout=5)
                    resp = s.send_and_recv("Browser.getWindowForTarget", {})
                    tab_wid = resp.get("result", {}).get("windowId") if resp else None
                    s.close()
                    if tab_wid and tab_wid != session_window_id:
                        tid = t.get("id", "")
                        close_url = f"http://localhost:{port}/json/close/{tid}"
                        urllib.request.urlopen(close_url, timeout=3)
                        closed += 1
                except Exception:
                    pass
    except Exception:
        pass
    return closed


def start_demo_on_tab(srv_port: int, session_id: Optional[str] = None,
                      port: int = CDP_PORT) -> Optional[int]:
    """Start the demo subprocess on the chat tab. Returns the PID or None."""
    if not session_id:
        return None

    time.sleep(1.5)

    demo_ws = None
    for t in list_tabs(port):
        url = t.get("url", "")
        ws = t.get("webSocketDebuggerUrl")
        if ws and f":{srv_port}" in url and "/chat" in url:
            demo_ws = ws
            break

    if not demo_ws:
        return None

    demo_py = str(_TOOL_DIR / "logic" / "cdp" / "demo.py")
    project_root = str(_PROJECT_ROOT)

    py_path = _find_project_python()
    inline_code = (
        f"import sys, os; os.chdir({project_root!r}); "
        f"sys.path.insert(0, {project_root!r}); "
        "import importlib.util; "
        f"spec = importlib.util.spec_from_file_location('demo', {demo_py!r}); "
        "mod = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(mod); "
        f"mod.run_demo_on_tab({demo_ws!r}, port={port})"
    )

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _REPORT_DIR / "demo_subprocess.log"

    with open(log_file, "a") as lf:
        proc = subprocess.Popen(
            [py_path, "-c", inline_code],
            stdout=lf, stderr=lf,
            start_new_session=True,
        )
    return proc.pid


def boot_tool_session(
    session_name: str,
    timeout_sec: int = 86400,
    idle_timeout_sec: int = 3600,
    port: int = CDP_PORT,
) -> Dict[str, Any]:
    """Unified session boot for any tool.

    Session reuse strategy (in order of priority):
      1. Reuse an existing session with the same name if alive.
      2. Reuse ANY active session (shares the Chrome window).
      3. Create a new session + Chrome window as last resort.

    After boot, tools call session.require_tab() to open their specific tabs.

    Returns: {"ok": bool, "session": CDMCPSession, "action": str, ...}
      action is one of: "already_booted", "reused_active", "booted".
    """
    def _ensure_http_server():
        """Start or discover the shared persistent HTTP server."""
        server_path = _TOOL_DIR / "logic" / "cdp" / "server.py"
        spec = importlib.util.spec_from_file_location("cdmcp_srv_boot", str(server_path))
        srv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(srv)
        return srv.start_server()

    chrome_result = ensure_chrome(port)
    if not chrome_result["ok"]:
        return {"ok": False, "error": chrome_result.get("error", "Chrome not available"),
                "action": chrome_result.get("action", "chrome_failed")}

    # Fix stale tabs from a previous server; close tabs from dead sessions
    existing_for_stale = get_session(session_name)
    _keep_sid = existing_for_stale.session_id if existing_for_stale else None
    try:
        restore = restore_stale_session_tabs(
            port=port, keep_session_id=_keep_sid)
        if restore.get("fixed", 0) > 0 or restore.get("closed", 0) > 0:
            _log_session("boot:stale_fix", session_name,
                         f"Fixed {restore['fixed']}, closed {restore['closed']} stale tab(s)")
    except Exception:
        pass

    existing = get_session(session_name)
    if existing:
        cdp = existing.get_cdp()
        if cdp:
            server_url = None
            _srv_port = existing._http_port
            try:
                server_url, _srv_port = _ensure_http_server()
                port_changed = existing._http_port != _srv_port
                if port_changed:
                    existing._http_port = _srv_port
                    _save_state()

                # Refresh welcome tab URL if server port changed or URL is file://
                old_url = existing.lifetime_tab_url or ""
                needs_refresh = (
                    port_changed
                    or old_url.startswith("file://")
                    or ("127.0.0.1" in old_url and f":{_srv_port}" not in old_url)
                )
                if needs_refresh:
                    sid_short = existing.session_id[:8]
                    created_ts = int(existing.created_at)
                    new_welcome = (
                        f"{server_url}/welcome?session_id={sid_short}"
                        f"&port={port}&timeout_sec={existing.timeout_sec}"
                        f"&created_at={created_ts}"
                    )
                    existing.lifetime_tab_url = new_welcome
                    # Navigate the welcome tab to the new URL
                    try:
                        cdp.evaluate(f"window.location.href = {json.dumps(new_welcome)}")
                    except Exception:
                        pass
                    _save_state()
            except Exception:
                server_url = None
                _srv_port = existing._http_port

            _ensure_demo_tab(existing, server_url or f"http://127.0.0.1:{_srv_port}", port)

            try:
                overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
                spec = importlib.util.spec_from_file_location(
                    "cdmcp_ov_reboot", str(overlay_path))
                ov = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ov)
                if existing.lifetime_tab_id:
                    ov.pin_tab_by_target_id(
                        existing.lifetime_tab_id, pinned=True, port=port)
                sid_short = existing.session_id[:8]
                ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
                ov.inject_badge(cdp, text=f"CDMCP [{sid_short}]", color="#1a73e8")
                ov.inject_focus(cdp, color="#1a73e8")
            except Exception:
                pass

            try:
                auth_path = _TOOL_DIR / "logic" / "cdp" / "google_auth.py"
                auth_spec = importlib.util.spec_from_file_location(
                    "cdmcp_gauth_reboot", str(auth_path))
                auth_mod = importlib.util.module_from_spec(auth_spec)
                auth_spec.loader.exec_module(auth_mod)
                auth_mod.start_auth_monitor(
                    get_session_fn=lambda: get_session(session_name),
                    interval=1.0
                )
            except Exception:
                pass

            return {
                "ok": True, "action": "already_booted",
                "session": existing,
                "session_id": existing.session_id,
                "window_id": existing.window_id,
            }
        close_session(session_name)

    active = get_any_active_session()
    if active:
        cdp = active.get_cdp()
        if cdp:
            _sessions[session_name] = active
            _save_state()
            _log_session("reuse", session_name,
                         f"sharing window from '{active.name}'")
            try:
                server_url, _srv_port = _ensure_http_server()
                if active._http_port != _srv_port:
                    active._http_port = _srv_port
                    _save_state()
            except Exception:
                pass
            return {
                "ok": True, "action": "reused_active",
                "session": active,
                "session_id": active.session_id,
                "window_id": active.window_id,
            }

    session = create_session(
        session_name,
        timeout_sec=timeout_sec,
        idle_timeout_sec=idle_timeout_sec,
        port=port,
    )

    try:
        server_url, _srv_port = _ensure_http_server()
        session._http_port = _srv_port
    except Exception as e:
        return {"ok": False, "error": f"Server start failed: {e}"}

    sid_short = session.session_id[:8]
    created_ts = int(session.created_at)
    welcome_url = (
        f"{server_url}/welcome?session_id={sid_short}"
        f"&port={port}&timeout_sec={timeout_sec}&created_at={created_ts}"
    )

    boot_result = session.boot(welcome_url, new_window=True)
    if not boot_result.get("ok"):
        close_session(session_name)
        return {"ok": False, "error": boot_result.get("error", "Boot failed")}

    time.sleep(0.8)

    # Pin + overlays
    try:
        overlay_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
        spec = importlib.util.spec_from_file_location("cdmcp_ov_boot", str(overlay_path))
        ov = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ov)

        cdp = session.get_cdp()
        if cdp and session.lifetime_tab_id:
            ov.pin_tab_by_target_id(session.lifetime_tab_id, pinned=True, port=port)
            ov.activate_tab(session.lifetime_tab_id, port)
            ov.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
            ov.inject_badge(cdp, text=f"CDMCP [{sid_short}]", color="#1a73e8")
            ov.inject_focus(cdp, color="#1a73e8")
    except Exception:
        pass

    _ensure_demo_tab(session, server_url, port)

    # Start Google auth monitor for the ACCOUNT card
    try:
        auth_path = _TOOL_DIR / "logic" / "cdp" / "google_auth.py"
        auth_spec = importlib.util.spec_from_file_location("cdmcp_gauth", str(auth_path))
        auth_mod = importlib.util.module_from_spec(auth_spec)
        auth_spec.loader.exec_module(auth_mod)
        auth_mod.start_auth_monitor(
            get_session_fn=lambda: get_session(session_name),
            interval=1.0
        )
    except Exception:
        pass

    _save_state()

    return {
        "ok": True,
        "action": "booted",
        "session": session,
        "session_id": session.session_id,
        "window_id": session.window_id,
        **boot_result,
    }


# ---------------------------------------------------------------------------
# CDP-to-session lookup — allows interact module to touch owning session
# ---------------------------------------------------------------------------

def _find_session_by_cdp(cdp_session: CDPSession) -> Optional["CDMCPSession"]:
    """Find the CDMCPSession that owns *cdp_session*, matched by ws URL."""
    ws = getattr(cdp_session, "ws_url", None) or ""
    if not ws:
        return None
    for s in _sessions.values():
        if s.is_expired():
            continue
        for tab_info in s._tabs.values():
            if tab_info.get("ws") == ws:
                return s
        if s._cdp and getattr(s._cdp, "ws_url", None) == ws:
            return s
    return None


def touch_by_cdp(cdp_session: CDPSession):
    """Find the CDMCPSession that owns *cdp_session* and call touch().

    Matches by websocket URL against all registered tabs. This is called
    automatically by the interact module so that every MCP operation
    (mcp_click, mcp_type, mcp_navigate, etc.) resets the idle timer.
    """
    s = _find_session_by_cdp(cdp_session)
    if s:
        s.touch()


def increment_mcp_count_by_cdp(cdp_session: CDPSession) -> int:
    """Increment and return the persistent MPC counter for the session owning cdp_session."""
    s = _find_session_by_cdp(cdp_session)
    if s:
        s.mcp_count += 1
        _save_state()
        return s.mcp_count
    return 0


def get_mcp_count_by_cdp(cdp_session: CDPSession) -> int:
    """Return the persistent MPC counter for the session owning cdp_session."""
    s = _find_session_by_cdp(cdp_session)
    if s:
        return s.mcp_count
    return 0


def _cleanup_expired():
    """Clean up all expired sessions (idle + absolute timeout)."""
    expired = [n for n, s in _sessions.items() if s.is_expired()]
    for n in expired:
        info = _sessions[n].expiry_info()
        reason = "idle" if info.get("idle_expired") else "absolute"
        _log_session("expired_cleanup", n, f"reason={reason}")
        _sessions[n].close()
        del _sessions[n]
    if expired:
        _save_state()
    return expired


# ---------------------------------------------------------------------------
# Background watchdog thread — proactively cleans up expired sessions
# ---------------------------------------------------------------------------

_watchdog_thread: Optional[threading.Thread] = None
_watchdog_running = False
_WATCHDOG_INTERVAL_SEC = 60


def _watchdog_loop():
    """Background loop that periodically checks and cleans expired sessions."""
    global _watchdog_running
    while _watchdog_running:
        try:
            expired = _cleanup_expired()
            if expired:
                _log_session("watchdog", ",".join(expired),
                             f"cleaned {len(expired)} expired session(s)")
        except Exception:
            pass
        time.sleep(_WATCHDOG_INTERVAL_SEC)


def start_watchdog():
    """Start the background watchdog thread (idempotent)."""
    global _watchdog_thread, _watchdog_running
    if _watchdog_running:
        return
    _watchdog_running = True
    _watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True,
                                        name="cdmcp-watchdog")
    _watchdog_thread.start()


def stop_watchdog():
    """Stop the background watchdog thread."""
    global _watchdog_running
    _watchdog_running = False


# Auto-start watchdog when module loads if there are active sessions
if _sessions:
    start_watchdog()
