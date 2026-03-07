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
| `nvidia_glm47` | z-ai/glm4.7 (358B) | integrate.api.nvidia.com | 40 RPM, 131K ctx |
| `zhipu_glm4` | glm-4-flash | open.bigmodel.cn | Rate limited, 128K ctx |

## Cross-Tool Interface

Other tools access LLM capabilities via the interface:

```python
from tool.LLM.interface.main import send, get_provider, SessionContext

result = send("What is 2+2?", provider_name="zhipu_glm4")
print(result["text"])
print(result["estimated_cost_usd"])  # Cost estimation per call

provider = get_provider("nvidia_glm47")
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

provider = get_provider("zhipu_glm4")
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

## Architecture

```
tool/LLM/
  main.py                        CLI entry point
  interface/main.py              Cross-tool API
  logic/
    base.py                      LLMProvider ABC + CostModel
    rate_limiter.py              Token-bucket RPM limiter with jitter + retry
    session_context.py           Multi-turn message array manager
    config.py                    API key storage (data/llm_config.json)
    usage.py                     Usage monitoring (data/usage.jsonl)
    registry.py                  Provider discovery and instantiation
    providers/
      nvidia_glm47.py            NVIDIA Build GLM-4.7
      zhipu_glm4.py              Zhipu AI GLM-4-Flash
```

## Configuration

API keys are stored in `tool/LLM/data/llm_config.json`. They can also be set via environment variables `NVIDIA_API_KEY` and `ZHIPU_API_KEY`.
