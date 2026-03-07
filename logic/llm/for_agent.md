# logic/llm -- Agent Reference

## Overview

Shared LLM provider infrastructure for all tools. Use the registry to
get a provider, then call `send()` with an OpenAI-format messages array.

## API

### Registry
```python
from logic.llm.registry import get_provider, list_providers, get_default_provider

providers = list_providers()
provider = get_provider("nvidia-glm-4-7b")
provider = get_default_provider()
```

### LLMProvider.send()
```python
result = provider.send(
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7,
    max_tokens=16384,
)
# result = {"ok": True, "text": "...", "usage": {...}, "finish_reason": "stop"}
```

### SessionContext
```python
from logic.llm.session_context import SessionContext

ctx = SessionContext("system prompt", max_context_tokens=32000)
ctx.add_user("question")
msgs = ctx.get_messages_for_api()
result = provider.send(msgs)
ctx.add_assistant(result["text"])
```

### RateLimiter
```python
from logic.llm.rate_limiter import RateLimiter

rl = RateLimiter(rpm=30, min_interval_s=2.0, jitter_s=1.0)
rl.wait()  # blocks until next request is permitted
```

## Config

API keys stored in `data/llm_config.json`:
```json
{"nvidia_api_key": "nvapi-..."}
```

Also reads from `NVIDIA_API_KEY` environment variable.
