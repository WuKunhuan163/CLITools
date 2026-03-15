#!/usr/bin/env python3
"""postToolUse hook: Anti-fatigue reminder system for USERINPUT execution.

Fires after every tool call. Implements progressive escalation with format
variation to combat message habituation over long sessions (50-100+ tool calls).

Anti-fatigue strategies:
1. Dynamic messages — randomly selected from pools, never the same twice in a row
2. Progressive escalation — 4 tiers with increasing urgency and format changes
3. Format variation — alternates between brief/verbose, structural markers change
4. Time awareness — tracks wall-clock time since last USERINPUT
5. Contextual triggers — includes active task context at higher tiers
"""
import json
import os
import sys
import time
import random
import traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] brain_remind: {msg}\n")
    except Exception:
        pass


# Tier 1: Gentle (count 1-10) — every 3rd call
_T1_POOL = [
    "Remember to run USERINPUT when ready for user feedback.",
    "USERINPUT is available when you need user input.",
    "Don't forget: USERINPUT before ending your turn.",
    "Tip: call USERINPUT periodically for user feedback.",
]

# Tier 2: Assertive (count 11-25) — every 2nd call
_T2_POOL = [
    ">>> USERINPUT required. Run: python3 -B tool/USERINPUT/main.py --timeout 120",
    "ACTION NEEDED: Execute USERINPUT now. The user may have corrections.",
    "You have not called USERINPUT in {n} tool calls. Execute it.",
    "USERINPUT overdue ({elapsed}). Run it before continuing.",
    "Stop and run USERINPUT. User feedback prevents wasted work.",
]

# Tier 3: Urgent (count 26-50) — every call
_T3_POOL = [
    "!!! CRITICAL: {n} tool calls without USERINPUT. RUN IT IMMEDIATELY !!!",
    "=== USERINPUT OVERDUE ({elapsed}) === Execute: python3 -B tool/USERINPUT/main.py --timeout 120",
    "### STOP ### You MUST call USERINPUT before ANY more tool calls. {n} calls without it.",
    "*** URGENT *** {n} operations without user feedback. USERINPUT NOW. python3 -B tool/USERINPUT/main.py",
    "BLOCKED: No more actions until USERINPUT is executed. Calls since last: {n}. Time: {elapsed}.",
]

# Tier 4: Emergency (count 50+) — every call, with full context
_T4_POOL = [
    "🚨 EMERGENCY: {n} TOOL CALLS WITHOUT USERINPUT. YOU ARE IGNORING THIS REMINDER.\n"
    "Execute this EXACT command in Shell: python3 -B tool/USERINPUT/main.py --timeout 120\n"
    "DO NOT make another tool call before running USERINPUT.",

    "╔══════════════════════════════════════════════╗\n"
    "║  USERINPUT NOT CALLED — {n} CALLS OVERDUE   ║\n"
    "║  Run: python3 -B tool/USERINPUT/main.py     ║\n"
    "╚══════════════════════════════════════════════╝\n"
    "The user is waiting. Execute USERINPUT RIGHT NOW.",

    "⛔ FINAL WARNING [{n} calls, {elapsed}]: Your turn CANNOT end without USERINPUT.\n"
    "The stop hook will REJECT your completion. Run USERINPUT now to avoid forced retry.\n"
    "Command: python3 -B tool/USERINPUT/main.py --timeout 120",
]


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m{int(seconds%60)}s"
    else:
        return f"{int(seconds/3600)}h{int((seconds%3600)/60)}m"


def _load_state(conversation_id: str) -> dict:
    state_file = Path(f"/tmp/cursor-remind-state-{conversation_id}")
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"count": 0, "last_msg_hash": 0, "first_call_ts": time.time(), "last_userinput_ts": 0}


def _save_state(conversation_id: str, state: dict):
    state_file = Path(f"/tmp/cursor-remind-state-{conversation_id}")
    state_file.write_text(json.dumps(state))


def _pick_unique(pool: list, last_hash: int) -> tuple:
    """Pick a message from pool that differs from the last one sent."""
    candidates = list(pool)
    random.shuffle(candidates)
    for msg in candidates:
        h = hash(msg) % 10000
        if h != last_hash:
            return msg, h
    return candidates[0], hash(candidates[0]) % 10000


def _load_active_tasks(project_dir: Path) -> str:
    tasks_file = project_dir / "runtime" / "brain" / "tasks.json"
    if not tasks_file.exists():
        return ""
    try:
        data = json.loads(tasks_file.read_text())
        active = [t for t in data.get("tasks", []) if t.get("status") != "done"]
        if active:
            return "\n".join(f"  #{t['id']} [{t['status']}] {t['content']}" for t in active[:5])
    except Exception:
        pass
    return ""


def main():
    try:
        raw = sys.stdin.read()
        _log(f"stdin length={len(raw)}")
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(f"ERROR parsing stdin: {e}")
        print(json.dumps({}))
        return

    conversation_id = payload.get("conversation_id", "unknown")
    tool_name = payload.get("tool_name", "?")
    _log(f"tool={tool_name} conv={conversation_id[:12]}")

    state = _load_state(conversation_id)
    state["count"] = state.get("count", 0) + 1
    count = state["count"]

    if "first_call_ts" not in state:
        state["first_call_ts"] = time.time()

    userinput_flag = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
    if userinput_flag.exists():
        state["last_userinput_ts"] = userinput_flag.stat().st_mtime
        state["count"] = 0
        count = 0

    _save_state(conversation_id, state)

    last_ui_ts = state.get("last_userinput_ts", 0)
    if not last_ui_ts:
        last_ui_ts = state.get("first_call_ts", time.time())
    since_userinput = time.time() - last_ui_ts
    elapsed = _format_elapsed(since_userinput)
    last_hash = state.get("last_msg_hash", 0)

    output = {}
    workspace_roots = payload.get("workspace_roots", [])
    project_dir = Path(workspace_roots[0]) if workspace_roots else Path("/Applications/AITerminalTools")

    if count >= 50:
        # Tier 4: Emergency — every call
        msg, new_hash = _pick_unique(_T4_POOL, last_hash)
        msg = msg.format(n=count, elapsed=elapsed)
        tasks = _load_active_tasks(project_dir)
        if tasks:
            msg += f"\n\nActive tasks:\n{tasks}"
        output["additional_context"] = msg
        _log(f"T4 EMERGENCY count={count}")

    elif count >= 26:
        # Tier 3: Urgent — every call
        msg, new_hash = _pick_unique(_T3_POOL, last_hash)
        msg = msg.format(n=count, elapsed=elapsed)
        output["additional_context"] = msg
        _log(f"T3 URGENT count={count}")

    elif count >= 11:
        # Tier 2: Assertive — every 2nd call
        if count % 2 == 0:
            msg, new_hash = _pick_unique(_T2_POOL, last_hash)
            msg = msg.format(n=count, elapsed=elapsed)
            output["additional_context"] = msg
            _log(f"T2 ASSERTIVE count={count}")
        else:
            new_hash = last_hash
            _log(f"T2 skip count={count}")

    elif count >= 4:
        # Tier 1: Gentle — every 3rd call
        if count % 3 == 0:
            msg, new_hash = _pick_unique(_T1_POOL, last_hash)
            output["additional_context"] = f"[Reminder] {msg}"
            _log(f"T1 GENTLE count={count}")
        else:
            new_hash = last_hash
            _log(f"T1 skip count={count}")
    else:
        new_hash = last_hash
        _log(f"silent count={count}")

    state["last_msg_hash"] = new_hash
    _save_state(conversation_id, state)

    result = json.dumps(output)
    _log(f"output={result[:200]}")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
