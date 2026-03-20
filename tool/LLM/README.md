# LLM

Unified LLM provider management with rate limiting, usage monitoring, cost tracking, and multi-turn session context.

## Quick Start

```bash
LLM setup               # Configure API keys
LLM status              # Check provider availability and pricing
LLM providers           # List all providers with details
LLM test                # Send a test message
LLM send "hello"        # One-shot message
LLM usage               # View API usage statistics
LLM usage --period today # Today's usage only
```

## Providers

| Provider | Model | Endpoint | Free Tier |
|----------|-------|----------|-----------|
| `nvidia-glm-4-7b` | z-ai/glm4.7 (358B) | integrate.api.nvidia.com | 40 RPM, 131K ctx |
| `zhipu-glm-4-flash` | glm-4-flash | open.bigmodel.cn | Rate limited, 128K ctx |

## Cross-Tool Interface

Other tools access LLM capabilities via the interface:

```python
from tool.LLM.interface.main import send, get_provider, SessionContext

result = send("What is 2+2?", provider_name="zhipu-glm-4-flash")
print(result["text"])
print(result["estimated_cost_usd"])  # Cost estimation per call

provider = get_provider("nvidia-glm-4-7b")
ctx = SessionContext(system_prompt="You are helpful.")
ctx.add_user("Hello")
result = provider.send(ctx.get_messages_for_api())
```

## Rate Limiting and Retry

Every provider has a built-in `RateLimiter` with:
- RPM cap (requests per minute)
- Minimum interval between requests
- Random jitter to avoid anti-bot detection
- Adaptive backoff on consecutive 429 responses

For transient errors (429, 5xx, network), use `retry_on_transient`:

```python
from tool.LLM.interface.main import retry_on_transient, get_provider

provider = get_provider("zhipu-glm-4-flash")
messages = [{"role": "user", "content": "Hello"}]

result = retry_on_transient(
    lambda: provider.send(messages),
    max_retries=3,
    rate_limiter=provider._rate_limiter,
)
```

## Usage Monitoring

Every API call is automatically logged to `data/usage.jsonl` with:
- Timestamp, provider, model
- Token counts (prompt, completion, total)
- Latency, error details, error codes
- Estimated cost (USD)

```python
from tool.LLM.interface.main import get_usage_summary, get_daily_usage_summary

summary = get_usage_summary()         # All-time
daily = get_daily_usage_summary()     # Today only
# {"total_calls": N, "successful": N, "failed": N, "total_tokens": N, ...}
```

## Agent GUI Engine

A reusable, protocol-driven rendering engine for LLM agent UIs. The engine renders streaming tokens, tool calls (exec, edit, read, search), TODO management, exec/call trackers, and session management with a Cursor-inspired dark-mode UI.

### Architecture

The GUI is split into two layers:

- **`engine.js`** — Portable JS class (`AgentGUIEngine`) with zero framework dependencies. Handles all rendering, block registry, SSE streaming, session management, scroll behavior, and theming.
- **`demo.html`** — Thin demo wrapper that feeds protocol events to the engine.

### Embedding in Other Tools

```javascript
const engine = new AgentGUIEngine({
  chatArea: document.getElementById('chat'),
  todoListEl: document.getElementById('todo-list'),
  sessionListEl: document.getElementById('sessions'),
  // ... exec/call panels optional
});

// Custom blocks
engine.registerBlock('memory', (evt) => {
  engine._appendEl('div', 'custom-block', evt.content);
});

// Theme override (e.g. OpenClaw red theme)
engine.loadTheme({ accent: '#e63946', bg: '#1a0a0a' });

// Process events from SSE or backend
engine.connectSSE('/api/events');
// or manually: engine.processEvent({ type: 'text', tokens: 'Hello' });
```

### Protocol Events

| Type | Fields | Description |
|------|--------|-------------|
| `user` | `text` | User message bubble |
| `thinking` | `tokens` | Collapsible thinking block with streaming |
| `text` | `tokens` | Markdown-rendered assistant text |
| `tool` | `name`, `desc`, `cmd`, `file` | Tool call block (exec/edit/read/search) |
| `tool_result` | `ok`, `output` | Tool result with diff rendering for edit blocks |
| `todo` | `items[]` | Initialize TODO list |
| `todo_update` | `id`, `status` | Update a TODO item status |
| `todo_delete` | `id` | Remove a TODO item |
| `experience` | `lesson` | Muted info/experience block |
| `complete` | — | Task completion indicator |

### Session Management

```javascript
engine.addSession('id', 'Title', 'idle');    // idle | running | done
engine.renameSession('id', 'New Title');
engine.deleteSession('id');                  // with confirmation dialog
engine.setSessionStatus('id', 'running');
engine.setActiveSession('id');
engine.onSessionChange((action, session) => { /* rename|delete|activate */ });
```

### Interface Functions

```python
from tool.LLM.interface.main import get_agent_gui_path, get_engine_path

html_path = get_agent_gui_path()           # Full HTML template path
engine_path = get_engine_path()  # Reusable JS engine path
```

## Architecture

```
tool/LLM/
  main.py                        CLI entry point
  interface/main.py              Cross-tool API
  logic/
    base.py                      LLMProvider ABC + CostModel
    rate_limiter.py              Token-bucket RPM limiter with jitter + retry
    session_context.py           Multi-turn message array manager
    config.py                    API key storage (data/config.json)
    usage.py                     Usage monitoring (data/usage.jsonl)
    registry.py                  Provider discovery and instantiation
    providers/
      nvidia_glm47.py            NVIDIA Build GLM-4.7 (ID: nvidia-glm-4-7b)
      zhipu_glm4.py              Zhipu AI GLM-4-Flash (ID: zhipu-glm-4-flash)
    gui/
      engine.js        Reusable rendering engine (AgentGUIEngine)
      demo.html            Demo wrapper with sample protocol events
    dashboard/
      template.html              Usage monitoring dashboard
```

## Configuration

API keys are stored in `tool/LLM/data/config.json`. They can also be set via environment variables `NVIDIA_API_KEY` and `ZHIPU_API_KEY`.
