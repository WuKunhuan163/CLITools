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
| `zhipu-glm-4.7-flash` | glm-4.7-flash | open.bigmodel.cn/api/paas/v4/chat/completions | `zhipu_api_key` / `ZHIPU_API_KEY` | 10 | 128K |
| `auto` | (auto-select) | — | — | — | — |

### Auto Model Selection

Use `auto` as the provider name for automatic model selection with fallback. The Auto provider:
- Ranks available models by stability (free-tier preference, RPM headroom, recent error rate)
- Falls back to the next model on 429/500/502/503 errors
- Tracks per-provider health in a 10-minute sliding window
- Implemented in `tool/LLM/logic/auto.py`

## Live Agent GUI

Start the live agent server with:

```bash
LLM agent                            # Start with auto-detected provider
LLM agent --tools                    # Enable tool calling (exec, search, etc.)
LLM agent --port 8100 --no-open      # Custom port, no browser
LLM agent --agent-provider zhipu-glm-4-flash  # Specific provider
```

The live server provides:
- Real-time SSE streaming of agent events to the browser
- HTTP API for programmatic control (send messages, create sessions)
- Auto-generated conversation titles on first message
- `Ctrl+D` or `Enter` to send messages
- Single-line input field with overflow ellipsis

### Tool Calling via exec

When `--tools` is enabled, the agent can use the `exec` tool to call any
installed CLI tool. The agent discovers tools via `TOOL --list` and reads
their `for_agent.md` for usage. Example flow:

```
User: "帮我查找Bilibili播放量最大的10个视频"
Agent calls: exec(command="BILIBILI trending --limit 10")
→ Browser opens, navigates to Bilibili trending page, extracts video data
→ Agent formats and presents results to user
```

The system prompt guides the agent to use exec for tool calls. Any tool
in the `bin/` directory (BILIBILI, GOOGLE, GIT, etc.) can be called.

### Programmatic Control (MCP-compatible injection)

```python
from tool.LLM.interface.main import start_server

agent = start_server(port=8100, enable_tools=True)

# Inject text into input box (types character by character, then auto-sends)
import requests
requests.post(f"{agent.url}api/input", json={
    "session_id": agent.default_session_id,
    "text": "帮我查找Bilibili播放量最大的10个视频"
})

# Or send directly (bypasses input box animation)
requests.post(f"{agent.url}api/send", json={
    "session_id": agent.default_session_id,
    "text": "帮我查找Bilibili播放量最大的10个视频"
})
```

### Agent Discovery Pattern

A context-free agent discovers tools through this sequence:
1. `exec(command="TOOL --list")` → discovers BILIBILI, GOOGLE, etc.
2. `exec(command="cat tool/BILIBILI/for_agent.md")` → reads BILIBILI docs
3. `exec(command="BILIBILI boot")` → starts browser session
4. `exec(command="BILIBILI trending --limit 10")` → real browser automation

## Key Modules

- `logic/base.py` -- `LLMProvider` ABC with unified `send()` that auto-records usage, measures latency, and estimates cost. `CostModel` dataclass for pricing metadata.
- `logic/session_context.py` -- `SessionContext`: manages messages array with system prompt and auto-truncation.
- `logic/rate_limiter.py` -- `RateLimiter`: token-bucket with RPM cap, min interval, jitter, and adaptive 429 backoff. `retry_on_transient(fn, max_retries, rate_limiter)` for auto-retry.
- `logic/usage.py` -- `record_usage()`, `get_summary()`, `get_daily_summary()`, `rotate_usage()` -- persistent JSONL tracking.
- `logic/registry.py` -- `get_provider(name)`, `list_providers()`, `register(name, cls)`.
- `logic/config.py` -- `get_config_value(key)`, `set_config_value(key, value)` -- stores in `data/config.json`.

## Provider Architecture

Providers only implement `_send_request()` (raw API call). The base class `send()` method handles:
1. Latency timing
2. Cost estimation via `CostModel`
3. Automatic usage recording to `data/usage.jsonl`

## Agent GUI Engine

The LLM tool provides a reusable browser-based UI engine for agent interactions.

### Key Files

- `logic/gui/engine.js` — `AgentGUIEngine` class: block registry, SSE streaming, session management, scroll-to-bottom, theming.
- `logic/gui/demo.html` — Demo that feeds protocol events to the engine.

### Interface

```python
from tool.LLM.interface.main import get_agent_gui_path, get_engine_path

get_agent_gui_path()           # → path to demo.html
get_engine_path()    # → path to engine.js
```

### Protocol Event Types

Feed events via `engine.processEvent(evt)` or SSE at `/api/events`:

- `user { prompt, ecosystem, user_rationale, system_state }` — User message. `ecosystem` contains: project_summary, exploration (tool/skill/doc discovery commands), rationale (mental models), standard_tools (available tool list), skills (key skills + usage), agent_behaviors (expected patterns). `system_state` contains: nudge_triggered, quality_warnings, recent_results, discovered_tools.
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

## Provider Reports

When making improvements to provider behavior (prompt engineering, pipeline fixes,
quality feedback mechanisms), document findings in:

```
tool/LLM/logic/models/<model_name>/providers/<vendor>/report/YYYY-MM-DD_topic.md
```

Follow the `development-report` skill for naming and content structure. Reports should
include before/after metrics, root cause analysis, and lessons learned.

Existing reports:
- `providers/zhipu_glm4/report/2026-03-08_quality-feedback-loop.md` — Quality feedback loop infrastructure

## Context Feed Compression

Multi-round agent sessions generate rapidly growing context. The pipeline
applies automatic compression to keep API calls within token limits while
preserving the agent's ability to recall past actions.

### How it works

`compress_history()` in `logic/pipeline.py` processes messages before each
API call. It identifies "rounds" (user message boundaries) and:

- **Last 3 rounds**: Full tool output preserved (agent needs precise content
  for ongoing work).
- **Older rounds**: Tool results compressed to first/last line summaries:
  - `edit_file` → "[ok] Edited {file} ({N} lines)"
  - `read_file` → First line + "..." + last line
  - `exec` → "[ok] `{cmd}` + first/last output lines"
  - `search` → "Searched '{pattern}': ~{N} result lines"
  - `assistant` text → First + last sentence
  - `think` → Preserved in full (already concise)

### Design rationale

Remote model providers (Zhipu, Baidu, Google, etc.) do NOT maintain server-side
session context. Each API call sends the full message history. Without compression,
a 20-round session can exceed 100K tokens, causing failures on models with smaller
context windows and unnecessary API costs.

The round-based approach was chosen over LLM-based summarization because:
1. It's deterministic and fast (no extra API call)
2. It preserves the exact structure agents expect (role/tool_call_id fields)
3. First/last line heuristic retains enough detail for recall without full content
4. The most recent rounds (where active work happens) remain fully intact

### Future work (TODO)

- **Progressive disclosure**: Agent brain tracks what it has explored, enabling
  retrieval-augmented recall of specific old round contents on demand.
- **Semantic round labels**: Each round gets a brief label (e.g., "Read config.py")
  that serves as a compact index for the agent to reference.
- **Initial prompt compression**: System prompt + tool schemas compression to
  reduce the fixed-cost portion of each API call.
- **Multi-range edit_file**: Support a list of (old_text, new_text) pairs in
  a single edit_file call to reduce round trips.

## Dependencies

- PYTHON (managed Python runtime)
