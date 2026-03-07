"""CDMCP Demo -- Continuous automated chat interactions with visual effects.

Runs indefinitely, cycling through contacts with randomized timing, draft
messages, and simulated incoming messages. Auto-relocks 10s after user
unlock. State tracked by DemoStateMachine.
"""

import json
import time
import random
import hashlib
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

# Per-contact message pools (different personalities)
ALICE_MSGS = [
    "Just pushed the hotfix to staging.",
    "Can you review my latest commit?",
    "The API latency looks better after the cache update.",
    "I'll handle the frontend refactor this sprint.",
    "Test coverage went up to 94 percent.",
    "Noticed a flaky test in the auth module.",
    "Let's pair on the database migration tomorrow.",
    "The deployment script needs a rollback hook.",
    "Feature flag for dark mode is ready.",
    "Updated the CI config for parallel builds.",
    "Found a memory leak in the WebSocket handler.",
    "Rebased my branch on main, no conflicts.",
    "Docs for the new REST endpoints are up.",
    "Should we switch to gRPC for internal services?",
    "Performance benchmarks look promising.",
]

BOB_MSGS = [
    "Merged the PR for the payment module.",
    "The load test hit 10k concurrent users.",
    "Can we schedule a design review Thursday?",
    "I'm working on the notification service.",
    "Redis cluster is fully replicated now.",
    "Added rate limiting to the public API.",
    "The Kubernetes migration is 80 percent done.",
    "Grafana dashboards are live for the new service.",
    "Need your input on the caching strategy.",
    "Fixed the race condition in the queue worker.",
    "Our Docker images are 40 percent smaller now.",
    "The staging environment is back up.",
    "I'll write the post-mortem for yesterday's incident.",
    "TypeScript strict mode uncovered 12 issues.",
    "Let's move the meeting to 2pm.",
]

CAROL_MSGS = [
    "Design specs for the settings page are finalized.",
    "Can we discuss the onboarding flow changes?",
    "The accessibility audit passed with minor notes.",
    "I'm updating the component library to v3.",
    "User research results are in the shared drive.",
    "New mockups for the dashboard are ready.",
    "Should we A/B test the new checkout flow?",
    "The design system tokens are documented.",
    "Mobile responsive fixes are deployed.",
    "Analytics show 15 percent improvement in retention.",
    "Working on the search UX improvements.",
    "The icon set migration is complete.",
    "Color contrast ratios all pass WCAG AA.",
    "Let's sync on the Q2 roadmap priorities.",
    "Prototyped the new navigation pattern.",
]

DAVE_MSGS = [
    "CI pipeline runs are down to 4 minutes.",
    "Set up automated security scanning.",
    "The new monitoring alerts caught 3 issues today.",
    "Infrastructure costs dropped 20 percent this month.",
    "Terraform modules are version-locked now.",
    "Backup restoration test passed successfully.",
    "SSL certificates auto-renew is configured.",
    "Database replication lag is under 100ms.",
    "Set up log aggregation with structured output.",
    "The disaster recovery plan is documented.",
    "Container registry cleanup saved 50GB.",
    "Network policies are enforced in production.",
    "Load balancer health checks are optimized.",
    "Upgraded the cluster to the latest patch.",
    "Secrets rotation is automated now.",
]

TEAM_MSGS = [
    "Sprint retrospective at 4pm today.",
    "Release v2.4 is scheduled for Friday.",
    "Please update your status in the tracker.",
    "New hire onboarding session Wednesday.",
    "Quarterly planning starts next week.",
    "Reminder: code freeze starts Thursday.",
    "Lunch and learn on observability tomorrow.",
    "Team velocity improved by 18 percent.",
    "Bug bash results: 23 issues resolved.",
    "Architecture review meeting rescheduled.",
    "Please review the updated coding standards.",
    "Hackathon projects due by end of sprint.",
    "Cross-team sync moved to Monday.",
    "Holiday schedule posted in the wiki.",
    "New feature request from the product team.",
]

CONTACT_MSGS = {
    "alice": ALICE_MSGS, "bob": BOB_MSGS, "carol": CAROL_MSGS,
    "dave": DAVE_MSGS, "team": TEAM_MSGS,
}

INCOMING_MSGS = {
    "alice": ["Hey, quick question about the API.", "The tests are green now.",
              "Can you check the staging deployment?", "Updated the docs."],
    "bob": ["Just deployed the fix.", "Meeting moved to 3pm.",
            "Need your review on the PR.", "Benchmark results are in."],
    "carol": ["New mockups uploaded.", "Design review in 10 minutes.",
              "Updated the style guide.", "Accessibility fixes pushed."],
    "dave": ["Monitoring alert cleared.", "Backup completed successfully.",
             "Infrastructure change applied.", "Logs look clean."],
    "team": ["Standup in 5 minutes.", "Sprint goal updated.",
             "New ticket assigned to you.", "Release notes drafted."],
}

