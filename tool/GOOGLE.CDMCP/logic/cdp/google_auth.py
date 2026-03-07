"""Google account authentication monitoring for CDMCP sessions.

Provides:
- Lightweight cookie-based auth state checking via CDP (no rate limits)
- Background auth monitor that updates the welcome page ACCOUNT card
- Tab close detection for login/logout flows
- API for external tools to query Google login status
"""

import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List

from logic.chrome.session import CDPSession, CDP_PORT, list_tabs, close_tab


_AUTH_COOKIES = ("SID", "SSID", "APISID", "SAPISID", "HSID")
_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_REPORT_DIR = _TOOL_DIR / "data" / "report"
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"


def _load_overlay():
    """Lazy-load the overlay module."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("cdmcp_overlay_auth", str(_OVERLAY_PATH))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _log_auth(action: str, detail: str = ""):
    """Log auth events to a file for debugging."""
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    import datetime
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {action}"
    if detail:
        line += f" | {detail}"
    try:
        with open(_REPORT_DIR / "auth_log.txt", "a") as f:
            f.write(line + "\n")
    except OSError:
        pass

_auth_state: Dict[str, Any] = {
    "signed_in": False,
    "email": None,
    "display_name": None,
    "last_checked": 0,
}
_auth_lock = threading.Lock()
_monitor_thread: Optional[threading.Thread] = None
_monitor_running = False
_on_auth_change_callbacks: List[Callable] = []


# ---------------------------------------------------------------------------
# Cookie-based auth check (fast, local, no rate limits)
# ---------------------------------------------------------------------------

def check_auth_cookies(cdp: CDPSession) -> Dict[str, Any]:
    """Check Google auth state via cookies. No network requests.

    Requires calling Network.enable first (done automatically).
    """
    result = {"signed_in": False, "email": None, "display_name": None,
              "cookies_present": []}
    try:
        cdp.send_and_recv("Network.enable", {})
        resp = cdp.send_and_recv("Network.getCookies", {
            "urls": ["https://accounts.google.com",
                     "https://www.google.com",
                     "https://myaccount.google.com"]
        })
        cookies = (resp or {}).get("result", {}).get("cookies", [])
        found = set()
        for c in cookies:
            if c.get("name") in _AUTH_COOKIES:
                found.add(c["name"])
        result["cookies_present"] = sorted(found)
        result["signed_in"] = len(found) >= 3
    except Exception:
        pass
    return result


def check_auth_full(port: int = CDP_PORT) -> Dict[str, Any]:
    """Full auth check: cookies + DOM scrape for email/display name.

    Uses any available page tab for cookie check, then optionally
    navigates to myaccount.google.com for name/email extraction.
    """
    result = {"signed_in": False, "email": None, "display_name": None}

    tabs = list_tabs(port)
    for t in tabs:
        ws = t.get("webSocketDebuggerUrl")
        if ws and t.get("type") == "page":
            try:
                cdp = CDPSession(ws, timeout=5)
                cookie_result = check_auth_cookies(cdp)
                result["signed_in"] = cookie_result["signed_in"]

                if result["signed_in"] and "google.com" in (t.get("url") or ""):
                    info = cdp.evaluate('''
                        (function(){
                            var btn = document.querySelector('[aria-label*="Account"]');
                            if(!btn) return null;
                            var label = btn.getAttribute('aria-label') || '';
                            var m = label.match(/:\\s*(.+?)\\s*\\((.+?)\\)/);
                            if(m) return JSON.stringify({name: m[1].trim(), email: m[2].trim()});
                            return null;
                        })()
                    ''')
                    if info:
                        parsed = json.loads(info)
                        result["email"] = parsed.get("email")
                        result["display_name"] = parsed.get("name")
                cdp.close()
                if result["signed_in"]:
                    break
            except Exception:
                pass
    return result


# ---------------------------------------------------------------------------
# Cached state + callbacks
# ---------------------------------------------------------------------------

def get_cached_auth_state() -> Dict[str, Any]:
    """Return the cached auth state (updated by the monitor thread)."""
    with _auth_lock:
        return dict(_auth_state)


def _update_auth_state(new_state: Dict[str, Any]):
    """Update cached state and fire callbacks if signed_in changed."""
    global _auth_state
    with _auth_lock:
        old_signed_in = _auth_state.get("signed_in")
        if not new_state.get("signed_in"):
            new_state.pop("_probed", None)
            # Clear identity file on logout
            try:
                if _IDENTITY_FILE.exists():
                    _IDENTITY_FILE.unlink()
            except OSError:
                pass
        _auth_state.update(new_state)
        _auth_state["last_checked"] = time.time()

    if old_signed_in != new_state.get("signed_in"):
        for cb in _on_auth_change_callbacks:
            try:
                cb(new_state)
            except Exception:
                pass


def on_auth_change(callback: Callable):
    """Register a callback fired when signed_in state toggles."""
    _on_auth_change_callbacks.append(callback)


# ---------------------------------------------------------------------------
# Tab close detection (using CDP Target events)
# ---------------------------------------------------------------------------

_watched_tabs: Dict[str, Callable] = {}  # tab_id -> on_close_callback
_target_listener_active = False
_target_listener_lock = threading.Lock()


def watch_tab_close(tab_id: str, on_close: Callable):
    """Register a callback for when a specific tab is closed."""
    _watched_tabs[tab_id] = on_close
    _ensure_target_listener()


def _ensure_target_listener():
    """Start a browser-level CDP listener for Target.targetDestroyed."""
    global _target_listener_active
    with _target_listener_lock:
        if _target_listener_active:
            return
        _target_listener_active = True
    t = threading.Thread(target=_target_listener_loop, daemon=True,
                         name="cdmcp-target-listener")
    t.start()


def _target_listener_loop():
    """Listen for Target.targetDestroyed events on the browser CDP socket."""
    global _target_listener_active
    import urllib.request
    import websocket as _ws

    while _target_listener_active and _watched_tabs:
        try:
            ver_url = f"http://localhost:{CDP_PORT}/json/version"
            with urllib.request.urlopen(ver_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                time.sleep(2)
                continue

            sock = _ws.create_connection(browser_ws, timeout=5)
            msg_id = 9000
            sock.send(json.dumps({
                "id": msg_id,
                "method": "Target.setDiscoverTargets",
                "params": {"discover": True}
            }))

            while _target_listener_active and _watched_tabs:
                try:
                    raw = sock.recv()
                    msg = json.loads(raw)
                    method = msg.get("method", "")
                    if method == "Target.targetDestroyed":
                        destroyed_id = msg.get("params", {}).get("targetId", "")
                        cb = _watched_tabs.pop(destroyed_id, None)
                        if cb:
                            try:
                                cb(destroyed_id)
                            except Exception:
                                pass
                except _ws.WebSocketTimeoutException:
                    continue
                except Exception:
                    break

            try:
                sock.close()
            except Exception:
                pass

        except Exception:
            time.sleep(2)

    _target_listener_active = False


# ---------------------------------------------------------------------------
# Welcome page UI updater
# ---------------------------------------------------------------------------

def _update_welcome_ui(cdp: CDPSession, state: Dict[str, Any]):
    """Push auth state to the welcome page via CDP evaluate."""
    try:
        js_state = json.dumps({
            "signed_in": state.get("signed_in", False),
            "email": state.get("email"),
            "display_name": state.get("display_name"),
        })
        cdp.evaluate(
            f"if(window.__cdmcp_update_auth__) window.__cdmcp_update_auth__({js_state});"
        )
    except Exception:
        pass


def _check_welcome_click_action(cdp: CDPSession) -> Optional[str]:
    """Check if the user clicked the ACCOUNT card (login/logout action)."""
    try:
        action = cdp.evaluate("""
            (function(){
                var a = window.__cdmcp_account_action__;
                window.__cdmcp_account_action__ = null;
                return a;
            })()
        """)
        return action if action in ("login", "logout") else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Background monitor loop
# ---------------------------------------------------------------------------

def _monitor_loop(get_session_fn: Callable, interval: float):
    """Background loop: poll cookies, update welcome UI, handle card clicks."""
    global _monitor_running

    while _monitor_running:
        session = None
        try:
            session = get_session_fn()
        except Exception:
            pass

        if not session:
            time.sleep(interval)
            continue

        # 1. Check auth via cookies on any available tab
        cookie_state = {"signed_in": False, "email": None, "display_name": None}
        try:
            tabs = list_tabs(session.port)
            for t in tabs:
                ws = t.get("webSocketDebuggerUrl")
                if ws and t.get("type") == "page":
                    try:
                        cdp = CDPSession(ws, timeout=3)
                        cookie_state = check_auth_cookies(cdp)

                        if cookie_state["signed_in"] and "google.com" in (t.get("url") or ""):
                            info = cdp.evaluate('''
                                (function(){
                                    var btn = document.querySelector('[aria-label*="Account"]');
                                    if(!btn) return null;
                                    var label = btn.getAttribute('aria-label') || '';
                                    var m = label.match(/:\\s*(.+?)\\s*\\((.+?)\\)/);
                                    if(m) return JSON.stringify({name: m[1].trim(), email: m[2].trim()});
                                    return null;
                                })()
                            ''')
                            if info:
                                parsed = json.loads(info)
                                cookie_state["email"] = parsed.get("email")
                                cookie_state["display_name"] = parsed.get("name")

                        cdp.close()
                        if cookie_state.get("cookies_present"):
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        # Preserve email/name from previous probe if cookies still valid
        cached = get_cached_auth_state()
        if cookie_state.get("signed_in") and not cookie_state.get("email"):
            if cached.get("email"):
                cookie_state["email"] = cached["email"]
                cookie_state["display_name"] = cached.get("display_name")
            elif not cached.get("_probed"):
                try:
                    identity = _probe_identity(session)
                    if identity.get("email"):
                        cookie_state["email"] = identity["email"]
                        cookie_state["display_name"] = identity.get("display_name")
                        _push_identity_to_server(identity)
                except Exception as exc:
                    _log_auth("probe_error", str(exc))
                cookie_state["_probed"] = True

        _update_auth_state(cookie_state)

        # 2. Update the welcome page UI
        welcome_cdp = None
        try:
            welcome_cdp = session.get_cdp()
            if welcome_cdp:
                _update_welcome_ui(welcome_cdp, cookie_state)

                # 3. Check for user click action on the ACCOUNT card
                action = _check_welcome_click_action(welcome_cdp)
                if action:
                    _handle_account_action(session, action, welcome_cdp)
        except Exception:
            pass

        time.sleep(interval)


_IDENTITY_FILE = _TOOL_DIR / "data" / "sessions" / "google_identity.json"


def _push_identity_to_server(identity: Dict[str, Any]):
    """Persist identity to shared file for the HTTP /auth endpoint."""
    _IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_IDENTITY_FILE, "w") as f:
            json.dump({
                "email": identity.get("email"),
                "display_name": identity.get("display_name"),
            }, f)
        _log_auth("identity_cached", f"email={identity.get('email')}")
    except Exception:
        pass


def _probe_identity(session) -> Dict[str, Any]:
    """Open myaccount.google.com briefly to extract email and display name.

    Opens a tab, waits for content, scrapes account info, closes the tab.
    Returns dict with email/display_name if found.
    """
    result = {"email": None, "display_name": None}
    probe_url = "https://myaccount.google.com/"
    _log_auth("probe_start", f"session={session.name} window={session.window_id}")
    tab_id = session.open_tab_in_session(probe_url)
    _log_auth("probe_tab", f"tab_id={tab_id}")
    if not tab_id:
        return result

    time.sleep(3)
    tabs = list_tabs(session.port)
    cdp = None
    for t in tabs:
        if t.get("id") == tab_id:
            ws = t.get("webSocketDebuggerUrl", "")
            if ws:
                try:
                    cdp = CDPSession(ws, timeout=8)
                except Exception:
                    pass
            break

    if cdp:
        try:
            import re
            for _ in range(5):
                url = cdp.evaluate("window.location.href") or ""
                if "signin" in url or "ServiceLogin" in url:
                    break
                body = cdp.evaluate(
                    "document.body ? document.body.innerText.substring(0, 3000) : ''"
                ) or ""

                email_match = re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', body, re.I)
                if email_match:
                    result["email"] = email_match.group(0)
                    # Extract display name: text line just before email
                    lines = body.split("\n")
                    for i, line in enumerate(lines):
                        if result["email"] in line and i > 0:
                            candidate = lines[i - 1].strip()
                            if candidate and "@" not in candidate and len(candidate) < 60:
                                result["display_name"] = candidate
                            break

                if result["email"]:
                    _log_auth("probe_found", f"email={result['email']} name={result.get('display_name')}")
                    break
                time.sleep(1)
        except Exception as exc:
            _log_auth("probe_cdp_error", str(exc))
        try:
            cdp.close()
        except Exception:
            pass

    try:
        close_tab(tab_id, session.port)
    except Exception:
        pass
    return result


_LOGIN_TAB_ID: Optional[str] = None
_LOGIN_TRACKER_RUNNING = False


def _handle_account_action(session, action: str, welcome_cdp: CDPSession):
    """Handle a login or logout action triggered by the ACCOUNT card click."""
    if action == "login":
        initiate_login(session, welcome_cdp)
    elif action == "logout":
        initiate_logout(session, welcome_cdp)


def initiate_login(session, welcome_cdp: Optional[CDPSession] = None,
                   tip_text: str = "Please sign in to your Google account below",
                   poll_interval: float = 1.5,
                   auto_close: bool = True) -> Dict[str, Any]:
    """Open a login tab, show tip overlay, track auth, auto-close on success.

    Args:
        session: The active CDMCPSession.
        welcome_cdp: CDP session for the welcome page (for UI updates).
        tip_text: Text shown in the top-center tip banner on the login tab.
        poll_interval: How often to check auth cookies during login.
        auto_close: Whether to auto-close the login tab on successful auth.

    Returns:
        Dict with 'tab_id' and 'status' ('opened', 'already_signed_in').
    """
    global _LOGIN_TAB_ID

    cached = get_cached_auth_state()
    if cached.get("signed_in"):
        return {"status": "already_signed_in", "tab_id": None}

    signin_url = "https://accounts.google.com/signin/v2/identifier"

    if _LOGIN_TAB_ID:
        tabs = list_tabs(session.port)
        existing = any(t.get("id") == _LOGIN_TAB_ID for t in tabs)
        if existing:
            return {"status": "login_in_progress", "tab_id": _LOGIN_TAB_ID}
        _LOGIN_TAB_ID = None

    tab_id = session.open_tab_in_session(signin_url)
    if not tab_id:
        return {"status": "failed", "tab_id": None, "error": "Could not open login tab"}

    _LOGIN_TAB_ID = tab_id
    _log_auth("login_initiated", f"tab_id={tab_id}")

    t = threading.Thread(
        target=_login_tracker_loop,
        args=(session, tab_id, welcome_cdp, tip_text, poll_interval, auto_close),
        daemon=True, name="cdmcp-login-tracker",
    )
    t.start()

    return {"status": "opened", "tab_id": tab_id}


def _login_tracker_loop(session, tab_id: str,
                        welcome_cdp: Optional[CDPSession],
                        tip_text: str,
                        poll_interval: float,
                        auto_close: bool):
    """Background loop that tracks login tab state and auto-closes on success."""
    global _LOGIN_TAB_ID, _LOGIN_TRACKER_RUNNING
    _LOGIN_TRACKER_RUNNING = True

    _log_auth("tracker_start", f"tab_id={tab_id}")
    last_url = ""

    try:
        for cycle in range(300):
            if not _LOGIN_TRACKER_RUNNING:
                break

            tabs = list_tabs(session.port)
            tab_alive = False
            tab_ws = None
            tab_url = ""
            for t in tabs:
                if t.get("id") == tab_id:
                    tab_alive = True
                    tab_ws = t.get("webSocketDebuggerUrl")
                    tab_url = t.get("url", "")
                    break

            if not tab_alive:
                _log_auth("tracker_tab_closed", "User closed login tab")
                _force_auth_recheck(session, welcome_cdp)
                break

            url_changed = tab_url != last_url
            last_url = tab_url

            if tab_ws and (url_changed or cycle % 5 == 0):
                try:
                    cdp = CDPSession(tab_ws, timeout=5)
                    _ov_mod = _load_overlay()
                    if _ov_mod:
                        _ov_mod.inject_tip(cdp, tip_text, bg_color="#1a73e8")
                        _ov_mod.inject_badge(cdp, text="CDMCP Auth", color="#34a853")
                    cdp.close()
                except Exception:
                    pass

            if tab_ws:
                try:
                    cdp = CDPSession(tab_ws, timeout=3)
                    state = check_auth_cookies(cdp)
                    cdp.close()
                    if state.get("signed_in"):
                        _log_auth("tracker_login_detected", "Auth cookies present")
                        identity = _probe_identity(session)
                        if identity.get("email"):
                            state["email"] = identity["email"]
                            state["display_name"] = identity.get("display_name")
                            _push_identity_to_server(identity)
                        _update_auth_state(state)
                        if welcome_cdp:
                            _update_welcome_ui(welcome_cdp, state)
                        if auto_close:
                            time.sleep(0.8)
                            try:
                                close_tab(tab_id, session.port)
                                _log_auth("tracker_auto_closed", f"tab_id={tab_id}")
                            except Exception:
                                pass
                        break
                except Exception:
                    pass

            time.sleep(poll_interval)
    finally:
        _LOGIN_TAB_ID = None
        _LOGIN_TRACKER_RUNNING = False
        _log_auth("tracker_stopped", f"tab_id={tab_id}")


def initiate_logout(session, welcome_cdp: Optional[CDPSession] = None,
                    auto_close: bool = True) -> Dict[str, Any]:
    """Open a logout tab, track state, auto-close on completion.

    Args:
        session: The active CDMCPSession.
        welcome_cdp: CDP session for the welcome page (for UI updates).
        auto_close: Whether to auto-close the logout tab on completion.

    Returns:
        Dict with 'tab_id' and 'status'.
    """
    signout_url = "https://accounts.google.com/Logout"
    tab_id = session.open_tab_in_session(signout_url)
    if not tab_id:
        return {"status": "failed", "tab_id": None}

    _log_auth("logout_initiated", f"tab_id={tab_id}")

    t = threading.Thread(
        target=_logout_tracker_loop,
        args=(session, tab_id, welcome_cdp, auto_close),
        daemon=True, name="cdmcp-logout-tracker",
    )
    t.start()

    return {"status": "opened", "tab_id": tab_id}


def _logout_tracker_loop(session, tab_id: str,
                         welcome_cdp: Optional[CDPSession],
                         auto_close: bool):
    """Track logout tab: detect sign-out completion and auto-close."""
    _log_auth("logout_tracker_start", f"tab_id={tab_id}")

    try:
        for _ in range(60):
            tabs = list_tabs(session.port)
            tab_alive = any(t.get("id") == tab_id for t in tabs)

            if not tab_alive:
                _log_auth("logout_tab_closed", "User closed logout tab")
                break

            for t in tabs:
                ws = t.get("webSocketDebuggerUrl")
                if ws and t.get("type") == "page":
                    try:
                        cdp = CDPSession(ws, timeout=3)
                        state = check_auth_cookies(cdp)
                        cdp.close()
                        if not state.get("signed_in"):
                            _log_auth("logout_detected", "Auth cookies cleared")
                            _update_auth_state(state)
                            if welcome_cdp:
                                _update_welcome_ui(welcome_cdp, state)
                            if auto_close and tab_alive:
                                time.sleep(0.5)
                                try:
                                    close_tab(tab_id, session.port)
                                except Exception:
                                    pass
                            return
                    except Exception:
                        continue

            time.sleep(1.5)
    finally:
        _force_auth_recheck(session, welcome_cdp)
        _log_auth("logout_tracker_stopped", f"tab_id={tab_id}")


def _force_auth_recheck(session, welcome_cdp: CDPSession):
    """Immediately recheck auth state and update welcome UI."""
    try:
        tabs = list_tabs(session.port)
        for t in tabs:
            ws = t.get("webSocketDebuggerUrl")
            if ws and t.get("type") == "page":
                try:
                    cdp = CDPSession(ws, timeout=3)
                    state = check_auth_cookies(cdp)
                    cdp.close()
                    _update_auth_state(state)
                    break
                except Exception:
                    continue
        _update_welcome_ui(welcome_cdp, get_cached_auth_state())
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_auth_monitor(get_session_fn: Callable, interval: float = 1.0):
    """Start the background auth monitoring thread.

    Args:
        get_session_fn: Callable that returns the active CDMCPSession (or None).
        interval: Poll interval in seconds (default 1s, safe for cookie checks).
    """
    global _monitor_thread, _monitor_running
    if _monitor_running:
        return
    _monitor_running = True
    _monitor_thread = threading.Thread(
        target=_monitor_loop, args=(get_session_fn, interval),
        daemon=True, name="cdmcp-auth-monitor")
    _monitor_thread.start()


def stop_auth_monitor():
    """Stop the background auth monitoring thread."""
    global _monitor_running, _target_listener_active
    _monitor_running = False
    _target_listener_active = False
