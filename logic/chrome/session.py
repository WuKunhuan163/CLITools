"""Core Chrome DevTools Protocol (CDP) session management.

Generic building blocks for communicating with a Chrome instance running
with ``--remote-debugging-port``.  This module is service-agnostic: it
provides tab management, JS evaluation, input dispatch, and screenshot
capture that any tool can use.

Requirements:
    - Chrome with: --remote-debugging-port=9222 --remote-allow-origins=*
    - websocket-client (pip install websocket-client)
"""
import json
import time
import urllib.request
from typing import Optional, Dict, Any, List

CDP_PORT = 9222
CDP_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Chrome availability
# ---------------------------------------------------------------------------

def is_chrome_cdp_available(port: int = CDP_PORT) -> bool:
    """Check if Chrome DevTools Protocol is reachable on *port*."""
    try:
        url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return "Browser" in data
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tab helpers
# ---------------------------------------------------------------------------

def list_tabs(port: int = CDP_PORT) -> List[Dict[str, Any]]:
    """Return all Chrome targets as a list of dicts."""
    try:
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return []


def find_tab(url_pattern: str, port: int = CDP_PORT,
             tab_type: str = "page") -> Optional[Dict[str, Any]]:
    """Find a tab whose URL contains *url_pattern* (case-insensitive).

    Parameters
    ----------
    url_pattern : str
        Substring to match against tab URLs.
    tab_type : str
        Chrome target type filter (default ``"page"``).  Set to ``""``
        to match any type.

    Returns the first matching tab dict, or None.
    """
    pattern = url_pattern.lower()
    for tab in list_tabs(port):
        if tab_type and tab.get("type") != tab_type:
            continue
        if pattern in tab.get("url", "").lower():
            if tab.get("webSocketDebuggerUrl"):
                return tab
    return None


def close_tab(target_id: str, port: int = CDP_PORT) -> bool:
    """Close a Chrome tab by its target id."""
    try:
        url = f"http://localhost:{port}/json/close/{target_id}"
        with urllib.request.urlopen(url, timeout=3):
            pass
        return True
    except Exception:
        return False


def open_tab(url: str, port: int = CDP_PORT) -> bool:
    """Open a new tab in Chrome via the browser-level WebSocket."""
    try:
        ver_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(ver_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return False
        import websocket
        ws = websocket.create_connection(browser_ws, timeout=15)
        try:
            ws.send(json.dumps({
                "id": 1, "method": "Target.createTarget",
                "params": {"url": url},
            }))
            ws.settimeout(10)
            for _ in range(20):
                r = json.loads(ws.recv())
                if r.get("id") == 1:
                    return True
        finally:
            ws.close()
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# CDPSession
# ---------------------------------------------------------------------------

class CDPSession:
    """Lightweight Chrome DevTools Protocol session over WebSocket."""

    def __init__(self, ws_url: str, timeout: int = 30):
        import websocket
        self.ws_url = ws_url
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self._msg_id = 0

    def send_and_recv(self, method: str, params: dict = None,
                      timeout: int = CDP_TIMEOUT):
        self._msg_id += 1
        msg: Dict[str, Any] = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        self.ws.settimeout(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data = json.loads(self.ws.recv())
                if data.get("id") == self._msg_id:
                    return data
            except Exception:
                break
        return None

    def evaluate(self, expression: str, timeout: int = CDP_TIMEOUT) -> Any:
        """Evaluate JavaScript and return the result value."""
        result = self.send_and_recv("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        }, timeout=timeout)
        if result and "result" in result:
            r = result["result"].get("result", {})
            if "value" in r:
                return r["value"]
            return r.get("description", str(r))
        return None

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

def real_click(session: CDPSession, x: float, y: float):
    """Dispatch a real mouse-click event (satisfies Chrome user-gesture checks)."""
    session.send_and_recv("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x, "y": y,
        "button": "left", "clickCount": 1,
    }, timeout=5)
    time.sleep(0.05)
    session.send_and_recv("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x, "y": y,
        "button": "left", "clickCount": 1,
    }, timeout=5)


def insert_text(session: CDPSession, text: str):
    """Insert text at the current focus using Input.insertText."""
    session.send_and_recv("Input.insertText", {"text": text}, timeout=5)


def dispatch_key(session: CDPSession, key: str, code: str = "",
                 key_code: int = 0, event_type: str = "keyDown"):
    """Send a keyboard event."""
    params: Dict[str, Any] = {"type": event_type, "key": key}
    if code:
        params["code"] = code
    if key_code:
        params["windowsVirtualKeyCode"] = key_code
        params["nativeVirtualKeyCode"] = key_code
    session.send_and_recv("Input.dispatchKeyEvent", params, timeout=5)


def capture_screenshot(session: CDPSession, fmt: str = "png") -> Optional[bytes]:
    """Take a screenshot and return the raw image bytes (or None)."""
    import base64
    r = session.send_and_recv("Page.captureScreenshot",
                              {"format": fmt}, timeout=10)
    data = r.get("result", {}).get("data", "") if r else ""
    return base64.b64decode(data) if data else None


# ---------------------------------------------------------------------------
# DOM helpers
# ---------------------------------------------------------------------------

def get_dom_text(session: CDPSession, selector: str) -> Optional[str]:
    """Return the textContent of the first element matching *selector*."""
    js = f"document.querySelector({json.dumps(selector)})?.textContent ?? null"
    return session.evaluate(js)


def get_dom_attribute(session: CDPSession, selector: str, attr: str) -> Optional[str]:
    """Return an attribute value from the first element matching *selector*."""
    js = f"document.querySelector({json.dumps(selector)})?.getAttribute({json.dumps(attr)}) ?? null"
    return session.evaluate(js)


def query_selector_all_text(session: CDPSession, selector: str, limit: int = 50) -> list:
    """Return textContent of all elements matching *selector* (up to *limit*)."""
    js = f"""
        Array.from(document.querySelectorAll({json.dumps(selector)}))
            .slice(0, {limit})
            .map(el => el.textContent.trim())
    """
    result = session.evaluate(js)
    return result if isinstance(result, list) else []


def fetch_api(session: CDPSession, url: str, method: str = "GET",
              headers: dict = None, body: str = None,
              timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Perform a fetch() in the tab context and return parsed JSON.

    Uses the tab's existing cookies/auth for authenticated API calls.
    """
    opts: Dict[str, Any] = {"method": method, "credentials": "include"}
    if headers:
        opts["headers"] = headers
    if body:
        opts["body"] = body
    opts_json = json.dumps(opts)
    js = f"""
        (async function() {{
            try {{
                var resp = await fetch({json.dumps(url)}, {opts_json});
                var text = await resp.text();
                try {{ return JSON.stringify({{ok: resp.ok, status: resp.status, data: JSON.parse(text)}}); }}
                catch(_) {{ return JSON.stringify({{ok: resp.ok, status: resp.status, data: text}}); }}
            }} catch(e) {{
                return JSON.stringify({{ok: false, status: 0, data: e.toString()}});
            }}
        }})()
    """
    raw = session.evaluate(js, timeout=timeout)
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return None
