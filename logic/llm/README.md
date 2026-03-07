# logic/llm -- Shared LLM Provider Infrastructure

Re-exports from `tool/LLM/`. All modules in this directory delegate to the canonical implementation in `tool/LLM/logic/`.

## Quick Start

```python
from logic.llm import get_provider, SessionContext, RateLimiter, CostModel

provider = get_provider("nvidia_glm47")
result = provider.send([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
])
print(result["text"])
print(result["latency_s"], result["estimated_cost_usd"])
```

## Canonical Source

All LLM logic lives in `tool/LLM/logic/`. See `tool/LLM/README.md` for full documentation.

## Modules

All re-export from `tool/LLM/logic/`:

- `base.py` -- `LLMProvider`, `CostModel`
- `nvidia_glm47.py` -- `NvidiaGLM47Provider`, `get_api_key`, `save_api_key`
- `rate_limiter.py` -- `RateLimiter`, `retry_on_transient`
- `session_context.py` -- `SessionContext`
- `registry.py` -- `get_provider`, `list_providers`, `register`, `get_default_provider`
- `__init__.py` -- Convenience re-exports of all major classes

## Adding New Providers

1. Create `tool/LLM/logic/providers/my_provider.py` implementing `LLMProvider._send_request()`.
2. Set `cost_model = CostModel(...)` on the class for pricing metadata.
3. Register in `tool/LLM/logic/registry.py`'s `_ensure_builtins()`.
4. Optionally add a re-export in `logic/llm/`.
