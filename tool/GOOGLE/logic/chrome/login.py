"""Google Account login/logout automation via Chrome DevTools Protocol.

Provides CDP-based functions to detect login state, sign out, and sign in
to a Google account in the CDMCP Chrome session (port 9222).

Security notes:
- Passwords are NEVER stored; they must be provided at runtime.
- Email can be persisted in config for convenience.
- Recovery codes are single-use and should be provided at runtime.
"""
import json
import time
from typing import Optional, Callable, Dict

from logic.chrome.session import (
    CDPSession, CDP_PORT, list_tabs, open_tab,
)


SIGNIN_URL = "https://accounts.google.com/signin/v2/identifier"
SIGNOUT_URL = "https://accounts.google.com/Logout"
MYACCOUNT_URL = "https://myaccount.google.com/"


def check_login_state(port: int = CDP_PORT, log_fn: Optional[Callable] = None) -> Dict:
    """Check if a Google account is signed in in the Chrome session.

    Returns dict with keys:
        signed_in (bool), email (str or None), display_name (str or None)
    """
    _log = log_fn or (lambda m: None)
    result = {"signed_in": False, "email": None, "display_name": None}

    tabs = list_tabs(port)
    google_tabs = [t for t in tabs if t.get("type") == "page"
                   and ("google.com" in t.get("url", "") or "colab" in t.get("url", ""))]

    cdp = None
    tab_to_close = None

    if not google_tabs:
        _log("No Google tab found. Opening myaccount to check login state...")
        open_tab(MYACCOUNT_URL, port)
        time.sleep(3)
        tabs = list_tabs(port)
        google_tabs = [t for t in tabs if t.get("type") == "page"
                       and "myaccount.google.com" in t.get("url", "")]
        if google_tabs:
            tab_to_close = google_tabs[0]["id"]

    if not google_tabs:
        _log("Cannot open Google page to check login state.")
        return result

    try:
        cdp = CDPSession(google_tabs[0]["webSocketDebuggerUrl"], timeout=10)
        url = cdp.evaluate("window.location.href") or ""

        if "accounts.google.com/signin" in url or "accounts.google.com/ServiceLogin" in url:
            _log("Redirected to sign-in page: not signed in.")
            return result

        state_json = cdp.evaluate('''
            (function(){
                var out = {signed_in: false, email: null, display_name: null};

                // Check aria-label on account button (contains email/name)
                var accountBtn = document.querySelector('[aria-label*="Account"]');
                if(accountBtn){
                    var label = accountBtn.getAttribute('aria-label') || '';
                    out.signed_in = true;
                    // Parse "Google Account: Name (email@gmail.com)"
                    var match = label.match(/:\\s*(.+?)\\s*\\((.+?)\\)/);
                    if(match){
                        out.display_name = match[1].trim();
                        out.email = match[2].trim();
                    }
                }

                // Fallback: check for user avatar image
                if(!out.signed_in){
                    var img = document.querySelector('img[data-profile-identifier]');
                    if(img) out.signed_in = true;
                }

                // Fallback: check body text for account name on myaccount page
                if(!out.email){
                    var body = document.body ? document.body.innerText : '';
                    var emailMatch = body.match(/([\\w.+-]+@[\\w.-]+\\.[a-z]{2,})/i);
                    if(emailMatch) out.email = emailMatch[1];
                }

                return JSON.stringify(out);
            })()
        ''')

        if state_json:
            parsed = json.loads(state_json)
            result.update(parsed)
            if result["signed_in"]:
                _log(f"Signed in as {result.get('email', 'unknown')}.")
            else:
                _log("Not signed in.")
    except Exception as e:
        _log(f"Error checking login state: {e}")
    finally:
        if cdp:
            try:
                cdp.close()
            except Exception:
                pass
        if tab_to_close:
            _close_tab(tab_to_close, port)

    return result


def sign_out(port: int = CDP_PORT, log_fn: Optional[Callable] = None) -> bool:
    """Sign out of the current Google account in the Chrome session."""
    _log = log_fn or (lambda m: None)

    _log("Navigating to Google sign-out page...")
    open_tab(SIGNOUT_URL, port)
    time.sleep(3)

    tabs = list_tabs(port)
    logout_tabs = [t for t in tabs if t.get("type") == "page"
                   and ("accounts.google.com" in t.get("url", ""))]

    if not logout_tabs:
        _log("Failed to find sign-out page.")
        return False

    try:
        cdp = CDPSession(logout_tabs[0]["webSocketDebuggerUrl"], timeout=10)
        url = cdp.evaluate("window.location.href") or ""

        # Google may show "Choose an account" or "Sign in" after logout
        body = (cdp.evaluate("document.body ? document.body.innerText.substring(0, 500) : ''") or "").lower()

        if "sign in" in body or "choose an account" in body or "signin" in url:
            _log("Successfully signed out.")
            cdp.close()
            _close_tab(logout_tabs[0]["id"], port)
            return True

        # May need to click "Sign out" confirmation button
        clicked = cdp.evaluate('''
            (function(){
                var btns = document.querySelectorAll('button, a, [role=button]');
                for(var i=0; i<btns.length; i++){
                    var text = (btns[i].innerText || '').trim().toLowerCase();
                    if(text === 'sign out' || text === 'log out'){
                        btns[i].click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()
        ''')
        if clicked == "clicked":
            time.sleep(3)
            _log("Clicked sign-out confirmation.")

        cdp.close()
        _close_tab(logout_tabs[0]["id"], port)
        return True

    except Exception as e:
        _log(f"Error during sign-out: {e}")
        return False


