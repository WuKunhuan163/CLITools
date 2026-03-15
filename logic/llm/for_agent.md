# logic/llm -- Agent Reference

## Overview

Shared LLM provider infrastructure for all tools. **Import from `tool.LLM.interface.main`**, not from `logic.llm`.

## API

### Registry
```python
from tool.LLM.interface.main import get_provider, list_providers

providers = list_providers()
provider = get_provider("zhipu-glm-4.7")
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
from tool.LLM.interface.main import SessionContext

ctx = SessionContext("system prompt", max_context_tokens=32000)
ctx.add_user("question")
msgs = ctx.get_messages_for_api()
result = provider.send(msgs)
ctx.add_assistant(result["text"])
```

## Config

API keys stored in `tool/LLM/data/llm_config.json` (per-provider nested format):
```json
{"providers": {"zhipu": {"api_key": "..."}, "nvidia": {"api_key": "..."}}}
```

Also reads from `ZHIPU_API_KEY` / `NVIDIA_API_KEY` environment variables.
