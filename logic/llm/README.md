# logic/llm -- Shared LLM Provider Infrastructure

Canonical implementation lives in `tool/LLM/`. Import directly from `tool.LLM.interface.main`:

```python
from tool.LLM.interface.main import get_provider, SessionContext

provider = get_provider("zhipu-glm-4.7")
result = provider.send([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
])
print(result["text"])
```

## Canonical Source

All LLM logic lives in `tool/LLM/logic/`. See `tool/LLM/README.md` for full documentation.

## Adding New Providers

1. Create `tool/LLM/logic/providers/<name>/interface/__init__.py` implementing `LLMProvider._send_request()`.
2. Create `tool/LLM/logic/providers/<name>/pipeline/context.py` for model-specific quirks.
3. Register in `tool/LLM/logic/registry.py`'s `_ensure_builtins()`.
