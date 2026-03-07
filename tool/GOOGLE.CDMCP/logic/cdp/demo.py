"""CDMCP Demo — Automated interaction sequence on the Chat app.

Drives the chat app with CDP to demonstrate CDMCP overlay features.
Supports both single-run and continuous loop modes.
"""

import json
import time
import random
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List

from logic.chrome.session import (
    CDPSession, CDP_PORT, find_tab, real_click, insert_text, dispatch_key,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_PATH = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_SERVER_PATH = _TOOL_DIR / "logic" / "cdp" / "server.py"

DEMO_MESSAGES = [
    "All 22 tests passing! CDMCP overlays working perfectly.",
    "Session system is live. Timeout set to 24 hours.",
    "Just finished the tab pinning feature.",
    "Badge, focus, lock, and highlight all operational.",
    "The Chat app demo is running in continuous mode.",
    "Privacy config allows OAuth by default -- configurable.",
    "Element highlight returns full metadata: tag, type, rect.",
    "Lock overlay flashes on user click. Nice UX touch.",
    "Tab grouping ensures all CDMCP tabs stay in one window.",
    "Running the full interaction sequence now...",
]

CONTACTS = ["alice", "bob", "carol", "dave", "team"]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_overlay():
    return _load_module("cdmcp_overlay", _OVERLAY_PATH)


def _load_session_mgr():
    return _load_module("cdmcp_session_mgr", _SESSION_PATH)


def _load_server():
    return _load_module("cdmcp_server", _SERVER_PATH)


def _step_log(step: int, total: int, msg: str):
    print(f"  [{step}/{total}] {msg}")


def _countdown_badge(overlay, cdp, seconds: int, prefix: str = "Next in"):
    """Show a countdown on the badge, updating every second."""
    for remaining in range(seconds, 0, -1):
        overlay.inject_badge(cdp, text=f"{prefix} {remaining}s", color="#ea8600")
        time.sleep(1)
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")


def _ensure_locked(overlay, cdp, relock_wait: float = 10.0):
    """If the lock was removed (user clicked unlock), wait then re-lock."""
    locked = overlay.is_locked(cdp)
    if not locked:
        print(f"  >> User unlocked. Re-locking in {relock_wait:.0f}s...")
        time.sleep(relock_wait)
        overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)


def _do_send_message(overlay, cdp, contact: str, message: str,
                     delay: float = 1.0) -> bool:
    """Execute one full send-message interaction on the chat app."""
    # Highlight and click contact
    hl = overlay.inject_highlight(
        cdp, f'.contact-item[data-contact="{contact}"]',
        label=f"Select: {contact}")
    time.sleep(delay * 0.5)

    rect = hl.get("rect", {})
    if rect:
        cx = rect.get("left", 0) + rect.get("width", 0) / 2
        cy = rect.get("top", 0) + rect.get("height", 0) / 2
        overlay.remove_highlight(cdp)
        real_click(cdp, cx, cy)
    time.sleep(delay * 0.5)

    # Highlight input
    overlay.inject_highlight(cdp, '#messageInput', label="Message input")
    time.sleep(delay * 0.3)

    # Focus and type
    cdp.evaluate("document.getElementById('messageInput').focus()")
    time.sleep(0.2)
    for char in message:
        insert_text(cdp, char)
        time.sleep(0.02)
    overlay.remove_highlight(cdp)
    time.sleep(delay * 0.3)

    # Highlight send button
    hl_btn = overlay.inject_highlight(cdp, '#sendBtn', label="Send")
    time.sleep(delay * 0.3)

    rect = hl_btn.get("rect", {})
    if rect:
        cx = rect.get("left", 0) + rect.get("width", 0) / 2
        cy = rect.get("top", 0) + rect.get("height", 0) / 2
        overlay.remove_highlight(cdp)
        real_click(cdp, cx, cy)
    time.sleep(delay * 0.3)

    # Verify
    last_msg = cdp.evaluate("""
        (function() {
            var msgs = document.querySelectorAll('.message.sent');
            if (msgs.length === 0) return '';
            return msgs[msgs.length - 1].querySelector('div').textContent;
        })()
    """)
    return message in str(last_msg or "")


