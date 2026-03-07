"""OAuth automation via Chrome DevTools Protocol.

Handles the Google OAuth consent flow when drive.mount() triggers an
authorization dialog in Colab.  Uses CDP Input.dispatchMouseEvent (real
user gestures) to click through the permission dialog and consent screens.
"""
import json
import time
import urllib.request
from typing import Optional, Callable

from tool.GOOGLE.logic.chrome.session import CDPSession, CDP_PORT, real_click


# ---------------------------------------------------------------------------
# Dialog & tab detection
# ---------------------------------------------------------------------------

def has_oauth_dialog(session: CDPSession) -> bool:
    """Return True if the Colab 'Connect to Google Drive' dialog is visible."""
    try:
        result = session.evaluate("""
            (function() {
                var all = document.querySelectorAll('md-text-button');
                for (var i = 0; i < all.length; i++) {
                    if ((all[i].innerText || '').trim() === 'Connect to Google Drive') return 'found';
                }
                return '';
            })()
        """)
        return result == "found"
    except Exception:
        return False


def click_connect_button(session: CDPSession) -> bool:
    """Real-click the 'Connect to Google Drive' button."""
    center = session.evaluate("""
        (function() {
            var all = document.querySelectorAll('md-text-button');
            for (var i = 0; i < all.length; i++) {
                if ((all[i].innerText || '').trim() === 'Connect to Google Drive') {
                    var r = all[i].getBoundingClientRect();
                    return JSON.stringify({x: r.x + r.width/2, y: r.y + r.height/2});
                }
            }
        })()
    """)
    if center:
        c = json.loads(center)
        real_click(session, c["x"], c["y"])
        return True
    return False


def find_oauth_tab(port: int = CDP_PORT) -> Optional[dict]:
    """Find an accounts.google.com OAuth popup tab."""
    try:
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=3) as resp:
            tabs = json.loads(resp.read().decode())
        for t in tabs:
            u = t.get("url", "")
            if t.get("type") == "page" and (
                "accounts.google.com/signin" in u
                or "accounts.google.com/o/oauth2" in u
            ):
                return t
    except Exception:
        pass
    return None


def close_oauth_tabs(port: int = CDP_PORT):
    """Close all accounts.google.com / RotateCookiesPage tabs."""
    try:
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=3) as resp:
            for t in json.loads(resp.read().decode()):
                u = t.get("url", "")
                if t.get("type") == "page" and "accounts.google.com" in u:
                    try:
                        cu = f"http://localhost:{port}/json/close/{t['id']}"
                        with urllib.request.urlopen(cu, timeout=3):
                            pass
                    except Exception:
                        pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Popup consent flow
# ---------------------------------------------------------------------------

def _find_and_click_button(session: CDPSession, text_match: str) -> bool:
    """Scroll a <button> into view and real-click it by visible text."""
    scrolled = session.evaluate(f"""
        (function() {{
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {{
                if (btns[i].innerText.trim().toLowerCase() === '{text_match}') {{
                    btns[i].scrollIntoView({{behavior: 'instant', block: 'center'}});
                    var r = btns[i].getBoundingClientRect();
                    return JSON.stringify({{x: r.x + r.width/2, y: r.y + r.height/2}});
                }}
            }}
            return null;
        }})()
    """)
    if scrolled:
        coords = json.loads(scrolled)
        time.sleep(0.3)
        real_click(session, coords["x"], coords["y"])
        return True
    return False


def _extract_oauth_url_from_output(session: CDPSession) -> Optional[str]:
    """Try to extract the OAuth URL from Colab cell output when popup is blocked."""
    try:
        url = session.evaluate("""
            (function(){
                var links = document.querySelectorAll('a[href*="accounts.google.com"]');
                for (var i = links.length - 1; i >= 0; i--) {
                    var h = links[i].href || '';
                    if (h.indexOf('oauth2') >= 0 || h.indexOf('signin') >= 0) return h;
                }
                var outputs = document.querySelectorAll('.output-content, .output_text');
                for (var j = outputs.length - 1; j >= 0; j--) {
                    var txt = outputs[j].textContent || '';
                    var m = txt.match(/https:\\/\\/accounts\\.google\\.com[^\\s"'<>]+/);
                    if (m) return m[0];
                }
                return '';
            })()
        """)
        return url if url else None
    except Exception:
        return None


