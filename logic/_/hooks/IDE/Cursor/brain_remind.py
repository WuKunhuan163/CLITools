#!/usr/bin/env python3
"""postToolUse hook: Anti-fatigue reminder system for USERINPUT execution.

Fires after every tool call. Implements progressive escalation with format
variation to combat message habituation over long sessions.

Schedule:
  - Tool call #1: One initial reminder (establishes the pattern for fresh agents)
  - Tool calls #2 to START_AFTER: Silent (agent remembers from the first reminder)
  - Tool calls START_AFTER+: Reminders appear, ramping from MIN_INTERVAL to
    MAX_INTERVAL (in tool calls between reminders). The ramp is linear.

Anti-fatigue strategies:
1. Dynamic messages — randomly selected from pools, never the same twice in a row
2. Progressive frequency — reminders get more frequent as work continues
3. Format variation — alternates between brief/verbose, structural markers change
4. Time awareness — tracks wall-clock time since last USERINPUT
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

_DEFAULT_START_AFTER = 500
_DEFAULT_MIN_INTERVAL = 200
_DEFAULT_MAX_INTERVAL = 50
_RAMP_SPAN = 2000


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] brain_remind: {msg}\n")
    except Exception:
        pass


_INITIAL_MSG = (
    "USERINPUT is available for user feedback. "
    "Call it with block_until_ms: 310000 when ready. "
    "Never use short timeouts or background execution."
)

_REMINDER_POOL = [
    "Remember to run USERINPUT when ready for user feedback.",
    "USERINPUT overdue ({elapsed}). Execute it before continuing more work.",
    "You have not called USERINPUT in {n} tool calls. Run it now.",
    "Stop and run USERINPUT. User feedback prevents wasted work.",
    ">>> USERINPUT required. The user may have corrections. block_until_ms: 310000",
    "ACTION NEEDED: Execute USERINPUT now. Do not background it.",
    "{n} tool calls without USERINPUT ({elapsed}). RUN IT IMMEDIATELY.",
    "=== USERINPUT OVERDUE ({elapsed}) === Execute now with block_until_ms: 310000",
    "### STOP ### You MUST call USERINPUT before continuing. {n} calls without it.",
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
    return {
        "count": 0,
        "last_msg_hash": 0,
        "first_call_ts": time.time(),
        "last_userinput_ts": 0,
        "last_remind_at": 0,
    }


def _save_state(conversation_id: str, state: dict):
    state_file = Path(f"/tmp/cursor-remind-state-{conversation_id}")
    state_file.write_text(json.dumps(state))


def _load_hook_config() -> dict:
    config_file = Path("/tmp/cursor-remind-hook-config.json")
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except Exception:
            pass
    return {}


def _pick_unique(pool: list, last_hash: int) -> tuple:
    candidates = list(pool)
    random.shuffle(candidates)
    for msg in candidates:
        h = hash(msg) % 10000
        if h != last_hash:
            return msg, h
    return candidates[0], hash(candidates[0]) % 10000


def _get_current_interval(count: int, start_after: int,
                          min_interval: int, max_interval: int) -> int:
    """Calculate the current interval between reminders.

    Returns the number of tool calls between reminders, linearly ramping
    from min_interval (infrequent) to max_interval (frequent) over RAMP_SPAN
    calls after start_after.
    """
    calls_past_start = count - start_after
    if calls_past_start <= 0:
        return min_interval
    progress = min(calls_past_start / _RAMP_SPAN, 1.0)
    return max(int(min_interval - progress * (min_interval - max_interval)),
               max_interval)


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
        flag_ts = userinput_flag.stat().st_mtime
        if flag_ts > state.get("last_userinput_ts", 0):
            state["last_userinput_ts"] = flag_ts
            state["count"] = 0
            count = 0
            state["last_remind_at"] = 0

    _save_state(conversation_id, state)

    hook_cfg = _load_hook_config()
    start_after = hook_cfg.get("start_after", _DEFAULT_START_AFTER)
    min_interval = hook_cfg.get("min_interval", _DEFAULT_MIN_INTERVAL)
    max_interval = hook_cfg.get("max_interval", _DEFAULT_MAX_INTERVAL)

    last_ui_ts = state.get("last_userinput_ts", 0)
    if not last_ui_ts:
        last_ui_ts = state.get("first_call_ts", time.time())
    since_userinput = time.time() - last_ui_ts
    elapsed = _format_elapsed(since_userinput)
    last_hash = state.get("last_msg_hash", 0)

    output = {}

    if count == 1:
        output["additional_context"] = f"[Reminder] {_INITIAL_MSG}"
        _log(f"INITIAL count=1")

    elif count in (5, 8):
        output["additional_context"] = (
            "[Reminder] After completing your current task, run BRAIN reflect "
            "then USERINPUT --hint. This is the core feedback loop."
        )
        _log(f"EARLY count={count}")

    elif count > start_after:
        interval = _get_current_interval(count, start_after,
                                         min_interval, max_interval)
        last_remind = state.get("last_remind_at", 0)
        calls_since_remind = count - last_remind

        if calls_since_remind >= interval:
            msg, new_hash = _pick_unique(_REMINDER_POOL, last_hash)
            msg = msg.format(n=count, elapsed=elapsed)
            output["additional_context"] = msg
            state["last_msg_hash"] = new_hash
            state["last_remind_at"] = count
            _save_state(conversation_id, state)
            _log(f"REMIND count={count} interval={interval} elapsed={elapsed}")
        else:
            _log(f"skip count={count} interval={interval} since_remind={calls_since_remind}")
    else:
        _log(f"silent count={count} start_after={start_after}")

    result = json.dumps(output)
    _log(f"output={result[:200]}")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
