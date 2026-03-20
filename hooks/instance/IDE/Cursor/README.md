# Cursor IDE Hooks — Instances

Active hook implementations for Cursor IDE's lifecycle system. These scripts are referenced by `.cursor/hooks.json` and run as standalone processes.

## Installation

Hooks are auto-deployed when running `python setup.py` at the project root. The deploy step:
1. Detects Cursor IDE (via `CURSOR_VERSION` env, `~/.cursor/`, or `.cursor/` directory)
2. Copies `logic/setup/cursor/hooks/hooks.json` → `.cursor/hooks.json`
3. Copies rule templates from `logic/setup/cursor/rules/` → `.cursor/rules/`

The hooks.json references scripts using relative paths from project root:
```json
"command": "python3 hooks/instance/IDE/Cursor/brain_remind.py"
```

## Instances

| Script | Hook Event | Purpose |
|--------|-----------|---------|
| `brain_inject.py` | `sessionStart` | Load brain (tasks + context + lessons + ecosystem) into conversation |
| `brain_remind.py` | `postToolUse` + `afterFileEdit` | Anti-fatigue USERINPUT reminder with progressive escalation |
| `userinput_flag.py` | `afterShellExecution` | Flag USERINPUT execution (matcher: `USERINPUT`) |
| `userinput_enforce.py` | `stop` | If USERINPUT wasn't called, auto-continue to force it |
| `file_search_fallback.py` | `postToolUse` | Fallback for file search operations |

## Anti-Fatigue Reminder System (brain_remind.py)

The reminder system uses 4 escalation tiers to combat message habituation:

| Tier | Count Range | Frequency | Style |
|------|-------------|-----------|-------|
| Silent | 1-3 | Never | No reminders (grace period) |
| T1 Gentle | 4-10 | Every 3rd call | Polite reminder |
| T2 Assertive | 11-25 | Every 2nd call | Direct with command |
| T3 Urgent | 26-49 | Every call | Bold markers, time tracking |
| T4 Emergency | 50+ | Every call | Box art, task context, threats |

Key anti-habituation features:
- **Unique selection**: Never sends the same message twice in a row
- **Format variation**: Different visual patterns (>>>, ###, ===, ╔══╗, 🚨)
- **Time tracking**: Includes elapsed time since last USERINPUT
- **Counter reset**: Resets to 0 when USERINPUT flag file is detected
- **Task context**: At T4, includes active task list for added relevance

## Architecture

```
User starts conversation
    │
    ▼
sessionStart → brain_inject.py → additional_context (brain state + ecosystem)
    │
    ▼
Agent works... (tool calls)
    │
    ├─ postToolUse → brain_remind.py → tiered reminder (resets on USERINPUT flag)
    ├─ afterFileEdit → brain_remind.py → same tiered system
    ├─ afterShellExecution (USERINPUT) → userinput_flag.py → sets flag file
    │
    ▼
Agent stops
    │
    ▼
stop → userinput_enforce.py → checks flag → followup_message if missing
```

## State Files

| File | Purpose | Lifetime |
|------|---------|----------|
| `/tmp/cursor-remind-state-<conv_id>` | Reminder state (count, hash, timestamps) | Session |
| `/tmp/cursor-userinput-done-<conv_id>` | USERINPUT execution flag | Session |

## Testing

```bash
echo '{"workspace_roots": ["/Applications/AITerminalTools"], "conversation_id": "test"}' | python3 hooks/instance/IDE/Cursor/brain_inject.py
echo '{"workspace_roots": ["/Applications/AITerminalTools"], "conversation_id": "test", "tool_name": "Read"}' | python3 hooks/instance/IDE/Cursor/brain_remind.py
```
