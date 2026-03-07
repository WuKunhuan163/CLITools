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
from pathlib import Path
from typing import Optional, Dict, Any, List

from logic.chrome.session import (
    CDPSession, CDP_PORT, CDP_TIMEOUT,
    is_chrome_cdp_available, list_tabs, find_tab, open_tab, close_tab,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_SESSION_DIR = _TOOL_DIR / "data" / "sessions"
_REPORT_DIR = _TOOL_DIR / "data" / "report"

DEFAULT_TIMEOUT_SEC = 86400  # 24 hours


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


class CDMCPSession:
    """A named CDMCP session with a lifetime tab."""

    def __init__(self, name: str, timeout_sec: int = DEFAULT_TIMEOUT_SEC,
                 port: int = CDP_PORT):
        self.name = name
        self.session_id = str(uuid.uuid4())[:8]
        self.port = port
        self.timeout_sec = timeout_sec
        self.created_at = time.time()
        self.last_activity = time.time()
        self.lifetime_tab_id: Optional[str] = None
        self.lifetime_tab_url: Optional[str] = None
        self._cdp: Optional[CDPSession] = None
        self._booted = False
        self.tab_was_recovered = False
        self.window_id: Optional[int] = None
        self._tabs: Dict[str, Dict[str, Any]] = {}  # tab_label -> {id, url, ws, state}

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

    def open_tab_in_session(self, url: str) -> Optional[str]:
        """Open a new tab inside this session's window (not a new window).

        Returns the CDP target ID of the new tab, or None on failure.
        """
        if not self.window_id:
            return self._open_in_existing_window(url)

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
            return inner.get("targetId")
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
        return (time.time() - self.last_activity) > self.timeout_sec

    def close(self):
        """Close the session and its lifetime tab."""
        _log_session("close", self.name)
        if self._cdp:
            try:
                self._cdp.close()
            except Exception:
                pass
            self._cdp = None
        if self.lifetime_tab_id:
            close_tab(self.lifetime_tab_id, self.port)
            self.lifetime_tab_id = None
        self._booted = False

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
                    wait_sec: float = 10.0) -> Optional[Dict[str, Any]]:
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

        Returns:
            Dict ``{id, url, ws, label, recovered}`` or None.
        """
        self.touch()

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
                    return {"id": existing["id"], "url": existing["url"],
                            "ws": ws, "label": label, "recovered": False}

        # 2. Scan all tabs by URL pattern
        if url_pattern:
            for t in list_tabs(self.port):
                if url_pattern.lower() in (t.get("url", "") or "").lower() and t.get("type") == "page":
                    tab_id = t.get("id")
                    ws = t.get("webSocketDebuggerUrl", "")
                    self.register_tab(label, tab_id, url=t.get("url", ""), ws=ws)
                    _log_session("require_tab:found_by_url", self.name,
                                 f"label={label} id={tab_id}")
                    _save_state()
                    return {"id": tab_id, "url": t.get("url", ""),
                            "ws": ws, "label": label, "recovered": False}

        if not auto_open or not open_url:
            _log_session("require_tab:not_found", self.name,
                         f"label={label} auto_open={auto_open}")
            return None

        # 3. Ensure the session window is alive before opening a tab in it.
        #    If the window was closed, ensure_tab will reboot the lifetime
        #    tab in a fresh window and capture the new window_id.
        if self.lifetime_tab_url:
            self.ensure_tab()

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
                    return {"id": t["id"], "url": t.get("url", ""),
                            "ws": ws, "label": label, "recovered": True}

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
            "last_activity": self.last_activity,
            "expired": self.is_expired(),
            "age_sec": int(time.time() - self.created_at),
            "tabs": self.list_tabs_in_session(),
        }


# ---------------------------------------------------------------------------
# Persistent state file
# ---------------------------------------------------------------------------

_STATE_FILE = _SESSION_DIR / "state.json"


def _save_state():
    """Persist all session metadata to disk for cross-process sharing."""
    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
    state = {}
    for name, s in _sessions.items():
        state[name] = {
            "session_id": s.session_id,
            "window_id": s.window_id,
            "lifetime_tab_id": s.lifetime_tab_id,
            "lifetime_tab_url": s.lifetime_tab_url,
            "created_at": s.created_at,
            "last_activity": s.last_activity,
            "timeout_sec": s.timeout_sec,
            "port": s.port,
        }
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except OSError:
        pass


def _load_state():
    """Restore sessions from disk (window_id, tab_id, etc.)."""
    if not _STATE_FILE.exists():
        return
    try:
        with open(_STATE_FILE, "r") as f:
            state = json.load(f)
    except Exception:
        return
    for name, info in state.items():
        if name in _sessions:
            continue
        s = CDMCPSession(name, timeout_sec=info.get("timeout_sec", DEFAULT_TIMEOUT_SEC),
                         port=info.get("port", CDP_PORT))
        s.session_id = info.get("session_id", s.session_id)
        s.window_id = info.get("window_id")
        s.lifetime_tab_id = info.get("lifetime_tab_id")
        s.lifetime_tab_url = info.get("lifetime_tab_url")
        s.created_at = info.get("created_at", s.created_at)
        s.last_activity = info.get("last_activity", s.last_activity)
        s._booted = bool(s.lifetime_tab_id)
        if not s.is_expired():
            _sessions[name] = s


# ---------------------------------------------------------------------------
# Session Registry (module-level singleton)
# ---------------------------------------------------------------------------

_sessions: Dict[str, CDMCPSession] = {}
_load_state()


def create_session(name: str, timeout_sec: int = DEFAULT_TIMEOUT_SEC,
                   port: int = CDP_PORT) -> CDMCPSession:
    """Create a new named session (replaces any existing session with the same name)."""
    if name in _sessions:
        _sessions[name].close()
    session = CDMCPSession(name, timeout_sec=timeout_sec, port=port)
    _sessions[name] = session
    _log_session("create", name, f"timeout={timeout_sec}s")
    _save_state()
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


def _cleanup_expired():
    expired = [n for n, s in _sessions.items() if s.is_expired()]
    for n in expired:
        _sessions[n].close()
        del _sessions[n]
        _log_session("expired_cleanup", n)
    if expired:
        _save_state()