def sign_in(
    email: str,
    password: str,
    recovery_code: Optional[str] = None,
    port: int = CDP_PORT,
    log_fn: Optional[Callable] = None,
) -> Dict:
    """Sign in to a Google account via CDP automation.

    Args:
        email: Google account email.
        password: Account password (never stored).
        recovery_code: Optional 2FA backup code.
        port: Chrome CDP port.
        log_fn: Logging callback.

    Returns:
        dict with keys: success (bool), error (str or None), email (str)
    """
    _log = log_fn or (lambda m: None)
    result = {"success": False, "error": None, "email": email}

    _log("Opening Google sign-in page...")
    open_tab(SIGNIN_URL, port)
    time.sleep(3)

    tabs = list_tabs(port)
    signin_tabs = [t for t in tabs if t.get("type") == "page"
                   and "accounts.google.com" in t.get("url", "")]
    if not signin_tabs:
        result["error"] = "Failed to open sign-in page."
        return result

    cdp = None
    try:
        cdp = CDPSession(signin_tabs[0]["webSocketDebuggerUrl"], timeout=15)

        # Step 1: Enter email
        _log(f"Entering email: {email}")
        if not _wait_and_fill_input(cdp, "identifierId", email, log_fn=_log):
            if not _wait_and_fill_input(cdp, None, email, aria_label="Email or phone", log_fn=_log):
                result["error"] = "Could not find email input field."
                return result

        # Click Next
        if not _click_button_by_text(cdp, "Next", _log):
            if not _click_button_by_id(cdp, "identifierNext", _log):
                result["error"] = "Could not click Next after email."
                return result
        time.sleep(3)

        # Step 2: Enter password
        _log("Entering password...")
        url_after_email = cdp.evaluate("window.location.href") or ""
        if "challenge" in url_after_email or "signin/v2/challenge" in url_after_email:
            _log("2FA challenge detected before password.")
            if recovery_code:
                return _handle_2fa(cdp, recovery_code, result, _log)
            else:
                result["error"] = "2FA required but no recovery code provided."
                return result

        if not _wait_and_fill_input(cdp, None, password, input_type="password", log_fn=_log):
            body_text = (cdp.evaluate("document.body ? document.body.innerText.substring(0,300) : ''") or "")
            if "couldn't find" in body_text.lower() or "couldn't find" in body_text.lower():
                result["error"] = f"Google could not find account: {email}"
                return result
            result["error"] = "Could not find password input field."
            return result

        # Click Next
        if not _click_button_by_text(cdp, "Next", _log):
            if not _click_button_by_id(cdp, "passwordNext", _log):
                result["error"] = "Could not click Next after password."
                return result
        time.sleep(3)

        # Step 3: Check for 2FA or success
        url_after_password = cdp.evaluate("window.location.href") or ""
        body_text = (cdp.evaluate("document.body ? document.body.innerText.substring(0,500) : ''") or "")

        if "myaccount.google.com" in url_after_password or "google.com" in url_after_password:
            if "challenge" not in url_after_password and "signin" not in url_after_password:
                _log("Sign-in successful.")
                result["success"] = True
                return result

        if "wrong password" in body_text.lower():
            result["error"] = "Wrong password."
            return result

        if "2-step" in body_text.lower() or "challenge" in url_after_password:
            _log("2FA challenge detected.")
            if recovery_code:
                return _handle_2fa(cdp, recovery_code, result, _log)
            else:
                result["error"] = "2FA required but no recovery code provided."
                return result

        # Check if we're on a consent/terms page
        if "terms" in body_text.lower() or "agree" in body_text.lower():
            _click_button_by_text(cdp, "I agree", _log)
            time.sleep(2)

        # Final check
        final_url = cdp.evaluate("window.location.href") or ""
        if "signin" not in final_url and "challenge" not in final_url:
            _log("Sign-in appears successful.")
            result["success"] = True
        else:
            result["error"] = f"Sign-in flow stuck at: {final_url[:80]}"

    except Exception as e:
        result["error"] = str(e)
    finally:
        if cdp:
            try:
                cdp.close()
            except Exception:
                pass
        # Close the sign-in tab
        for t in list_tabs(port):
            if t.get("type") == "page" and "accounts.google.com" in t.get("url", ""):
                _close_tab(t["id"], port)

    return result


