# OPENCLAW

Agent autonomy framework with multi-backend LLM integration. Supports
exploration-driven tool discovery, persistent memory, and an evolution
cycle (lessons -> skills -> tools -> better tools).

## Architecture

```
OPENCLAW (default: HTML GUI; --cli for terminal)
  |
  +-- OpenClawCore (shared state layer)
  |     |-- SessionManager (sessions, messages, operation logs)
  |     |-- LLM provider (streaming + non-streaming)
  |     |-- AgentEnvironment (dynamic context per turn)
  |     |-- Context compression
  |
  +-- CLI GUI (terminal agent, Claude Code-style)
  |     |-- Interactive prompt with /commands
  |     |-- External control injection (cli-inject)
  |     |-- Step display: > step_summary -> commands -> done
  |
  +-- HTML GUI (browser-based, reserved)
  |     |-- LocalHTMLServer (logic/serve/html_server.py)
  |     |-- Sidebar sessions, chat area, input
  |
  v
Pipeline
  |
  +-- Step Protocol
  |     |-- <<STEP: label >> per response
  |     |-- <<OPENCLAW_STEP_COMPLETE>> or <<OPENCLAW_TASK_COMPLETE>>
  |     |-- Streaming via LLM base.stream()
  |
  +-- Sandbox (sandbox.py)
  |     |-- Restricted filesystem view
  |     |-- Special: --openclaw-tool-help, --openclaw-memory-search
  |
  +-- Guardrails
        |-- Token budget, loop detection, command limits
```

## First-Time Setup

```bash
OPENCLAW cli                  # Launch terminal agent
> /setup                      # Configure API key (arrow-key selector + getpass)
```

Get API keys at:
- Zhipu: https://bigmodel.cn/usercenter/proj-mgmt/apikeys
- NVIDIA: https://build.nvidia.com/z-ai/glm4_7

## Commands

```bash
OPENCLAW                      # Launch HTML GUI (default)
OPENCLAW cli                  # Interactive terminal agent (Claude Code-style)
OPENCLAW chat                 # Launch HTML chatbot
OPENCLAW status               # Check LLM provider status
OPENCLAW sessions             # List saved sessions
OPENCLAW setup-llm            # Configure API key
```

### External Control (for testing)

```bash
OPENCLAW cli-list             # List active CLI instances
OPENCLAW cli-status PID       # Query a running CLI's state
OPENCLAW cli-inject PID CMD   # Inject a command into a running CLI
```

## LLM Backends

| Backend | Provider | Rate Limit | Context | Auth |
|---|---|---|---|---|
| `nvidia_glm47` | NVIDIA Build GLM-4.7 | 40 RPM (30 configured) | 131K tokens | API key |
| `zhipu_glm4` | Zhipu GLM-4-Flash | Rate limited | 128K tokens | API key |
| `yuanbao_web` (legacy) | Tencent Yuanbao | N/A | N/A | Manual browser login |

The default backend uses the official GLM-4.7 API via NVIDIA Build, which is
compliant with service terms. The legacy Yuanbao backend uses CDMCP browser
automation (manual login + DOM interaction).

## GUI Theme

The HTML GUI uses the OpenClaw red theme with:
- Red accent color scheme (#d32f2f) matching OpenClaw branding
- Lobster emoji as browser tab favicon
- Official OpenClaw logo and avatar assets
- Warm dark palette with red-brown tones

## Compliance (YAB-Bridge Architecture)

The system follows the YAB-Bridge (Yuanbao-AI-Assistant-Bridge) compliance
framework defined in the Yuanbao conversation:

1. **API-first**: Default backend uses official API, not browser automation.
2. **Manual login only**: Browser backend never automates login.
3. **Rate limiting**: Hard RPM cap (30) with random jitter (0-1s).
4. **No data persistence**: Bridge layer does not persist scraped data.
5. **Local only**: All services bind to 127.0.0.1.

## Protocol

The agent communicates via special tokens:
- `<<STEP: label >>` -- Step summary (first line of every response)
- `<<EXEC: command >>` -- Execute a sandboxed command
- `<<EXPERIENCE: lesson >>` -- Record an experience/lesson
- `<<OPENCLAW_STEP_COMPLETE>>` -- Step done, continue to next step
- `<<OPENCLAW_TASK_COMPLETE>>` -- Entire task done
- `TITLE: Session Title` -- Set session title (first response only)

## Security

Protected paths (agent cannot access):
- `tool/OPENCLAW/` -- The tool itself
- `tool/GOOGLE.CDMCP/` -- CDMCP infrastructure
- `logic/chrome/` -- CDP session management
- `.git/`, `.cursor/` -- Version control and IDE config
