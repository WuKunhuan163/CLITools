# logic/llm -- Shared LLM Provider Infrastructure

Provides a unified interface for calling LLM APIs from any tool in the
AITerminalTools project. Inspired by OpenClaw's architecture where the
"brain" communicates with LLMs via clean API contracts.

## Quick Start

```python
from logic.llm.registry import get_provider

provider = get_provider("nvidia_glm47")
result = provider.send([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
])
print(result["text"])
```

## Providers

| Name | Model | Endpoint | Rate Limit | Context |
|---|---|---|---|---|
| `nvidia_glm47` | z-ai/glm4.7 | integrate.api.nvidia.com | 30 RPM | 131K tokens |

## Modules

- `base.py` -- `LLMProvider` abstract interface
- `nvidia_glm47.py` -- NVIDIA Build GLM-4.7 client (OpenAI-compatible)
- `rate_limiter.py` -- Token-bucket rate limiter with RPM cap and jitter
- `session_context.py` -- Multi-turn messages array manager with auto-truncation
- `registry.py` -- Provider discovery and instantiation

## Configuration

API keys and provider settings are stored in `data/llm_config.json`.
Set via environment variable `NVIDIA_API_KEY` or programmatically:

```python
from logic.llm.nvidia_glm47 import save_api_key
save_api_key("nvapi-...")
```

## Multi-Turn Sessions

```python
from logic.llm.session_context import SessionContext

ctx = SessionContext("You are a coding assistant.", max_context_tokens=32000)
ctx.add_user("Write a fibonacci function")
messages = ctx.get_messages_for_api()
result = provider.send(messages)
ctx.add_assistant(result["text"])
```

## Rate Limiting

All providers use `RateLimiter` with configurable RPM, minimum interval,
and random jitter to avoid triggering anti-bot detection.

## Adding New Providers

1. Create `logic/llm/my_provider.py` implementing `LLMProvider`.
2. Register in `registry.py`'s `_ensure_builtins()`.
3. Update this README.
