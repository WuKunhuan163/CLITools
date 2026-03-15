---
name: unified-gui-development
description: Guide for synchronized development of HTML GUI and CLI GUI features. Use when adding new GUI features, settings, or interactive elements that must work in both HTML and terminal interfaces.
---

# Unified GUI Development

## Why This Exists

Every user-facing feature must work in both the HTML GUI and the CLI GUI. Without a shared discipline, features drift apart — settings appear in HTML but not CLI, or tool blocks render differently across frontends. This skill ensures synchronized development and a consistent backend.

## Architecture

```
Backend (Python)
├── ConversationManager   → emits events via callbacks
├── AgentServer           → HTTP API + SSE for HTML GUI
└── CLI (OpenClawCLI)     → direct callback consumption

Events flow:
  ConversationManager.on_event(callback)
      ├── AgentServer._on_mgr_event → SSE push → browser JS
      └── CLI._on_event             → terminal rendering
```

### Shared Event Protocol

All frontends consume the same event types from `ConversationManager._emit()`:

| Event Type | Key Fields | HTML Rendering | CLI Rendering |
|---|---|---|---|
| `text` | `tokens` | Append to message bubble | Print inline |
| `tool_call` | `name`, `args` | Shimmer block | `_ToolBlock` with blinking ▫ |
| `tool_result` | `name`, `ok`, `output` | Block expand/collapse | `_ToolBlock.end()` with ▪ |
| `notice` | `text`, `icon` | Centered gray text | `_system_notice()` |
| `error` | `message` | Red X icon, stop spinner | ■ red indicator |
| `debug` | `text` | Hidden unless debug mode | Gray 20-char + log ref |
| `llm_request` | `provider`, `round` | Status bar update | `○ Round N` |
| `llm_response_end` | `round`, `usage` | Update token count | `● Round N — X tokens` |
| `complete` | — | Re-enable input | ■ green indicator |
| `session_status` | `id`, `status` | Sidebar update | — |

### Adding a New Event Type

1. Define in `ConversationManager._emit()` with a descriptive `type` string
2. Handle in `agent_gui_engine.js` → register block type or update `processEvent`
3. Handle in CLI → add case in the event callback
4. Document in this table

## Core Workflow: Adding a Feature

### Step 1: Backend API First

Every setting or action needs a backend endpoint. Define it in `AgentServer._api_handler`:

```python
elif path == "/api/my-setting":
    value = body.get("value")
    # persist to config
    return {"ok": True}
```

### Step 2: CLI Command

Map the same action to a CLI command. In `main.py` or the CLI handler:

```python
elif cmd == "/my-setting":
    value = args[0] if args else None
    # same logic as API
    print(fmt_status("Setting updated.", dim=value))
```

### Step 3: HTML GUI

Add UI controls in `agent_live.html` that call the API endpoint:

```javascript
await fetch('/api/my-setting', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({value: newValue})
});
```

### Step 4: Verify Parity

Checklist for every feature:
- [ ] Backend logic is in a shared function (not duplicated per frontend)
- [ ] HTML GUI calls the API endpoint
- [ ] CLI command calls the same shared function
- [ ] Event emission works for both SSE and direct callback
- [ ] Settings persist to the same config store

## Settings Synchronization

HTML settings are configured through the settings panel. Every HTML setting MUST have a corresponding CLI command:

| HTML Setting | CLI Command | Backend |
|---|---|---|
| Model selection | `/model <name>` | `config.set_model()` |
| Turn limit | `/turns <n>` | `config.set_turn_limit()` |
| Debug toggle | `/debug` | `config.toggle_debug()` |
| Theme | `/theme <dark\|light>` | `config.set_theme()` |
| API key | `/key <vendor> <key>` | `config.set_api_key()` |

## Anti-Patterns

**Bad**: Adding a button in HTML that directly modifies state without an API endpoint.
Why: CLI users cannot access this feature, and the action is not testable.

**Bad**: Adding a CLI command that prints output without emitting an event.
Why: HTML GUI will not reflect the change.

**Bad**: Duplicating business logic in both `agent_live.html` JS and `cli.py`.
Why: Logic diverges over time. Put shared logic in Python backend, expose via API.

## SSE vs Direct Callback

- **HTML GUI**: `AgentServer` wraps events as SSE (`text/event-stream`). The browser's `EventSource` receives them. Reconnection is automatic.
- **CLI GUI**: Events arrive as direct Python callbacks. No network layer. The CLI renders immediately.

Both frontends MUST handle the same set of event types. When adding a new event type, grep for `processEvent` (HTML) and the CLI event handler to ensure both are updated.

## See Also

- `standard-command-development` — Three-layer architecture for commands
- `turing-machine-development` — Progress display patterns
- `tool-interface` — Cross-tool communication
