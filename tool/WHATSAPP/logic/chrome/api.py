"""WhatsApp Web operations via Chrome DevTools Protocol.

Uses the ``web.whatsapp.com`` session.  When linked (QR scanned),
the tool can read chats, search contacts, send messages, and read
profile info from the DOM.

Sending messages uses WhatsApp Web's URL scheme (``wa.me``) to open
a chat and then types + sends via the message input area.
"""
import json
import time as _time
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

WHATSAPP_URL_PATTERN = "web.whatsapp.com"


def find_whatsapp_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the WhatsApp Web tab in Chrome."""
    return find_tab(WHATSAPP_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_whatsapp_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check WhatsApp Web authentication / link state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var chatList = document.querySelector(
                    "[data-testid='chat-list'], [aria-label='Chat list'], #pane-side"
                );
                var searchBox = document.querySelector("[data-testid='chat-list-search']");
                var body = (document.body ? document.body.innerText : "").substring(0, 200);
                var needsQr = body.includes("Scan") || body.includes("Link with phone");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    authenticated: !!chatList || !!searchBox,
                    needsQrScan: needsQr && !chatList
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get WhatsApp Web page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_chats(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read visible chat list from the DOM (requires linked session)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var cells = document.querySelectorAll(
                        "[data-testid='cell-frame-container']"
                    );
                    if (!cells.length) {
                        var pane = document.querySelector("#pane-side");
                        if (pane) cells = pane.querySelectorAll("[role='listitem'], [role='row']");
                    }
                    var chats = Array.from(cells).slice(0, 30).map(function(el) {
                        var name = el.querySelector("[data-testid='cell-frame-title'] span, span[dir='auto']");
                        var msg = el.querySelector("[data-testid='last-msg-status'] span, span[title]");
                        var time = el.querySelector("[data-testid='cell-frame-primary-detail']");
                        var badge = el.querySelector("[data-testid='icon-unread-count'], [aria-label*='unread']");
                        return {
                            name: name ? name.textContent.trim().substring(0, 50) : "?",
                            lastMessage: msg ? msg.textContent.trim().substring(0, 80) : "",
                            time: time ? time.textContent.trim() : "",
                            unread: badge ? badge.textContent.trim() : null
                        };
                    });
                    return JSON.stringify({ok: true, count: chats.length, chats: chats});
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


def get_profile(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read profile info from WhatsApp Web (requires linked session)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var headerImg = document.querySelector(
                        "[data-testid='menu-bar-user-avatar'] img, header img"
                    );
                    var pushName = null;
                    try {
                        var ls = Object.keys(localStorage);
                        for (var i = 0; i < ls.length; i++) {
                            if (ls[i].includes("push") || ls[i].includes("name")) {
                                var v = localStorage.getItem(ls[i]);
                                if (v && v.length < 50 && v.length > 1) {
                                    pushName = v;
                                    break;
                                }
                            }
                        }
                    } catch(e) {}
                    return JSON.stringify({
                        ok: true,
                        data: {
                            avatarUrl: headerImg ? headerImg.src : null,
                            pushName: pushName
                        }
                    });
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


def search_contact(query: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search for a contact or chat by typing into the search box.

    Returns a list of matching results from the filtered chat/contact list.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        # Click the search box
        session.evaluate("""
            (function() {
                var search = document.querySelector(
                    "[data-testid='chat-list-search'], " +
                    "[contenteditable='true'][data-tab='3'], " +
                    "div[title='Search input textbox']"
                );
                if (search) { search.focus(); search.click(); }
            })()
        """)
        _time.sleep(0.5)

        safe_q = query.replace("\\", "\\\\").replace("'", "\\'")
        session.send_and_recv("Input.insertText", {"text": safe_q})
        _time.sleep(2)

        r = session.evaluate("""
            (function() {
                try {
                    var results = document.querySelectorAll(
                        "[data-testid='cell-frame-container']"
                    );
                    if (!results.length) {
                        var pane = document.querySelector("#pane-side");
                        if (pane) results = pane.querySelectorAll("[role='listitem'], [role='row']");
                    }
                    var contacts = Array.from(results).slice(0, 20).map(function(el) {
                        var name = el.querySelector("[data-testid='cell-frame-title'] span, span[dir='auto']");
                        return {
                            name: name ? name.textContent.trim().substring(0, 50) : el.textContent.trim().substring(0, 50)
                        };
                    });
                    return JSON.stringify({ok: true, count: contacts.length, contacts: contacts});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)

        # Clear the search by pressing Escape
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Escape", "code": "Escape",
            "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27,
        })

        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def send_message(phone: str, message: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Send a message to a phone number via WhatsApp Web.

    Uses the ``wa.me/<phone>`` deep link to open the chat, waits for
    the conversation to load, types the message, and clicks Send.

    ``phone`` should be digits only (e.g. ``85290549853``).
    """
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return {"ok": False, "error": "Invalid phone number"}

    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        # Navigate to the chat via wa.me URL scheme
        session.evaluate(
            'window.location.href = "https://web.whatsapp.com/send?phone=%s"' % digits
        )
        _time.sleep(5)

        # Wait for the message input to appear
        for _ in range(6):
            has_input = session.evaluate("""
                (function() {
                    var inp = document.querySelector(
                        "[data-testid='conversation-compose-box-input'], " +
                        "div[contenteditable='true'][data-tab='10']"
                    );
                    return inp ? 'yes' : 'no';
                })()
            """)
            if has_input == "yes":
                break
            _time.sleep(2)

        if has_input != "yes":
            # Check if there's an "invalid phone" message
            body = session.evaluate(
                "document.body ? document.body.innerText.substring(0,300) : ''"
            ) or ""
            return {"ok": False, "error": "Message input not found", "page": body[:150]}

        # Focus the compose box and type
        session.evaluate("""
            (function() {
                var inp = document.querySelector(
                    "[data-testid='conversation-compose-box-input'], " +
                    "div[contenteditable='true'][data-tab='10']"
                );
                if (inp) { inp.focus(); inp.click(); }
            })()
        """)
        _time.sleep(0.3)

        safe_msg = message.replace("\\", "\\\\").replace("'", "\\'")
        session.send_and_recv("Input.insertText", {"text": safe_msg})
        _time.sleep(0.5)

        # Click the send button
        session.evaluate("""
            (function() {
                var btn = document.querySelector(
                    "[data-testid='send'], button[aria-label='Send']"
                );
                if (btn) btn.click();
            })()
        """)
        _time.sleep(2)

        # Verify the message was sent by checking last outgoing message
        r = session.evaluate("""
            (function() {
                var msgs = document.querySelectorAll("[data-testid='msg-container'] [class*='message-out']");
                var last = msgs.length > 0 ? msgs[msgs.length - 1] : null;
                var lastText = last ? last.textContent.trim().substring(0, 100) : null;
                return JSON.stringify({ok: true, sent: !!last, lastOutgoing: lastText});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "sent": True, "note": "Could not verify"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
