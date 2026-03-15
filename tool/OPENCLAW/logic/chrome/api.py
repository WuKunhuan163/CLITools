"""Tencent Yuanbao (yuanbao.tencent.com) operations via CDMCP.

Uses the CDMCP session infrastructure for Chrome lifecycle management
and the authenticated yuanbao.tencent.com/chat session for conversation.
"""
import json
import time as _time
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
    open_tab,
)
from logic.cdmcp_loader import load_cdmcp_sessions

YUANBAO_URL_PATTERN = "yuanbao.tencent.com"
YUANBAO_CHAT_URL = "https://yuanbao.tencent.com/chat"


def find_yuanbao_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Yuanbao chat tab in Chrome."""
    return find_tab(YUANBAO_URL_PATTERN, port=port, tab_type="page")


def boot_yuanbao(port: int = CDP_PORT, wait: int = 8) -> Dict[str, Any]:
    """Boot OPENCLAW's Yuanbao session using CDMCP infrastructure.

    1. Use CDMCP's ensure_chrome() to guarantee Chrome is running.
    2. Boot a tool session via boot_tool_session().
    3. Open the Yuanbao tab via session.require_tab() or open_tab().
    4. Return auth state.
    """
    try:
        sessions = load_cdmcp_sessions()
    except ImportError:
        return {"ok": False, "error": "GOOGLE.CDMCP not installed. Run: TOOL install GOOGLE.CDMCP"}

    # Use ensure_chrome() to guarantee Chrome is running
    if hasattr(sessions, 'ensure_chrome'):
        chrome_result = sessions.ensure_chrome()
        if not chrome_result.get("ok"):
            return {"ok": False, "error": f"Chrome unavailable: {chrome_result.get('error', 'unknown')}"}
    elif not is_chrome_cdp_available(port):
        return {"ok": False, "error": "Chrome CDP not available and ensure_chrome() not found"}

    # Clean up stale OPENCLAW sessions before booting
    if hasattr(sessions, 'list_sessions') and hasattr(sessions, 'close_session'):
        try:
            for s in sessions.list_sessions():
                if s.get("name") == "OPENCLAW":
                    sessions.close_session("OPENCLAW")
        except Exception:
            pass

    # Boot a fresh CDMCP session for OPENCLAW
    if hasattr(sessions, 'boot_tool_session'):
        try:
            result = sessions.boot_tool_session("OPENCLAW", timeout_sec=86400, idle_timeout_sec=3600)
            session = result.get("session")
            if session and hasattr(session, 'require_tab'):
                session.require_tab("yuanbao", url_pattern=YUANBAO_URL_PATTERN,
                                    open_url=YUANBAO_CHAT_URL)
                _time.sleep(wait)
                return get_auth_state(port)
        except Exception:
            pass

    # Fallback: direct tab management
    tab = find_yuanbao_tab(port)
    if not tab:
        opened = open_tab(YUANBAO_CHAT_URL, port)
        if not opened:
            return {"ok": False, "error": "Failed to open Yuanbao tab"}
        _time.sleep(wait)
        tab = find_yuanbao_tab(port)
        if not tab:
            return {"ok": False, "error": "Yuanbao tab opened but not found after wait"}

    return get_auth_state(port)


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_yuanbao_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Yuanbao authentication state.

    Reliable detection: checks for explicit "nologin" class and whether
    send button is disabled, rather than just editor presence.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "Yuanbao tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;

                // Yuanbao-specific: nologin header class = definitely not logged in
                var nologin = document.querySelector('[class*="nologin"]');

                // Yuanbao-specific: login button present = not logged in
                var loginBtn = document.querySelector(
                    '[class*="tool__login"], [class*="Login"], button[class*="sign"]'
                );

                // Send button disabled = can't send = likely not logged in
                var sendBtn = document.querySelector('[class*="send-btn"]');
                var sendDisabled = sendBtn && sendBtn.className.includes('disabled');

                var chatInput = document.querySelector(
                    'textarea, [contenteditable="true"]'
                );

                var isAuthenticated = !!chatInput && !nologin && !loginBtn && !sendDisabled;

                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    authenticated: isAuthenticated,
                    hasInput: !!chatInput,
                    hasNologin: !!nologin,
                    hasLoginBtn: !!loginBtn,
                    sendDisabled: !!sendDisabled
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_conversations(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read sidebar conversation list from the DOM."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Yuanbao tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll(
                        '[class*="session-item"], [class*="conversation-item"], ' +
                        '[class*="chat-item"], [class*="history-item"], ' +
                        '[class*="sidebar"] [class*="item"]'
                    );
                    if (!items.length) {
                        var sidebar = document.querySelector(
                            '[class*="sidebar"], [class*="side-bar"], ' +
                            '[class*="nav"], [class*="session-list"]'
                        );
                        if (sidebar) {
                            items = sidebar.querySelectorAll('a, li, [role="listitem"]');
                        }
                    }
                    var convos = Array.from(items).slice(0, 50).map(function(el, idx) {
                        var title = el.textContent.trim().substring(0, 80);
                        var isActive = el.classList.contains('active') ||
                                       el.querySelector('.active') !== null ||
                                       el.getAttribute('aria-selected') === 'true';
                        return { index: idx, title: title, active: isActive };
                    }).filter(function(c) { return c.title.length > 0; });
                    return JSON.stringify({ok: true, count: convos.length, conversations: convos});
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


def create_conversation(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click the 'New Conversation' button and verify navigation.

    Yuanbao's SPA requires full mouse event chain (mousedown/mouseup/click).
    After clicking, verifies the URL changed to confirm new chat was created.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Yuanbao tab not found"}
    try:
        old_url = session.evaluate("window.location.href") or ""

        r = session.evaluate("""
            (function() {
                try {
                    var btn = document.querySelector('[class*="ic_newchat"]');
                    if (btn) {
                        var clickTarget = btn.closest('div[class*="trigger"]') || btn.parentElement || btn;
                        ["mousedown", "mouseup", "click"].forEach(function(type) {
                            clickTarget.dispatchEvent(new MouseEvent(type, {
                                bubbles: true, cancelable: true, view: window
                            }));
                        });
                        return JSON.stringify({ok: true, clicked: true, method: "icon_mouse"});
                    }
                    var buttons = document.querySelectorAll('button, [role="button"], a, div[class*="btn"]');
                    for (var i = 0; i < buttons.length; i++) {
                        var text = buttons[i].textContent.trim().toLowerCase();
                        if (text.includes('new') || text.includes('create') ||
                            text === '+') {
                            ["mousedown", "mouseup", "click"].forEach(function(type) {
                                buttons[i].dispatchEvent(new MouseEvent(type, {
                                    bubbles: true, cancelable: true, view: window
                                }));
                            });
                            return JSON.stringify({ok: true, clicked: true, method: "text_mouse"});
                        }
                    }
                    return JSON.stringify({ok: false, error: "New chat button not found"});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        result = json.loads(r) if r else {"ok": False, "error": "No response"}
        if not result.get("ok"):
            return result

        # Verify URL changed (new conversation = new URL path)
        for _ in range(10):
            _time.sleep(0.5)
            new_url = session.evaluate("window.location.href") or ""
            if new_url != old_url and "yuanbao.tencent.com" in new_url:
                result["new_url"] = new_url
                result["verified"] = True
                _time.sleep(2)
                return result

        # Fallback: navigate to chat root to get a fresh conversation
        session.evaluate("window.location.href = 'https://yuanbao.tencent.com/chat'")
        _time.sleep(3)
        final_url = session.evaluate("window.location.href") or ""
        result["new_url"] = final_url
        result["verified"] = final_url != old_url
        result["fallback"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def send_message(text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Type a message into the input area and send it.
    
    Supports Yuanbao's Quill editor (.ql-editor contenteditable) and generic
    textarea inputs. Uses full mouse event chain for the send button.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Yuanbao tab not found"}
    try:
        # Set content in the editor via a two-step approach:
        # 1. Focus the editor
        # 2. Clear + use Input.insertText which handles text correctly
        session.evaluate("""
            (function() {
                var editor = document.querySelector('.ql-editor');
                if (editor) {
                    editor.innerHTML = '';
                    editor.focus();
                    return 'quill';
                }
                var ta = document.querySelector('textarea');
                if (!ta) {
                    var all = document.querySelectorAll('[contenteditable="true"]');
                    for (var i = 0; i < all.length; i++) {
                        if (all[i].offsetHeight > 0) { ta = all[i]; break; }
                    }
                }
                if (ta) {
                    if (ta.tagName === 'TEXTAREA') { ta.value = ''; }
                    else { ta.innerHTML = ''; }
                    ta.focus();
                    return 'generic';
                }
                return 'none';
            })()
        """)
        _time.sleep(0.3)
        session.send_and_recv("Input.insertText", {"text": text})
        _time.sleep(0.5)
        _time.sleep(0.5)

        # Click send button with full mouse event chain
        sent = session.evaluate("""
            (function() {
                // Yuanbao: send button with icon-send
                var icon = document.querySelector('.icon-send');
                var btn = icon ? (icon.closest('a') || icon.parentElement) : null;
                
                if (!btn) {
                    btn = document.querySelector(
                        '[class*="send-btn"], [class*="send-button"], ' +
                        'button[class*="send"], [class*="submit-btn"]'
                    );
                }
                
                if (btn && btn.offsetParent !== null) {
                    ["mousedown", "mouseup", "click"].forEach(function(type) {
                        btn.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                    });
                    return 'clicked';
                }
                return 'no_button';
            })()
        """)

        if sent == "no_button":
            session.send_and_recv("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": "Enter", "code": "Enter",
                "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
            })
            _time.sleep(0.1)
            session.send_and_recv("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": "Enter", "code": "Enter",
                "windowsVirtualKeyCode": 13, "nativeVirtualKeyCode": 13,
            })

        _time.sleep(1)
        return {"ok": True, "sent": True, "method": "click" if sent == "clicked" else "enter"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def is_generating(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check if the agent is still generating a response.
    
    Yuanbao shows a stop button and streaming indicator during generation.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Yuanbao tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                // Yuanbao-specific: stop/regenerate button during generation
                var stopBtn = document.querySelector(
                    '[class*="stop-btn"], [class*="stop-generate"], ' +
                    '[class*="ic_stop"], [class*="ic_pause"], ' +
                    '[class*="stop"], [class*="Stop"], ' +
                    '[aria-label*="stop"], [aria-label*="Stop"]'
                );
                // Yuanbao: streaming/typing indicators
                var cursor = document.querySelector(
                    '[class*="cursor"], [class*="typing-indicator"], ' +
                    '[class*="blink"], [class*="streaming"], ' +
                    '[class*="generating"]'
                );
                var spinner = document.querySelector(
                    '[class*="spinner"], [class*="loading-dots"], ' +
                    '.animate-spin, [class*="thinking"], ' +
                    '[class*="deep-think"]'
                );
                // Yuanbao: check if send button is disabled (means generating)
                var sendBtn = document.querySelector('[class*="send-btn"]');
                var sendDisabled = sendBtn && (sendBtn.classList.contains('disabled') ||
                    sendBtn.getAttribute('aria-disabled') === 'true' ||
                    sendBtn.style.opacity === '0.5');
                
                return JSON.stringify({
                    ok: true,
                    generating: !!(stopBtn || cursor || spinner || sendDisabled),
                    hasStopBtn: !!stopBtn,
                    hasCursor: !!cursor,
                    hasSpinner: !!spinner,
                    sendDisabled: !!sendDisabled
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_last_response(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the last assistant message from the chat.
    
    Yuanbao renders responses in elements with class 'hyc-common-markdown'.
    Falls back to generic selectors for other UIs.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Yuanbao tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    // Yuanbao-specific: markdown response containers
                    var msgs = document.querySelectorAll('.hyc-common-markdown');
                    if (!msgs.length) {
                        msgs = document.querySelectorAll(
                            '[class*="markdown"], [class*="prose"], ' +
                            '[class*="message"], [class*="chat-msg"], ' +
                            '[class*="response"], [class*="answer"]'
                        );
                    }
                    if (!msgs.length) {
                        return JSON.stringify({ok: true, text: "", empty: true});
                    }
                    var last = msgs[msgs.length - 1];
                    var text = last.innerText || last.textContent || "";
                    return JSON.stringify({
                        ok: true,
                        text: text.trim(),
                        length: text.trim().length,
                        selector: last.className.substring(0, 60)
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


def _count_responses(port: int = CDP_PORT) -> int:
    """Count the total number of assistant response elements in the chat."""
    session = _get_session(port)
    if not session:
        return 0
    try:
        r = session.evaluate("""
            (function() {
                var msgs = document.querySelectorAll('.hyc-common-markdown');
                if (!msgs.length) {
                    msgs = document.querySelectorAll(
                        '[class*="markdown"], [class*="prose"], [class*="response"]'
                    );
                }
                return msgs.length;
            })()
        """)
        return int(r) if r else 0
    except Exception:
        return 0
    finally:
        session.close()


def wait_for_response(timeout: int = 120, poll_interval: float = 2.0,
                      port: int = CDP_PORT,
                      prev_response_count: int = -1) -> Dict[str, Any]:
    """Wait for a NEW response from the agent, then return it.

    Uses a two-phase approach:
    Phase 1: Wait for a new response to APPEAR (response count increases)
    Phase 2: Wait for generation to FINISH (is_generating becomes false)

    If prev_response_count is provided, we use it to detect new responses.
    Otherwise, we just wait for generation to stop (legacy behavior).
    """
    start = _time.time()
    _time.sleep(2)

    # Phase 1: Wait for a new response element to appear
    if prev_response_count >= 0:
        while _time.time() - start < timeout:
            current_count = _count_responses(port)
            if current_count > prev_response_count:
                break
            _time.sleep(poll_interval)
        else:
            resp = get_last_response(port)
            resp["timeout"] = True
            resp["response_count"] = _count_responses(port)
            return resp

    # Phase 2: Wait for generation to finish
    while _time.time() - start < timeout:
        status = is_generating(port)
        if not status.get("generating", True):
            break
        _time.sleep(poll_interval)

    if _time.time() - start >= timeout:
        resp = get_last_response(port)
        resp["timeout"] = True
        resp["response_count"] = _count_responses(port)
        return resp

    _time.sleep(1)
    resp = get_last_response(port)
    resp["response_count"] = _count_responses(port)
    return resp
