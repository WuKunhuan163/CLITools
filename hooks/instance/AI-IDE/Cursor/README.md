# Cursor IDE Hooks — Instances

Active hook implementations for Cursor IDE's lifecycle system. These scripts are referenced by `.cursor/hooks.json` and run as standalone processes.

## Instances

| Script | Hook Event | Purpose |
|--------|-----------|---------|
| `brain_inject.py` | `sessionStart` | Load brain (tasks + context + recent lessons) into conversation |
| `brain_remind.py` | `postToolUse` | Every 10 calls: light reminder. Every 30: full brain injection |
| `userinput_flag.py` | `afterShellExecution` | Flag USERINPUT execution (matcher: `USERINPUT`) |
| `userinput_enforce.py` | `stop` | If USERINPUT wasn't called, auto-continue to force it |

## Architecture

```
User starts conversation
    │
    ▼
sessionStart → brain_inject.py → additional_context (brain state)
    │
    ▼
Agent works... (tool calls)
    │
    ├─ postToolUse (every 10) → brain_remind.py → additional_context (reminder)
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
| `/tmp/cursor-brain-counter-<conv_id>` | Tool call counter per conversation | Session |
| `/tmp/cursor-userinput-done-<conv_id>` | USERINPUT execution flag | Session |

## Testing

```bash
echo '{"workspace_roots": ["/Applications/AITerminalTools"], "conversation_id": "test"}' | python3 hooks/instance/AI-IDE/Cursor/brain_inject.py
```