CONTACTS = ["alice", "bob", "carol", "dave", "team"]
RELOCK_WAIT_SEC = 10
COUNTDOWN_MIN = 3
COUNTDOWN_MAX = 6


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_overlay(): return _load_module("cdmcp_overlay", _OVERLAY_PATH)
def _load_session_mgr(): return _load_module("cdmcp_session_mgr", _SESSION_PATH)
def _load_server(): return _load_module("cdmcp_server", _SERVER_PATH)
def _load_interact(): return _load_module("cdmcp_interact", _INTERACT_PATH)
def _load_demo_state(): return _load_module("cdmcp_demo_state", _DEMO_STATE_PATH)


def _log(msg):
    print(f"  >> {msg}", flush=True)


def _now():
    return time.strftime("%H:%M:%S")


def _is_unlocked(overlay, cdp):
    """Quick check: return True if the tab is not locked (user took control)."""
    try:
        return not overlay.is_locked(cdp)
    except Exception:
        return False


def _check_and_relock(overlay, cdp, session, machine, ds, port):
    """Check if user unlocked, wait 10s with countdown, then re-lock.

    If the user clicks the "Start Demo" button, re-lock immediately.
    Returns the (possibly refreshed) cdp session, or None if unrecoverable.
    """
    cdp = session.get_cdp()
    if not cdp:
        return None

    if overlay.is_locked(cdp):
        return cdp

    overlay.set_lock_passthrough(cdp, False)

    machine.transition(ds.DemoState.WAITING_RELOCK)
    _log(f"User unlocked. Resuming in {RELOCK_WAIT_SEC}s...")

    for sec in range(RELOCK_WAIT_SEC, 0, -1):
        machine.set_relock_remaining(float(sec))
        overlay.inject_badge(cdp, text=f"Resuming in {sec}s", color="#ea8600")
        time.sleep(1)
        cdp = session.get_cdp()
        if not cdp:
            return None
        try:
            takeover = cdp.evaluate("window._isDemoTakeoverRequested ? window._isDemoTakeoverRequested() : false")
            if takeover:
                _log("Manual takeover requested. Re-locking immediately.")
                break
        except Exception:
            pass

    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
    machine.set_relock_remaining(0)
    _log("Re-locked.")
    return cdp


def _simulate_incoming(cdp, overlay, contact_idx, msg_idx):
    """Randomly send an incoming message from another contact."""
    if random.random() > 0.35:
        return
    other = random.choice([c for c in CONTACTS if c != CONTACTS[contact_idx % len(CONTACTS)]])
    msgs = INCOMING_MSGS.get(other, [])
    if not msgs:
        return
    text = msgs[random.randint(0, len(msgs) - 1)]
    cdp.evaluate(f"window.receiveMessage({json.dumps(other)}, {json.dumps(text)})")
    _log(f"[incoming] {other}: {text[:40]}")


def _recover_cdp(session, overlay, port):
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


def run_demo(port=CDP_PORT, delay=1.2, continuous=True):
    overlay = _load_overlay()
    session_mgr = _load_session_mgr()
    server_mod = _load_server()
    interact = _load_interact()
    ds = _load_demo_state()
    machine = ds.get_demo_machine()
    machine.reset()

    results = {"steps": [], "ok": True}

    machine.transition(ds.DemoState.BOOTING)
    _log("Preparing chat page...")
    chat_html = _TOOL_DIR / "data" / "chat_app.html"
    time.sleep(0.3)

    _log("Creating session and booting tab...")
    session = session_mgr.create_session("demo", timeout_sec=86400)
    ts = time.strftime("%m%d%H%M")
    sid = ts + hashlib.md5(session.session_id.encode()).hexdigest()[:4]
    url = f"file://{chat_html}?session_id={sid}"
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
        return results

    tab_id = session.lifetime_tab_id
    if tab_id:
        overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
        overlay.activate_tab(tab_id, port)

    overlay.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
    overlay.inject_focus(cdp, color="#1a73e8")
    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)

    # Start the timer overlay
    cdp.evaluate("window.startDemoTimer()")

    _log(f"Tab pinned. Session [{sid}].")
    results["steps"].append({"step": "boot", "ok": True, "session_id": sid})

    if not continuous:
        return _single_run(overlay, interact, cdp, session, machine, ds, delay, results)

    _run_continuous_loop(overlay, interact, cdp, session, machine, ds, delay, results, port)
    return results


