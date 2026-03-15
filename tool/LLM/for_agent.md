# LLM -- Agent Reference

## Quick Start

```bash
LLM setup                         # Configure API keys interactively
LLM status                        # Check which providers are ready
LLM providers                     # Detailed provider info
LLM test                          # Send test message to default provider
LLM send "prompt text"            # One-shot message
LLM usage                         # View all-time API usage stats
LLM usage --period today          # Today's usage only
LLM usage --filter-provider NAME  # Filter by provider
```

## Cross-Tool Interface

```python
from tool.LLM.interface.main import (
    send, get_provider, SessionContext, list_providers,
    retry_on_transient, CostModel,
    get_usage_summary, get_daily_usage_summary,
)

# Simple one-shot
result = send("Hello", provider_name="zhipu-glm-4-flash")
# result = {"ok": True, "text": "...", "usage": {...},
#           "latency_s": 1.2, "estimated_cost_usd": 0.0}

# With retry on transient errors
provider = get_provider("nvidia-glm-4-7b")
msgs = [{"role": "user", "content": "Hello"}]
result = retry_on_transient(
    lambda: provider.send(msgs),
    max_retries=3,
    rate_limiter=provider._rate_limiter,
)
```

## Providers

| Name | Model | API URL | Key Config | RPM | Context |
|------|-------|---------|------------|-----|---------|
| `nvidia-glm-4-7b` | z-ai/glm4.7 | integrate.api.nvidia.com/v1/chat/completions | `nvidia_api_key` / `NVIDIA_API_KEY` | 30 | 131K |
| `zhipu-glm-4-flash` | glm-4-flash | open.bigmodel.cn/api/paas/v4/chat/completions | `zhipu_api_key` / `ZHIPU_API_KEY` | 30 | 128K |

## Live Agent GUI

Start the live agent server with:

```bash
LLM agent                            # Start with default provider
LLM agent --provider nvidia-glm-4-7b # Specific provider
LLM agent --tools                    # Enable tool calling
LLM agent --port 8100 --no-open      # Custom port, no browser
```

The live server provides:
- Real-time SSE streaming of agent events to the browser
- HTTP API for programmatic control (send messages, create sessions)
- Auto-generated conversation titles on first message
- `Ctrl+D` or `Enter` to send messages
- Single-line input field

### Programmatic Control (MCP-compatible injection)

```python
from tool.LLM.interface.main import start_agent_server

agent = start_agent_server(port=8100)

# Inject text into input box (types character by character, then auto-sends)
import requests
requests.post(f"{agent.url}api/input", json={
    "session_id": agent.default_session_id,
    "text": "Build a REST API with JWT auth"
})

# Or send directly (bypasses input box animation)
requests.post(f"{agent.url}api/send", json={
    "session_id": agent.default_session_id,
    "text": "Build a REST API with JWT auth"
})
```

## Key Modules

- `logic/base.py` -- `LLMProvider` ABC with unified `send()` that auto-records usage, measures latency, and estimates cost. `CostModel` dataclass for pricing metadata.
- `logic/session_context.py` -- `SessionContext`: manages messages array with system prompt and auto-truncation.
- `logic/rate_limiter.py` -- `RateLimiter`: token-bucket with RPM cap, min interval, jitter, and adaptive 429 backoff. `retry_on_transient(fn, max_retries, rate_limiter)` for auto-retry.
- `logic/usage.py` -- `record_usage()`, `get_summary()`, `get_daily_summary()`, `rotate_usage()` -- persistent JSONL tracking.
- `logic/registry.py` -- `get_provider(name)`, `list_providers()`, `register(name, cls)`.
- `logic/config.py` -- `get_config_value(key)`, `set_config_value(key, value)` -- stores in `data/llm_config.json`.

## Provider Architecture

Providers only implement `_send_request()` (raw API call). The base class `send()` method handles:
1. Latency timing
2. Cost estimation via `CostModel`
3. Automatic usage recording to `data/usage.jsonl`

## Agent GUI Engine

The LLM tool provides a reusable browser-based UI engine for agent interactions.

### Key Files

- `logic/gui/agent_gui_engine.js` — `AgentGUIEngine` class: block registry, SSE streaming, session management, scroll-to-bottom, theming.
- `logic/gui/agent_demo.html` — Demo that feeds protocol events to the engine.

### Interface

```python
from tool.LLM.interface.main import get_agent_gui_path, get_agent_gui_engine_path

get_agent_gui_path()           # → path to agent_demo.html
get_agent_gui_engine_path()    # → path to agent_gui_engine.js
```

### Protocol Event Types

Feed events via `engine.processEvent(evt)` or SSE at `/api/events`:

- `user { text }` — User message
- `thinking { tokens }` — Streaming thinking block
- `text { tokens }` — Markdown assistant text
- `tool { name, desc, cmd, file }` — Tool call (exec/edit/read/search)
- `tool_result { ok, output }` — Tool output (auto-renders diff for edit)
- `todo { items[] }` / `todo_update { id, status }` / `todo_delete { id }` — TODO management
- `experience { lesson }` — Info/lesson block
- `complete` — Task done

### Extending

Register custom blocks: `engine.registerBlock('memory', renderFn)`
Override theme: `engine.loadTheme({ accent: '#e63946' })`
Session management: `addSession`, `renameSession`, `deleteSession`, `setSessionStatus`, `setActiveSession`

### ConversationManager (GUI-agnostic)

A stateful middle layer between any GUI and the LLM provider:

```python
from tool.LLM.interface.main import get_conversation_manager
ConversationManager = get_conversation_manager()

mgr = ConversationManager(provider_name="zhipu-glm-4-flash")
mgr.on_event(lambda evt: push_to_gui(evt))

sid = mgr.new_session()
mgr.send_message(sid, "Hello!")  # non-blocking, emits events via callback
mgr.rename_session(sid, "New Title")
mgr.delete_session(sid)
mgr.list_sessions()
mgr.get_state()  # full state export for persistence
```

All GUIs (HTML, CLI, tkinter) call the same methods. The first message in a session auto-generates a title.

### SSE Streaming

Use `logic/serve/html_server.py` (`LocalHTMLServer` with `enable_sse=True`) to push events from Python to the browser in real time. The server is now multi-threaded to handle concurrent SSE connections and API requests.

### HTTP API for Remote Control

When using the live GUI server, these API endpoints are available:

- `POST /api/send` — `{"session_id": "...", "text": "..."}` Send a message
- `POST /api/session` — `{"title": "..."}` Create a new session
- `POST /api/rename` — `{"session_id": "...", "title": "..."}` Rename session
- `POST /api/delete` — `{"session_id": "..."}` Delete session
- `GET /api/sessions` — List all sessions
- `GET /api/state` — Full state dump

## Dependencies

- PYTHON (managed Python runtime)