def run_demo(port: int = CDP_PORT, delay: float = 1.5,
             continuous: bool = False) -> Dict[str, Any]:
    """Run the CDMCP demo. If continuous=True, loops through contacts/messages."""
    overlay = _load_overlay()
    session_mgr = _load_session_mgr()
    server_mod = _load_server()

    results = {"steps": [], "ok": True}

    # Step 1: Start server
    _step_log(1, 8, "Starting local chat server...")
    url, srv_port = server_mod.start_server()
    results["steps"].append({"step": 1, "action": "start_server", "ok": True, "url": url})
    time.sleep(0.5)

    # Step 2: Boot session
    _step_log(2, 8, "Creating CDMCP session and booting tab...")
    session = session_mgr.create_session("demo", timeout_sec=86400)
    boot_result = session.boot(url)
    results["steps"].append({"step": 2, "action": "boot", "ok": boot_result.get("ok", False)})
    if not boot_result.get("ok"):
        results["ok"] = False
        results["error"] = boot_result.get("error", "Boot failed")
        return results
    time.sleep(delay)

    # Step 3: Pin tab + set favicon + badge + focus
    _step_log(3, 8, "Pinning tab and applying overlays...")
    cdp = session.get_cdp()
    if not cdp:
        results["ok"] = False
        results["error"] = "Cannot get CDP session"
        return results

    # Pin the tab (bring to front)
    tab_id = session.lifetime_tab_id
    if tab_id:
        overlay.activate_tab(tab_id, port)

    overlay.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
    overlay.inject_focus(cdp, color="#1a73e8")
    results["steps"].append({"step": 3, "action": "pin_overlays", "ok": True})
    time.sleep(delay)

    if continuous:
        _step_log(4, 8, "Starting continuous demo loop (Ctrl+C to stop)...")
        overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
        msg_idx = 0
        contact_idx = 0
        try:
            while True:
                contact = CONTACTS[contact_idx % len(CONTACTS)]
                message = DEMO_MESSAGES[msg_idx % len(DEMO_MESSAGES)]
                print(f"  >> Sending to {contact}: {message[:50]}...")

                # Ensure CDP is still alive
                cdp = session.get_cdp()
                if not cdp:
                    print("  >> Lost CDP connection, attempting recovery...")
                    session.ensure_tab()
                    time.sleep(2)
                    cdp = session.get_cdp()
                    if not cdp:
                        print("  >> Recovery failed.")
                        break
                    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
                    overlay.inject_focus(cdp, color="#1a73e8")
                    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)

                # If user unlocked, wait 10s then re-lock
                _ensure_locked(overlay, cdp, relock_wait=10.0)

                # Keep lock visible but allow clicks through during interaction
                overlay.set_lock_passthrough(cdp, True)
                sent = _do_send_message(overlay, cdp, contact, message, delay=delay)
                overlay.set_lock_passthrough(cdp, False)
                status_text = "Delivered" if sent else "Not verified"
                print(f"  >> {status_text}.")

                msg_idx += 1
                contact_idx += 1

                # Countdown badge between interactions
                wait_sec = max(3, int(delay * 4))
                _countdown_badge(overlay, cdp, wait_sec, prefix="Next in")
        except KeyboardInterrupt:
            print("\n  >> Continuous demo stopped by user.")
        results["steps"].append({"step": 4, "action": "continuous_loop", "ok": True,
                                 "messages_sent": msg_idx})
    else:
        # Single-run: send one message to Bob
        _step_log(4, 8, "Highlighting contact 'Bob Martinez'...")
        hl = overlay.inject_highlight(cdp, '.contact-item[data-contact="bob"]',
                                       label="Select contact: Bob Martinez")
        results["steps"].append({"step": 4, "action": "highlight_contact",
                                 "ok": hl.get("ok", False)})
        time.sleep(delay)

        rect = hl.get("rect", {})
        if rect:
            cx = rect.get("left", 0) + rect.get("width", 0) / 2
            cy = rect.get("top", 0) + rect.get("height", 0) / 2
            overlay.remove_highlight(cdp)
            real_click(cdp, cx, cy)
        time.sleep(delay)

        _step_log(5, 8, "Locking tab...")
        overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
        results["steps"].append({"step": 5, "action": "lock", "ok": True})
        time.sleep(delay)

        _step_log(6, 8, "Typing message...")
        overlay.set_lock_passthrough(cdp, True)
        overlay.inject_highlight(cdp, '#messageInput', label="Message input")
        time.sleep(delay * 0.5)
        cdp.evaluate("document.getElementById('messageInput').focus()")
        time.sleep(0.3)
        msg = DEMO_MESSAGES[0]
        for char in msg:
            insert_text(cdp, char)
            time.sleep(0.03)
        overlay.remove_highlight(cdp)
        time.sleep(delay)

        _step_log(7, 8, "Clicking send...")
        hl_btn = overlay.inject_highlight(cdp, '#sendBtn', label="Send message")
        time.sleep(delay)
        rect = hl_btn.get("rect", {})
        if rect:
            overlay.remove_highlight(cdp)
            real_click(cdp, rect["left"] + rect["width"] / 2,
                       rect["top"] + rect["height"] / 2)
        time.sleep(delay)

        _step_log(8, 8, "Verifying...")
        last_msg = cdp.evaluate("""
            (function() {
                var msgs = document.querySelectorAll('.message.sent');
                if (msgs.length === 0) return '';
                return msgs[msgs.length - 1].querySelector('div').textContent;
            })()
        """)
        sent_ok = "CDMCP" in str(last_msg or "")
        results["steps"].append({"step": 8, "action": "verify", "ok": sent_ok})

    # For continuous mode, final badge shows after KeyboardInterrupt
    # For single mode, clean up and restore badge
    cdp = session.get_cdp()
    if cdp:
        overlay.remove_all_overlays(cdp)
        overlay.inject_badge(cdp, text="CDMCP Demo", color="#34a853")
        overlay.inject_favicon(cdp, svg_color="#34a853", letter="C")

    results["ok"] = all(s.get("ok", False) for s in results["steps"])
    return results