def run_demo_on_tab(cdp_ws_url: str, port=CDP_PORT, delay=1.2):
    """Run the continuous demo on an already-open chat tab identified by WS URL.

    Designed to be called from a background thread.
    """
    overlay = _load_overlay()
    interact = _load_interact()
    ds = _load_demo_state()
    session_mgr = _load_session_mgr()
    machine = ds.get_demo_machine()
    machine.reset()
    machine.transition(ds.DemoState.BOOTING)

    cdp = CDPSession(cdp_ws_url, timeout=10)
    time.sleep(0.5)

    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    cdp.evaluate("window.startDemoTimer()")

    machine.transition(ds.DemoState.IDLE)

    class _FakeSession:
        def __init__(self, c, ws):
            self._cdp = c
            self._ws = ws
            self.lifetime_tab_id = None
        def get_cdp(self):
            if self._cdp:
                try:
                    self._cdp.send_and_recv("Runtime.evaluate",
                                            {"expression": "1"}, timeout=3)
                    return self._cdp
                except Exception:
                    self._cdp = None
            try:
                self._cdp = CDPSession(self._ws, timeout=10)
                return self._cdp
            except Exception:
                return None
        def ensure_tab(self):
            return self.get_cdp() is not None

    session = _FakeSession(cdp, cdp_ws_url)
    results = {"steps": [], "ok": True}
    _run_continuous_loop(overlay, interact, cdp, session, machine, ds, delay, results, port)
    return results


