# OPENCLAW

OpenClaw-inspired agent autonomy framework for AITerminalTools. Supports
two LLM backends: GLM-4.7 via NVIDIA Build API (compliant, free) and
Tencent Yuanbao via CDMCP browser automation (legacy).

## Architecture

```
OPENCLAW GUI (HTML default / tkinter fallback)
  |-- Sidebar: session list (create, switch, delete)
  |-- Chat area: message bubbles (user, assistant, system, feedback)
  |-- Input area: text entry + send
  |
  v
Pipeline (background thread)
  |
  +-- API Pipeline (nvidia_glm47, default)
  |     |-- SessionContext manages messages array
  |     |-- RateLimiter with RPM cap + jitter
  |     |-- HTTP POST to integrate.api.nvidia.com/v1/chat/completions
  |     |-- OpenAI-compatible format
  |
  +-- Browser Pipeline (yuanbao_web, legacy)
        |-- CDMCP: Quill editor + DOM scraping
        |-- Chrome CDP on port 9222
        |-- Manual login required
  |
  v
Sandbox (sandbox.py)
  |-- Restricted filesystem view
  |-- Commands: ls, cat, grep, python3, etc.
  |-- Special: --openclaw-memory-search, --openclaw-tool-help, etc.
```

## First-Time Setup

```bash
OPENCLAW setup-llm            # Enter NVIDIA API key (from build.nvidia.com)
OPENCLAW chat                 # Launch GUI with GLM-4.7 backend
```

Get your free API key at: https://build.nvidia.com/z-ai/glm4_7

## Commands

```bash
OPENCLAW                      # Show help
OPENCLAW chat                 # Launch HTML chatbot (GLM-4.7 API)
OPENCLAW chat --backend yuanbao_web  # Use Yuanbao browser backend
OPENCLAW chat --gui tkinter   # Launch tkinter GUI
OPENCLAW status               # Check LLM provider status
OPENCLAW sessions             # List saved sessions
OPENCLAW setup-llm            # Configure NVIDIA API key
```

## LLM Backends

| Backend | Provider | Rate Limit | Context | Auth |
|---|---|---|---|---|
| `nvidia_glm47` (default) | NVIDIA Build GLM-4.7 | 40 RPM (30 configured) | 131K tokens | API key |
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

The remote agent communicates via special tokens:
- `<<EXEC: command >>` -- Execute a sandboxed command
- `<<EXPERIENCE: lesson >>` -- Record an experience/lesson
- `<<OPENCLAW_TASK_COMPLETE>>` -- Signal task completion
- `TITLE: Session Title` -- Set session title (first response only)

## Security

Protected paths (agent cannot access):
- `tool/OPENCLAW/` -- The tool itself
- `tool/GOOGLE.CDMCP/` -- CDMCP infrastructure
- `logic/chrome/` -- CDP session management
- `.git/`, `.cursor/` -- Version control and IDE config
