# OPENCLAW -- Agent Reference

## Quick Start

```bash
OPENCLAW                               # Launch HTML GUI (default)
OPENCLAW cli                           # Interactive terminal agent (Claude Code-style)
OPENCLAW status                        # Check all LLM provider status
OPENCLAW sessions                      # List saved sessions
OPENCLAW setup-llm                     # Configure API keys
```

### CLI Commands (inside `OPENCLAW cli`)

| Command | Description |
|---------|-------------|
| `/setup` | Configure API key and select model (arrow-key selector) |
| `/help` | Show available commands |
| `/new` | Start a new session |
| `/sessions` | List saved sessions |
| `/resume <id>` | Resume a previous session |
| `/status` | Show provider and session status |
| `/context` | Show current context token usage |
| `/dashboard` | Launch LLM usage dashboard in browser |
| `/quit` | Exit CLI |

### External Control (for testing)

```bash
OPENCLAW cli-inject PID "task text"    # Inject a task into a running CLI
OPENCLAW cli-status PID               # Query CLI state
OPENCLAW cli-list                     # List active CLI instances
```

### Prompt Indicators
- `>` default (idle) -> blue (running) -> green (step done) -> red (error)
- Step summary replaces "Thinking..." when agent provides `<<STEP: label >>`

## Architecture

```
OpenClawCore (shared state)
  +-- SessionManager
  +-- LLM Provider (streaming + non-streaming)
  +-- AgentEnvironment (dynamic context)
  +-- Context compression
  |
  +-- CLI GUI (cli.py) -- terminal
  +-- HTML GUI (chat_html.py) -- browser
```

### LLM Backends (via `--backend`)

| Backend | Provider | Rate Limit | Context | Streaming |
|---------|----------|------------|---------|-----------|
| `nvidia-glm-4-7b` | NVIDIA Build GLM-4.7 | 30 RPM | 131K | SSE |
| `zhipu-glm-4-flash` | Zhipu GLM-4-Flash | 30 RPM | 128K | SSE |

### Step Protocol

Each agent response follows:
1. `<<STEP: brief label >>` -- what the agent is doing
2. Reasoning text + `<<EXEC: command >>` commands
3. `<<OPENCLAW_STEP_COMPLETE>>` or `<<OPENCLAW_TASK_COMPLETE>>`

## Key Components

### Core (`logic/core.py`)
- `OpenClawCore` -- shared state layer for all GUIs
- Owns SessionManager, provider, contexts, compression settings
- GUIs wrap core with display-specific behavior

### LLM Layer (via `tool/LLM`)
- `base.py` -- `LLMProvider` abstract interface (send, stream, is_available)
- `stream()` -- yields text chunks with usage tracking
- `rate_limiter.py` -- RPM cap with jitter
- `session_context.py` -- context management with auto-compression

### Context Compression
When context exceeds `compression_trigger` ratio of max tokens (default 0.5), the agent is asked to summarize its conversation down to `compression_target` ratio (default 0.1). The summary replaces the full history, preserving recent actions and discovered context.

### Agent Environment
Each turn sends the agent's "surroundings" -- tools, interfaces, and skills it has discovered through exploration. This is ephemeral (resets each session) and separate from persistent memory (lessons).

### System Prompt (Lean)
The system prompt does NOT list all tools or skills. Instead, the agent uses `TOOL --search` commands to discover what it needs. This keeps the prompt under 8KB.

### Pipelines
- `pipeline_api.py` -- API-based pipeline (GLM-4.7): sends messages array, parses response, executes commands, loops
- `pipeline.py` -- Browser-based pipeline (Yuanbao): same loop but uses CDMCP DOM interaction

### Interfaces
- `logic/gui/cli.py` -- Terminal agent (Claude Code-style): interactive prompt, inline spinners, color-coded output
- `logic/gui/chat_html.py` -- HTML GUI adapter (routes to correct pipeline based on backend)
- `logic/gui/chat.py` -- tkinter GUI (legacy fallback)

### Protocol (`logic/protocol.py`)
- `build_system_prompt()` -- lean prompt (no full tool listings)
- `build_task_message()` -- task + runtime state + agent environment
- `parse_response_segments()` -- parse response into interleaved thought/command/experience segments
- `AgentEnvironment` -- dynamic context tracking per turn

### Other
- `logic/sandbox.py` -- Restricted command execution with `--openclaw-*` special commands
- `logic/session.py` -- Session persistence (JSON files + operation logs)
- `logic/guardrails.py` -- Token budget, loop detection, command limits
- `logic/skills.py` -- Active skill chaining on error

## GLM-4.7 API Details

**Endpoint**: `POST https://integrate.api.nvidia.com/v1/chat/completions`

**Request format** (OpenAI-compatible):
```json
{
  "model": "z-ai/glm4.7",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "max_tokens": 16384,
  "stream": false
}
```

**Headers**: `Authorization: Bearer <NVIDIA_API_KEY>`

**Limits**:
- 40 RPM platform limit (we configure 30 RPM with 2s min interval + 0-1s jitter)
- 131,072 tokens input context
- 131,072 tokens max output

## Compliance (YAB-Bridge)

This tool follows the YAB-Bridge compliance framework:

1. **API-first**: GLM-4.7 via official API (no browser automation for LLM calls)
2. **Manual login**: Yuanbao backend never automates login; user logs in manually
3. **Rate limiting**: Hard 30 RPM cap + random jitter to avoid anti-bot triggers
4. **No data persistence**: Pipeline does not persist captured content to disk
5. **Local only**: All services bind to 127.0.0.1
6. **Responsibility separation**: OpenClaw (brain) never touches target web pages;
   CDMCP Bridge (hands) only executes atomic operations

## Token Storage

- `data/config.json` -- NVIDIA API key and provider settings

## Known Issues

- Stdout buffering: `main.py` sets `PYTHONUNBUFFERED=1` and uses `flush=True`.
- Browser open: `ChatbotServer.open_browser()` falls back to `webbrowser.open()` if CDP unavailable.
- Context truncation: SessionContext estimates tokens at 4 chars/token; long conversations may lose early context.

## Dependencies

- GOOGLE.CDMCP (Chrome tab/session management, only for yuanbao_web backend)
- websockets (Python package, for HTML GUI WebSocket)
