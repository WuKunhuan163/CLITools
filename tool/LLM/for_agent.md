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
result = send("Hello", provider_name="zhipu_glm4")
# result = {"ok": True, "text": "...", "usage": {...},
#           "latency_s": 1.2, "estimated_cost_usd": 0.0}

# With retry on transient errors
provider = get_provider("nvidia_glm47")
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
| `nvidia_glm47` | z-ai/glm4.7 | integrate.api.nvidia.com/v1/chat/completions | `nvidia_api_key` / `NVIDIA_API_KEY` | 30 | 131K |
| `zhipu_glm4` | glm-4-flash | open.bigmodel.cn/api/paas/v4/chat/completions | `zhipu_api_key` / `ZHIPU_API_KEY` | 30 | 128K |

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

## Dependencies

- PYTHON (managed Python runtime)
