"""Gmail operations via CDMCP (Chrome DevTools MCP).

Uses the authenticated ``mail.google.com`` session via CDP (port 9222).
Gmail's UI is a single-page app; data is read from the rendered DOM
(inbox rows, labels) and from the page title (unread count, email address).

Compose/send uses Gmail's compose window triggered by the Compose button,
then fills To/Subject/Body fields and clicks Send.
"""
import json
import time as _time
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

GMAIL_URL_PATTERN = "mail.google.com"


def find_gmail_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Gmail tab in Chrome."""
    return find_tab(GMAIL_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_gmail_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Gmail authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "Gmail tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var emailMatch = title.match(/([\\w.+-]+@[\\w-]+\\.[\\w.]+)/);
                var unreadMatch = title.match(/\\((\\d+)\\)/);
                var isSignin = url.includes("signin") || url.includes("accounts.google.com");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    email: emailMatch ? emailMatch[1] : null,
                    unreadCount: unreadMatch ? parseInt(unreadMatch[1]) : 0,
                    authenticated: !isSignin && url.includes("mail.google.com"),
                    isInbox: url.includes("#inbox")
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Gmail page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Gmail tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var hash = url.split("#")[1] || "";
                var section = hash.split("/")[0] || "inbox";
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    section: section
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_inbox(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """Read inbox emails from the DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Gmail tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var rows = document.querySelectorAll("tr.zA");
                    var emails = Array.from(rows).slice(0, %d).map(function(row) {
                        var isUnread = row.classList.contains("zE");
                        var from = row.querySelector(".yW .bA4, .yW .yP, .yW .zF");
                        var subj = row.querySelector(".bog");
                        var snip = row.querySelector(".y2");
                        var date = row.querySelector(".xW.xY span");
                        var starred = !!row.querySelector("[data-is-starred='true'], .T-KT-Jp");
                        return {
                            from: from ? from.textContent.trim() : "?",
                            subject: subj ? subj.textContent.trim().substring(0, 100) : "?",
                            snippet: snip ? snip.textContent.trim().substring(0, 100) : "",
                            date: date ? (date.getAttribute("title") || date.textContent.trim()) : "",
                            unread: isUnread,
                            starred: starred
                        };
                    });
                    return JSON.stringify({ok: true, count: emails.length, emails: emails});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """ % limit)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_labels(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read sidebar labels from the DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Gmail tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll(
                        "[data-type='navigation'] .aim, .TO .nU"
                    );
                    var labels = Array.from(items).slice(0, 30).map(function(el) {
                        var name = el.querySelector(".nU, a");
                        var count = el.querySelector(".bsU");
                        return {
                            name: name ? name.textContent.trim() : el.textContent.trim().substring(0, 40),
                            count: count ? count.textContent.trim() : null
                        };
                    }).filter(function(l) { return l.name.length > 0; });
                    return JSON.stringify({ok: true, count: labels.length, labels: labels});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def search_emails(query: str, limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search emails by typing into Gmail search box and reading results."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Gmail tab not found"}
    try:
        safe_query = query.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
        session.evaluate("""
            (function() {
                window.location.hash = "#search/%s";
            })()
        """ % safe_query.replace("/", "%2F"))

        import time
        time.sleep(5)

        r = session.evaluate("""
            (function() {
                try {
                    var rows = document.querySelectorAll("tr.zA");
                    var emails = Array.from(rows).slice(0, %d).map(function(row) {
                        var from = row.querySelector(".yW .bA4, .yW .yP, .yW .zF");
                        var subj = row.querySelector(".bog");
                        var snip = row.querySelector(".y2");
                        var date = row.querySelector(".xW.xY span");
                        return {
                            from: from ? from.textContent.trim() : "?",
                            subject: subj ? subj.textContent.trim().substring(0, 100) : "?",
                            snippet: snip ? snip.textContent.trim().substring(0, 100) : "",
                            date: date ? (date.getAttribute("title") || date.textContent.trim()) : ""
                        };
                    });
                    return JSON.stringify({ok: true, query: "%s", count: emails.length, emails: emails});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """ % (limit, safe_query))
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def send_email(to: str, subject: str, body: str,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """Compose and send an email via the Gmail web UI.

    Opens the Compose window, fills To/Subject/Body, and clicks Send.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Gmail tab not found"}
    try:
        session.evaluate('window.location.hash = "#inbox"')
        _time.sleep(2)

        # Click the Compose button
        session.evaluate("""
            (function() {
                var btn = document.querySelector("[gh='cm']") ||
                          document.querySelector("div.T-I.T-I-KE.L3");
                if (btn) btn.click();
            })()
        """)
        _time.sleep(3)

        has_compose = "no"
        for _ in range(6):
            has_compose = session.evaluate("""
                (function() {
                    var fields = document.querySelectorAll(
                        "input[aria-label='To recipients'], input[name='to']"
                    );
                    var visible = Array.from(fields).find(function(f) {
                        return f.offsetParent !== null;
                    });
                    return visible ? 'yes' : 'no';
                })()
            """)
            if has_compose == "yes":
                break
            _time.sleep(1)

        if has_compose != "yes":
            return {"ok": False, "error": "Compose window did not open"}

        # Fill the To field (find the visible one)
        session.evaluate("""
            (function() {
                var fields = document.querySelectorAll(
                    "input[aria-label='To recipients'], input[name='to']"
                );
                var toField = Array.from(fields).find(function(f) {
                    return f.offsetParent !== null;
                });
                if (toField) { toField.focus(); toField.click(); }
            })()
        """)
        _time.sleep(0.3)
        session.send_and_recv("Input.insertText", {"text": to})
        _time.sleep(0.5)
        # Press Enter to confirm the recipient as a chip
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Enter", "code": "Enter",
            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
        })
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Enter", "code": "Enter",
            "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
        })
        _time.sleep(1)

        # Fill Subject (find the visible one)
        session.evaluate("""
            (function() {
                var fields = document.querySelectorAll("input[name='subjectbox']");
                var subj = Array.from(fields).find(function(f) {
                    return f.offsetParent !== null;
                });
                if (subj) { subj.focus(); subj.click(); }
            })()
        """)
        _time.sleep(0.3)
        session.send_and_recv("Input.insertText", {"text": subject})
        _time.sleep(0.5)

        # Fill Body (find the visible one)
        session.evaluate("""
            (function() {
                var fields = document.querySelectorAll(
                    "div[aria-label='Message Body'], div[role='textbox'][aria-label*='Body']"
                );
                var body = Array.from(fields).find(function(f) {
                    return f.offsetParent !== null;
                });
                if (body) { body.focus(); body.click(); }
            })()
        """)
        _time.sleep(0.3)
        session.send_and_recv("Input.insertText", {"text": body})
        _time.sleep(0.5)

        # Click the visible Send button
        session.evaluate("""
            (function() {
                var btns = document.querySelectorAll("[data-tooltip*='Send']");
                var visible = Array.from(btns).find(function(b) {
                    return b.offsetParent !== null;
                });
                if (visible) visible.click();
            })()
        """)
        _time.sleep(3)

        # Check for "Message sent" up to 3 times
        sent = False
        for _ in range(3):
            r = session.evaluate("""
                (function() {
                    var body = document.body ? document.body.innerText : '';
                    return body.includes('Message sent') || body.includes('Undo') ? 'yes' : 'no';
                })()
            """)
            if r == "yes":
                sent = True
                break
            _time.sleep(1)

        return {"ok": True, "sent": sent}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
