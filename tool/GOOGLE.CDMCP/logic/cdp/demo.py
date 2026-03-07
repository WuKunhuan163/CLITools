"""CDMCP Demo — Continuous automated interaction on the Chat app.

Drives the chat app via CDP to demonstrate CDMCP overlay features.
Runs indefinitely, cycling through contacts and messages. When the user
unlocks the tab, the demo pauses with a countdown and auto-relocks
after 10 seconds of inactivity.

State is tracked via a Turing machine (DemoStateMachine) and persisted
to disk for real-time monitoring.
"""

import json
import time
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any

from logic.chrome.session import (
    CDPSession, CDP_PORT, find_tab, real_click, insert_text, dispatch_key,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_PATH = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_SERVER_PATH = _TOOL_DIR / "logic" / "cdp" / "server.py"
_INTERACT_PATH = _TOOL_DIR / "logic" / "cdp" / "interact.py"
_DEMO_STATE_PATH = _TOOL_DIR / "logic" / "cdp" / "demo_state.py"

DEMO_MESSAGES = [
    "All tests passing. CDMCP overlays working perfectly.",
    "Session system is live. Timeout set to 24 hours.",
    "Tab pinning feature complete. Extension API approach.",
    "Badge, focus, lock, and highlight all operational.",
    "Continuous demo running. No timeout, no stopping.",
    "Privacy config allows OAuth by default.",
    "Element highlight returns full metadata: tag, type, rect.",
    "Lock overlay flashes on user click. Auto-relocks in 10s.",
    "Each session opens in a dedicated Chrome window.",
    "MCP interaction interfaces: highlight + dwell + action.",
    "Turing machine tracks demo state in real time.",
    "Recovery detects tab closure and reboots automatically.",
]

DRAFT_MESSAGES = [
    "I was thinking about the architecture...",
    "Quick question about the deployment...",
    "Let me check the latest test results...",
]

CONTACTS = ["alice", "bob", "carol", "dave", "team"]

RELOCK_WAIT_SEC = 10
COUNTDOWN_SEC = 5


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


def _load_interact():
    return _load_module("cdmcp_interact", _INTERACT_PATH)


def _load_demo_state():
    return _load_module("cdmcp_demo_state", _DEMO_STATE_PATH)


def _log(msg: str):
    print(f"  >> {msg}")


def _recover_cdp(session, overlay, port):
    """Attempt to recover CDP connection and re-apply overlays."""
    session.ensure_tab()
    time.sleep(1.5)
    cdp = session.get_cdp()
    if cdp:
        tab_id = session.lifetime_tab_id
        if tab_id:
            overlay.activate_tab(tab_id, port)
            overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
        overlay.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
        overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
        overlay.inject_focus(cdp, color="#1a73e8")
        overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    return cdp


def run_demo(port: int = CDP_PORT, delay: float = 1.2,
             continuous: bool = True) -> Dict[str, Any]:
    """Run the CDMCP demo. Always continuous unless continuous=False for a single run."""
    overlay = _load_overlay()
    session_mgr = _load_session_mgr()
    server_mod = _load_server()
    interact = _load_interact()
    ds = _load_demo_state()
    machine = ds.get_demo_machine()
    machine.reset()

    results = {"steps": [], "ok": True}

    # -- Boot --
    machine.transition(ds.DemoState.BOOTING)
    _log("Starting local chat server...")
    base_url, srv_port = server_mod.start_server()
    time.sleep(0.3)

    _log("Creating session and booting tab...")
    session = session_mgr.create_session("demo", timeout_sec=86400)
    # Generate session ID for the chat title
    import hashlib
    ts = time.strftime("%m%d%H%M")
    sid = ts + hashlib.md5(session.session_id.encode()).hexdigest()[:4]
    url = f"{base_url}?session_id={sid}"
    boot_result = session.boot(url)
    if not boot_result.get("ok"):
        machine.transition(ds.DemoState.ERROR, {"error": boot_result.get("error")})
        results["ok"] = False
        results["error"] = boot_result.get("error", "Boot failed")
        return results

    time.sleep(0.8)
    cdp = session.get_cdp()
    if not cdp:
        machine.transition(ds.DemoState.ERROR, {"error": "No CDP session"})
        results["ok"] = False
        results["error"] = "Cannot get CDP session"
        return results

    # Pin immediately, then overlays
    tab_id = session.lifetime_tab_id
    if tab_id:
        overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
        overlay.activate_tab(tab_id, port)

    overlay.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
    overlay.inject_focus(cdp, color="#1a73e8")
    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    _log("Tab pinned and overlays applied.")
    results["steps"].append({"step": "boot", "ok": True})

    if not continuous:
        return _single_run(overlay, interact, cdp, session, machine, ds, delay, results)

    # -- Continuous loop --
    msg_idx = 0
    contact_idx = 0
    _log("Starting continuous demo (Ctrl+C to stop)...")

    try:
        while True:
            contact = CONTACTS[contact_idx % len(CONTACTS)]
            message = DEMO_MESSAGES[msg_idx % len(DEMO_MESSAGES)]

            # Check CDP health
            cdp = session.get_cdp()
            if not cdp:
                _log("Lost CDP connection. Recovering...")
                machine.transition(ds.DemoState.RECOVERING)
                cdp = _recover_cdp(session, overlay, port)
                if not cdp:
                    _log("Recovery failed. Retrying in 5s...")
                    machine.transition(ds.DemoState.ERROR, {"error": "CDP recovery failed"})
                    time.sleep(5)
                    continue
                machine.transition(ds.DemoState.SELECTING_CONTACT)

            # Check if user unlocked — wait with countdown then re-lock
            locked = overlay.is_locked(cdp)
            if not locked:
                machine.transition(ds.DemoState.WAITING_RELOCK, {"contact": contact})
                _log(f"User unlocked. Resuming in {RELOCK_WAIT_SEC}s...")
                for sec in range(RELOCK_WAIT_SEC, 0, -1):
                    machine.set_relock_remaining(float(sec))
                    overlay.inject_badge(cdp, text=f"Resuming in {sec}s", color="#ea8600")
                    time.sleep(1)
                    # Re-check: user might have closed tab during wait
                    cdp = session.get_cdp()
                    if not cdp:
                        break
                if cdp:
                    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
                    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
                    machine.set_relock_remaining(0)
                else:
                    continue

            _log(f"[{contact}] {message[:45]}...")
            machine.transition(ds.DemoState.SELECTING_CONTACT, {"contact": contact, "message": message})

            overlay.set_lock_passthrough(cdp, True)

            # Every 3rd cycle: draft demo (type partially, switch, come back)
            is_draft_cycle = (msg_idx % 3 == 2) and msg_idx > 0

            if is_draft_cycle:
                draft_text = DRAFT_MESSAGES[msg_idx % len(DRAFT_MESSAGES)]
                next_contact = CONTACTS[(contact_idx + 1) % len(CONTACTS)]

                # Type a draft message (don't send)
                interact.mcp_click(
                    cdp, f'.contact-item[data-contact="{contact}"]',
                    label=f"Select: {contact}", dwell=delay * 0.4,
                    unlock_for_click=False,
                )
                time.sleep(delay * 0.2)

                machine.transition(ds.DemoState.TYPING_MESSAGE)
                interact.mcp_type(
                    cdp, '#messageInput', draft_text,
                    label=f"Draft: {draft_text[:25]}...",
                    char_delay=0.04, manage_passthrough=False,
                )
                time.sleep(delay * 0.5)
                overlay.inject_badge(cdp, text="Draft saved", color="#5f6368")
                time.sleep(0.8)

                # Switch to another contact (draft is saved by chat app)
                interact.mcp_click(
                    cdp, f'.contact-item[data-contact="{next_contact}"]',
                    label=f"Switch to: {next_contact}", dwell=delay * 0.5,
                    unlock_for_click=False,
                )
                time.sleep(delay * 0.3)
                overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")

                # Come back to original contact (draft should be restored)
                interact.mcp_click(
                    cdp, f'.contact-item[data-contact="{contact}"]',
                    label=f"Back to: {contact}", dwell=delay * 0.4,
                    unlock_for_click=False,
                )
                time.sleep(delay * 0.2)

                # Clear draft and type the actual message
                cdp.evaluate("document.getElementById('messageInput').value = ''")
                time.sleep(0.1)

            # Regular flow: select contact
            if not is_draft_cycle:
                interact.mcp_click(
                    cdp, f'.contact-item[data-contact="{contact}"]',
                    label=f"Select: {contact}", dwell=delay * 0.6,
                    unlock_for_click=False,
                )
                time.sleep(delay * 0.3)

            # Type message
            machine.transition(ds.DemoState.TYPING_MESSAGE)
            interact.mcp_type(
                cdp, '#messageInput', message,
                label="Message input", char_delay=0.035,
                manage_passthrough=False,
            )
            time.sleep(delay * 0.2)

            # Send
            machine.transition(ds.DemoState.SENDING)
            interact.mcp_click(
                cdp, '#sendBtn', label="Send", dwell=delay * 0.4,
                unlock_for_click=False,
            )

            overlay.set_lock_passthrough(cdp, False)
            time.sleep(delay * 0.2)

            # Verify
            machine.transition(ds.DemoState.VERIFYING)
            last_msg = cdp.evaluate("""
                (function() {
                    var msgs = document.querySelectorAll('.message.sent');
                    if (msgs.length === 0) return '';
                    return msgs[msgs.length - 1].querySelector('div').textContent;
                })()
            """)
            delivered = message in str(last_msg or "")
            _log(f"{'Delivered' if delivered else 'Not verified'}.")

            msg_idx += 1
            contact_idx += 1

            # 5. Countdown between interactions
            machine.transition(ds.DemoState.COUNTDOWN)
            for sec in range(COUNTDOWN_SEC, 0, -1):
                machine.set_countdown(sec)
                overlay.inject_badge(cdp, text=f"Next in {sec}s", color="#ea8600")
                time.sleep(1)
                # Check unlock during countdown
                cdp = session.get_cdp()
                if cdp and not overlay.is_locked(cdp):
                    break
            if cdp:
                overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
            machine.set_countdown(0)

    except KeyboardInterrupt:
        _log("Stopped by user.")
        machine.transition(ds.DemoState.STOPPED)

    results["steps"].append({"step": "continuous", "ok": True, "messages_sent": msg_idx})
    results["ok"] = True
    return results


def _single_run(overlay, interact, cdp, session, machine, ds, delay, results):
    """Run a single demo interaction (non-looping)."""
    machine.transition(ds.DemoState.SELECTING_CONTACT, {"contact": "bob"})

    overlay.set_lock_passthrough(cdp, True)
    interact.mcp_click(
        cdp, '.contact-item[data-contact="bob"]',
        label="Select contact: Bob Martinez", dwell=delay,
        unlock_for_click=False,
    )
    time.sleep(delay * 0.5)

    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    machine.transition(ds.DemoState.TYPING_MESSAGE)

    msg = DEMO_MESSAGES[0]
    interact.mcp_type(cdp, '#messageInput', msg, label="Message input", char_delay=0.03)
    time.sleep(delay * 0.3)

    machine.transition(ds.DemoState.SENDING)
    interact.mcp_click(cdp, '#sendBtn', label="Send message", dwell=delay * 0.5, unlock_for_click=False)
    overlay.set_lock_passthrough(cdp, False)
    time.sleep(delay * 0.3)

    machine.transition(ds.DemoState.VERIFYING)
    last_msg = cdp.evaluate("""
        (function() {
            var msgs = document.querySelectorAll('.message.sent');
            if (msgs.length === 0) return '';
            return msgs[msgs.length - 1].querySelector('div').textContent;
        })()
    """)
    sent_ok = "CDMCP" in str(last_msg or "")
    results["steps"].append({"step": "single_run", "ok": sent_ok})

    cdp2 = session.get_cdp()
    if cdp2:
        overlay.remove_all_overlays(cdp2)
        overlay.inject_badge(cdp2, text="CDMCP Demo", color="#34a853")
        overlay.inject_favicon(cdp2, svg_color="#34a853", letter="C")

    machine.transition(ds.DemoState.STOPPED)
    results["ok"] = all(s.get("ok", False) for s in results["steps"])
    return results
