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

## Directory Structure

```
tool/LLM/
  logic/
    config.py              Config reads per-provider data/keys.json + data/settings.json
    registry.py            get_provider(name), list_providers(), register(name, cls)
    base/
      __init__.py          LLMProvider ABC, CostModel, ModelCapabilities
      openai_compat.py     OpenAI-compatible base (most providers extend this)
      auto.py              Auto model selection, PRIMARY_LIST, FALLBACK_LIST
    models/<name>/
      main.py              Provider implementation (inherits base class)
      model.json           Model metadata: capabilities, rate_limits, cost, vendor
      pipeline.py          Custom context pipeline (optional)
      <vendor>.py          Secondary vendor implementation (optional)
      logo.svg             Model-specific favicon
    providers/<vendor>/
      data/keys.json       API keys + key states (gitignored)
      data/usage.db        Per-provider usage DB (gitignored)
      logo.svg             Vendor favicon
      manager.py           Unified ProviderManager (aggregates health, keys, rate limits)
    rate/
      limiter.py           RateLimiter: RPM cap, jitter, adaptive 429 backoff
      queue.py             RateQueueManager: global cross-provider coordination
      key_state.py         AdaptiveKeySelector: per-key health scoring
    session/
      context.py           SessionContext: multi-turn message manager
      usage.py             Per-provider usage monitoring (SQLite)
      brain.py             Long-term agent memory
```

## Providers

27 provider implementations across 9 vendors:

| Vendor | Models | Free Tier | Key Field |
|--------|--------|-----------|-----------|
| zhipu | glm-4-flash, glm-4.7, glm-4.7-flash | Yes (RPM limited) | `zhipu_api_key` |
| google | gemini-2.5-flash, 2.5-pro, 3-flash, 3.1-flash-lite, 3.1-pro, 2.5-flash-lite | Yes (RPM limited) | `google_api_key` |
| baidu | ernie-speed-8k, ernie-4.0-turbo-8k, ernie-4.5-*, ernie-5.0, ernie-x1.* | Partial | `baidu_api_key` |
| tencent | hunyuan-lite | Yes | `tencent_api_key` |
| siliconflow | qwen2.5-7b | Yes | `siliconflow_api_key` |
| nvidia | glm-4-7b | Yes (40 RPM) | `nvidia_api_key` |
| anthropic | claude-haiku-4.5, claude-sonnet-4.6 | No | `anthropic_api_key` |
| openai | gpt-4o, gpt-4o-mini | No | `openai_api_key` |
| deepseek | chat, reasoner | No | `deepseek_api_key` |

### Auto Model Selection

Use `auto` as provider name. Uses two lists:
- **List A (PRIMARY_LIST)**: All models ranked by quality (free first)
- **List B (FALLBACK_LIST)**: Fast non-thinking free models sorted by response speed for routing decisions

Decision timeout: 10s. Falls back to first available from A if all B fail.

The ProviderManager (`providers/manager.py`) aggregates per-key health, rate limiter state, and provider-level health into a unified status API. The Auto decision prompt includes UTC timestamps, 429 labels, and expected recovery times.

### Rate Limit Tuning

Provider rate limits are empirically calibrated. When encountering 429s:

1. Check status: `POST /api/provider/status {"provider": "zhipu-glm-4.7-flash"}`
2. Adjust `rate_limits` in `models/<model>/model.json`
3. Key parameters: `rpm`, `max_concurrency`, `min_interval_s`, `jitter_s`
4. Verify: monitor subsequent calls for zero 429s

### Creating a New Model

1. `logic/models/<model_name>/` — create directory with `model.json` + `main.py`
2. `main.py` extends `OpenAICompatProvider` (or `LLMProvider` for custom APIs)
3. Register in `logic/registry.py`
4. Add `logo.svg` from official branding / open-source icon set

### Creating a New Provider (Vendor)

1. `logic/providers/<vendor>/` — create with `__init__.py`, `data/.gitignore`
2. Optionally add `base.py` for vendor-specific base class
3. Add `logo.svg` from vendor branding
4. Keys stored in `data/keys.json`, usage in `data/usage.db` (both gitignored)

## Data Storage

| Data | Location | Gitignored |
|------|----------|------------|
| API keys + key states | `providers/<vendor>/data/keys.json` | Yes |
| Usage tracking | `providers/<vendor>/data/usage.db` | Yes |
| General settings | `data/settings.json` | No |
| Model metadata | `models/<model>/model.json` | No |
| Brain memory | `data/brain_memory.json` | No |

## Live Agent GUI

```bash
LLM --assistant --gui "task description"   # Open GUI with initial prompt
LLM --assistant --gui                      # Open GUI (no prompt)
LLM --assistant --gui --workspace /path    # Mount workspace directory
```

The frontend shows:
- Session ID and workspace path in the title bar
- Real-time SSE streaming of agent events
- Task timing from prompt submission to completion (includes Auto decision time)
- Task failed status on 429/error exits (not "Task completed")

### HTTP API

- `POST /api/send` — Send message to session
- `POST /api/session` — Create new session
- `POST /api/rename` / `POST /api/delete` — Session management
- `GET /api/sessions` — List sessions
- `GET /api/state` — Full state dump
- `POST /api/provider/status` — Provider health status

## Key Modules

- `logic/base/__init__.py` — `LLMProvider` ABC with unified `send()` (auto-records usage, measures latency, estimates cost)
- `logic/base/openai_compat.py` — `OpenAICompatProvider`: shared implementation for OpenAI-compatible APIs
- `logic/base/auto.py` — `AutoProvider`, `auto_decide()`, `ProviderHealth`, preference lists
- `logic/config.py` — Reads per-provider `data/keys.json` + general `data/settings.json`
- `logic/registry.py` — `get_provider(name)`, `list_providers()`, `register(name, cls)`
- `logic/providers/manager.py` — `ProviderManager`: unified health, keys, rate limits, status API
- `logic/rate/key_state.py` — `AdaptiveKeySelector`: weighted random key selection by health score
- `logic/rate/limiter.py` — `RateLimiter`: token-bucket with RPM, jitter, adaptive 429 backoff
- `logic/rate/queue.py` — `RateQueueManager`: global rate coordination
- `logic/session/context.py` — `SessionContext`: message array manager with auto-truncation
- `logic/session/usage.py` — Per-provider SQLite usage tracking
- `logic/session/brain.py` — Long-term memory management

## Dependencies

- PYTHON (managed Python runtime)