def _handle_2fa(cdp: CDPSession, recovery_code: str, result: dict,
                log_fn: Callable) -> dict:
    """Handle 2FA challenge using a recovery code."""
    log_fn("Attempting 2FA with recovery code...")

    # Click "Try another way" to access recovery codes
    time.sleep(1)
    _click_button_by_text(cdp, "Try another way", log_fn)
    time.sleep(2)

    # Look for "Enter one of your 8-digit backup codes"
    _click_link_containing(cdp, "backup code", log_fn)
    time.sleep(2)

    # Enter recovery code
    if not _wait_and_fill_input(cdp, None, recovery_code, log_fn=log_fn):
        result["error"] = "Could not find recovery code input field."
        return result

    # Click Next
    _click_button_by_text(cdp, "Next", log_fn)
    time.sleep(3)

    # Check result
    url = cdp.evaluate("window.location.href") or ""
    if "signin" not in url and "challenge" not in url:
        log_fn("2FA completed successfully.")
        result["success"] = True
    else:
        body = (cdp.evaluate("document.body ? document.body.innerText.substring(0,200) : ''") or "")
        if "wrong" in body.lower() or "invalid" in body.lower():
            result["error"] = "Invalid recovery code."
        else:
            result["error"] = f"2FA flow stuck at: {url[:80]}"

    return result


# ---------------------------------------------------------------------------
# CDP helpers
# ---------------------------------------------------------------------------

def _wait_and_fill_input(
    cdp: CDPSession,
    input_id: Optional[str],
    value: str,
    input_type: Optional[str] = None,
    aria_label: Optional[str] = None,
    timeout: int = 10,
    log_fn: Optional[Callable] = None,
) -> bool:
    """Wait for an input field and fill it with a value."""
    _log = log_fn or (lambda m: None)

    for _ in range(timeout):
        selector_parts = []
        if input_id:
            selector_parts.append(f"document.getElementById('{input_id}')")
        if input_type:
            selector_parts.append(f"document.querySelector('input[type=\"{input_type}\"]')")
        if aria_label:
            selector_parts.append(
                f"document.querySelector('input[aria-label=\"{aria_label}\"]')"
            )
        if not selector_parts:
            selector_parts.append("document.querySelector('input:not([type=hidden])')")

        js = " || ".join(selector_parts)
        value_escaped = json.dumps(value)

        filled = cdp.evaluate(f"""
            (function(){{
                var el = {js};
                if(!el) return false;
                el.focus();
                el.value = {value_escaped};
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return true;
            }})()
        """)

        if filled is True or filled == "true":
            return True
        time.sleep(1)

    _log("Input field not found within timeout.")
    return False


def _click_button_by_text(cdp: CDPSession, text: str,
                          log_fn: Optional[Callable] = None) -> bool:
    """Click a button/link by its visible text."""
    text_lower = text.lower()
    clicked = cdp.evaluate(f"""
        (function(){{
            var elems = document.querySelectorAll('button, [role=button], a');
            for(var i=0; i<elems.length; i++){{
                var t = (elems[i].innerText || '').trim().toLowerCase();
                if(t === '{text_lower}'){{
                    var r = elems[i].getBoundingClientRect();
                    if(r.width > 0 && r.height > 0){{
                        elems[i].click();
                        return 'clicked';
                    }}
                }}
            }}
            return 'not_found';
        }})()
    """)
    return clicked == "clicked"


def _click_button_by_id(cdp: CDPSession, btn_id: str,
                        log_fn: Optional[Callable] = None) -> bool:
    """Click a button by its DOM id (or inside shadow DOM)."""
    clicked = cdp.evaluate(f"""
        (function(){{
            var el = document.getElementById('{btn_id}');
            if(!el){{
                // Try shadow DOM
                var hosts = document.querySelectorAll('*');
                for(var i=0; i<hosts.length; i++){{
                    if(hosts[i].shadowRoot){{
                        el = hosts[i].shadowRoot.getElementById('{btn_id}');
                        if(el) break;
                    }}
                }}
            }}
            if(el){{
                el.click();
                return 'clicked';
            }}
            return 'not_found';
        }})()
    """)
    return clicked == "clicked"


def _click_link_containing(cdp: CDPSession, text_fragment: str,
                           log_fn: Optional[Callable] = None) -> bool:
    """Click a link/button whose text contains the given fragment."""
    fragment_lower = text_fragment.lower()
    clicked = cdp.evaluate(f"""
        (function(){{
            var elems = document.querySelectorAll('a, button, [role=button], [role=link]');
            for(var i=0; i<elems.length; i++){{
                var t = (elems[i].innerText || '').trim().toLowerCase();
                if(t.includes('{fragment_lower}')){{
                    elems[i].click();
                    return 'clicked';
                }}
            }}
            return 'not_found';
        }})()
    """)
    return clicked == "clicked"


def _close_tab(tab_id: str, port: int = CDP_PORT):
    """Close a Chrome tab by ID."""
    import urllib.request
    try:
        urllib.request.urlopen(
            f"http://localhost:{port}/json/close/{tab_id}", timeout=3
        )
    except Exception:
        pass