def _run_continuous_loop(overlay, interact, cdp, session, machine, ds, delay, results, port):
    """Core continuous demo loop, shared between run_demo and run_demo_on_tab."""
    msg_idx = 0
    contact_idx = 0
    _log("Starting continuous demo...")

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 20
    try:
        while True:
          try:
            contact = CONTACTS[contact_idx % len(CONTACTS)]
            pool = CONTACT_MSGS.get(contact, ALICE_MSGS)
            message = pool[msg_idx % len(pool)]

            cdp = session.get_cdp()
            if not cdp:
                _log("Lost CDP. Recovering...")
                machine.transition(ds.DemoState.RECOVERING)
                cdp = _recover_cdp(session, overlay, port)
                if not cdp:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        _log(f"Too many errors ({consecutive_errors}). Exiting.")
                        break
                    _log(f"Recovery failed ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}). Retrying in 5s...")
                    machine.transition(ds.DemoState.ERROR, {"error": "CDP lost"})
                    time.sleep(5)
                    continue

            cdp = _check_and_relock(overlay, cdp, session, machine, ds, port)
            if not cdp:
                continue

            _log(f"[{_now()}] [{contact}] {message[:45]}...")
            machine.transition(ds.DemoState.SELECTING_CONTACT,
                               {"contact": contact, "message": message})

            overlay.set_lock_passthrough(cdp, True)

            _simulate_incoming(cdp, overlay, contact_idx, msg_idx)

            is_draft = (msg_idx % 4 == 3) and msg_idx > 0
            if is_draft:
                _do_draft_cycle(overlay, interact, cdp, contact, contact_idx, delay)

            interact.mcp_click(
                cdp, f'.contact-item[data-contact="{contact}"]',
                label=f"Select: {contact}", dwell=delay * 0.5 + random.uniform(0, 0.3),
                unlock_for_click=False,
            )
            time.sleep(delay * 0.2 + random.uniform(0, 0.3))

            if _is_unlocked(overlay, cdp):
                overlay.set_lock_passthrough(cdp, False)
                cdp = _check_and_relock(overlay, cdp, session, machine, ds, port)
                if not cdp:
                    continue
                overlay.set_lock_passthrough(cdp, True)

            machine.transition(ds.DemoState.TYPING_MESSAGE)
            interact.mcp_type(
                cdp, '#messageInput', message,
                label="Message input",
                char_delay=random.uniform(0.025, 0.05),
                manage_passthrough=False,
            )
            time.sleep(delay * 0.15 + random.uniform(0, 0.2))

            if _is_unlocked(overlay, cdp):
                overlay.set_lock_passthrough(cdp, False)
                cdp = _check_and_relock(overlay, cdp, session, machine, ds, port)
                if not cdp:
                    continue
                overlay.set_lock_passthrough(cdp, True)

            machine.transition(ds.DemoState.SENDING)
            interact.mcp_click(
                cdp, '#sendBtn', label="Send", dwell=delay * 0.3,
                unlock_for_click=False,
            )

            overlay.set_lock_passthrough(cdp, False)
            time.sleep(delay * 0.15)

            machine.transition(ds.DemoState.VERIFYING)
            last = cdp.evaluate(
                "(function(){var m=document.querySelectorAll('.message.sent');"
                "if(!m.length)return '';return m[m.length-1].querySelector('div').textContent;})()"
            )
            delivered = message in str(last or "")
            _log(f"{'Delivered' if delivered else 'Not verified'}.")

            overlay.increment_mcp_count(cdp, 3)

            msg_idx += 1
            contact_idx += 1
            consecutive_errors = 0

            machine.transition(ds.DemoState.COUNTDOWN)
            wait = random.randint(COUNTDOWN_MIN, COUNTDOWN_MAX)
            for sec in range(wait, 0, -1):
                machine.set_countdown(sec)
                overlay.inject_badge(cdp, text=f"Next in {sec}s", color="#ea8600")
                time.sleep(1)
                cdp = session.get_cdp()
                if not cdp:
                    break
                if not overlay.is_locked(cdp):
                    cdp = _check_and_relock(overlay, cdp, session, machine, ds, port)
                    break
            if cdp:
                overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")
            machine.set_countdown(0)

          except KeyboardInterrupt:
            raise
          except Exception as _e:
            consecutive_errors += 1
            _log(f"Demo loop error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {_e}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                _log("Too many consecutive errors. Exiting demo loop.")
                break
            time.sleep(3)

    except KeyboardInterrupt:
        _log("Stopped by user.")
        machine.transition(ds.DemoState.STOPPED)

    results["steps"].append({"step": "continuous", "ok": True, "messages_sent": msg_idx})
    results["ok"] = True


def _do_draft_cycle(overlay, interact, cdp, contact, contact_idx, delay):
    """Type a partial draft, switch to another contact, then switch back."""
    drafts = [
        "I was thinking about the architecture...",
        "Quick question about the deployment...",
        "Let me check the latest test results...",
        "Could we revisit the caching approach...",
        "I'll send the updated spec after...",
    ]
    draft = drafts[contact_idx % len(drafts)]
    next_c = CONTACTS[(contact_idx + 1) % len(CONTACTS)]

    interact.mcp_type(
        cdp, '#messageInput', draft,
        label=f"Draft: {draft[:25]}...",
        char_delay=random.uniform(0.03, 0.05),
        manage_passthrough=False,
    )
    time.sleep(0.6 + random.uniform(0, 0.4))
    overlay.inject_badge(cdp, text="Draft saved", color="#5f6368")
    time.sleep(0.8)

    interact.mcp_click(
        cdp, f'.contact-item[data-contact="{next_c}"]',
        label=f"Switch: {next_c}", dwell=delay * 0.4,
        unlock_for_click=False,
    )
    time.sleep(0.5 + random.uniform(0, 0.3))
    overlay.inject_badge(cdp, text="CDMCP Demo", color="#1a73e8")

    interact.mcp_click(
        cdp, f'.contact-item[data-contact="{contact}"]',
        label=f"Back: {contact}", dwell=delay * 0.3,
        unlock_for_click=False,
    )
    time.sleep(0.3)
    cdp.evaluate("document.getElementById('messageInput').value = ''")
    overlay.increment_mcp_count(cdp, 3)
    time.sleep(0.1)


def _single_run(overlay, interact, cdp, session, machine, ds, delay, results):
    machine.transition(ds.DemoState.SELECTING_CONTACT, {"contact": "bob"})
    overlay.set_lock_passthrough(cdp, True)
    interact.mcp_click(cdp, '.contact-item[data-contact="bob"]',
                       label="Select: Bob Martinez", dwell=delay, unlock_for_click=False)
    time.sleep(delay * 0.5)
    overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25)
    machine.transition(ds.DemoState.TYPING_MESSAGE)
    msg = ALICE_MSGS[0]
    interact.mcp_type(cdp, '#messageInput', msg, label="Message input",
                      char_delay=0.03, manage_passthrough=False)
    time.sleep(delay * 0.3)
    machine.transition(ds.DemoState.SENDING)
    interact.mcp_click(cdp, '#sendBtn', label="Send", dwell=delay * 0.5, unlock_for_click=False)
    overlay.set_lock_passthrough(cdp, False)
    time.sleep(delay * 0.3)
    machine.transition(ds.DemoState.VERIFYING)
    last = cdp.evaluate(
        "(function(){var m=document.querySelectorAll('.message.sent');"
        "if(!m.length)return '';return m[m.length-1].querySelector('div').textContent;})()"
    )
    results["steps"].append({"step": "single", "ok": msg in str(last or "")})
    cdp2 = session.get_cdp()
    if cdp2:
        overlay.remove_all_overlays(cdp2)
        overlay.inject_badge(cdp2, text="CDMCP Demo", color="#34a853")
    machine.transition(ds.DemoState.STOPPED)
    results["ok"] = all(s.get("ok", False) for s in results["steps"])
    return results