def _open_url_as_tab(url: str, port: int) -> Optional[dict]:
    """Open a URL as a new tab via CDP, bypassing popup blocker."""
    try:
        req_url = f"http://localhost:{port}/json/new?{url}"
        with urllib.request.urlopen(req_url, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _handle_popup_consent(port: int, log_fn: Callable, timeout_s: int = 90,
                          colab_session: CDPSession = None) -> bool:
    """Wait for the OAuth popup, then click through consent screens.

    If the popup is blocked by Chrome, attempts to extract the OAuth URL
    from the Colab cell output and open it directly.
    """
    oauth_tab = None
    for _ in range(10):
        time.sleep(1)
        oauth_tab = find_oauth_tab(port)
        if oauth_tab:
            break

    if not oauth_tab:
        log_fn("No OAuth popup appeared - checking for popup blocked state")
        if colab_session:
            auth_url = _extract_oauth_url_from_output(colab_session)
            if auth_url:
                log_fn(f"Found OAuth URL in output - opening directly")
                new_tab = _open_url_as_tab(auth_url, port)
                if new_tab:
                    time.sleep(2)
                    oauth_tab = find_oauth_tab(port)
        if not oauth_tab:
            log_fn("Popup blocked: no OAuth popup and no fallback URL found")
            return False

    log_fn("OAuth popup opened")
    time.sleep(2)

    try:
        oauth_session = CDPSession(oauth_tab["webSocketDebuggerUrl"], timeout=15)
    except Exception as exc:
        log_fn(f"Failed to connect to OAuth popup: {exc}")
        return False

    consent_done = False
    for step in range(10):
        try:
            body = oauth_session.evaluate(
                "document.body ? document.body.innerText : ''"
            ) or ""
        except Exception:
            log_fn(f"OAuth popup closed/redirected at step {step + 1} - consent likely completed")
            consent_done = True
            break

        lower = body.lower()
        if "close this" in lower or "please close" in lower:
            log_fn(f"OAuth completed at step {step + 1}")
            consent_done = True
            break

        try:
            clicked = _find_and_click_button(oauth_session, "continue")
            if not clicked:
                clicked = _find_and_click_button(oauth_session, "allow")
            if not clicked:
                log_fn(f"No Continue/Allow at step {step + 1}")
        except Exception:
            log_fn(f"OAuth session lost at step {step + 1} - consent likely completed")
            consent_done = True
            break

        time.sleep(3)

    try:
        oauth_session.close()
    except Exception:
        pass

    close_oauth_tabs(port)
    return consent_done


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def handle_oauth_if_needed(
    session: CDPSession,
    port: int = CDP_PORT,
    dialog_timeout: int = 20,
    popup_timeout: int = 90,
    log_fn: Optional[Callable] = None,
    cell_done_fn: Optional[Callable] = None,
) -> str:
    """Detect the OAuth permission dialog and drive the consent flow.

    While polling for the dialog, *cell_done_fn* (if provided) is called
    each second.  If it returns True the cell finished without needing
    authorization and we return ``"not_needed"`` immediately.

    Returns:
        ``"not_needed"`` | ``"success"`` | ``"failed"``
    """
    _log = log_fn or (lambda m: None)

    for _ in range(dialog_timeout):
        time.sleep(1)

        if cell_done_fn and cell_done_fn():
            _log("Cell completed without OAuth")
            return "not_needed"

        if has_oauth_dialog(session):
            _log("OAuth dialog detected - clicking Connect")
            if not click_connect_button(session):
                _log("Failed to click Connect button")
                return "failed"
            time.sleep(1)

            _log("Navigating consent screens")
            ok = _handle_popup_consent(port, _log, popup_timeout,
                                       colab_session=session)
            return "success" if ok else "failed"

    _log("No OAuth dialog appeared within timeout")
    return "not_needed"
