# OPENCLAW -- Agent Reference

## Quick Start

```bash
OPENCLAW setup-llm                     # One-time: configure NVIDIA API key
OPENCLAW chat                          # Launch GUI (GLM-4.7 API backend)
OPENCLAW chat --backend yuanbao_web    # Legacy: Yuanbao browser backend
OPENCLAW status                        # Check all LLM provider status
OPENCLAW sessions                      # List saved sessions
```

## Architecture

OPENCLAW supports two LLM backends selected via `--backend`:

### nvidia_glm47 (default, compliant)
- GLM-4.7 via NVIDIA Build free API
- OpenAI-compatible endpoint: `integrate.api.nvidia.com/v1/chat/completions`
- Model: `z-ai/glm4.7` (358B params, 131K context)
- Rate limited: 30 RPM with random jitter
- Session context managed client-side via messages array

### yuanbao_web (legacy)
- Tencent Yuanbao via CDMCP browser automation
- Requires Chrome with `--remote-debugging-port=9222`
- Manual login required (no automated auth)
- DOM interaction via Quill editor + CDP

## Key Components

### LLM Layer (`logic/llm/`)
- `base.py` -- `LLMProvider` abstract interface (send, is_available, get_info)
- `nvidia_glm47.py` -- NVIDIA Build client with OpenAI-compatible HTTP calls
- `rate_limiter.py` -- Token-bucket rate limiter with RPM cap and jitter
- `session_context.py` -- Messages array manager with auto-truncation

### Pipelines
- `pipeline_api.py` -- API-based pipeline (GLM-4.7): sends messages array, parses response, executes commands, loops
- `pipeline.py` -- Browser-based pipeline (Yuanbao): same loop but uses CDMCP DOM interaction

### Other
- `logic/chrome/api.py` -- Yuanbao DOM interaction (create conversation, send messages, capture responses)
- `logic/sandbox.py` -- Restricted command execution with `--openclaw-*` special commands
- `logic/protocol.py` -- System prompt construction and response parsing
- `logic/session.py` -- Session persistence (JSON files)
- `logic/gui/chat_html.py` -- HTML GUI adapter (routes to correct pipeline based on backend)

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

- `data/llm_config.json` -- NVIDIA API key and provider settings

## Known Issues

- Stdout buffering: `main.py` sets `PYTHONUNBUFFERED=1` and uses `flush=True`.
- Browser open: `ChatbotServer.open_browser()` falls back to `webbrowser.open()` if CDP unavailable.
- Context truncation: SessionContext estimates tokens at 4 chars/token; long conversations may lose early context.

## Dependencies

- GOOGLE.CDMCP (Chrome tab/session management, only for yuanbao_web backend)
- websockets (Python package, for HTML GUI WebSocket)
