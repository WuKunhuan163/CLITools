# LLM

Unified LLM provider management with adaptive key selection, rate limiting, usage monitoring, cost tracking, Auto model routing, and multi-turn session context.

## Quick Start

```bash
LLM setup               # Configure API keys (per-provider)
LLM status              # Check provider availability and pricing
LLM providers           # List all providers with details
LLM test                # Send a test message
LLM send "hello"        # One-shot message
LLM usage               # View API usage statistics
LLM usage --period today # Today's usage only
```

## Directory Structure

```
tool/LLM/
  main.py                              CLI entry point
  interface/main.py                    Cross-tool API facade
  data/
    settings.json                      General settings (active_backend, turn limits)
    brain_memory.json                  Long-term agent memory
    report/                            Development reports
  logic/
    config.py                          Config manager (reads per-provider data + settings.json)
    registry.py                        Provider discovery and instantiation

    base/                              Base classes
      __init__.py                      LLMProvider ABC, CostModel, ModelCapabilities
      openai_compat.py                 OpenAI-compatible base (most providers inherit this)
      auto.py                          Auto model selection, provider health tracking

    models/                            One directory per model (max 1 level deep)
      <model_name>/
        main.py                        Primary provider implementation
        model.json                     Model metadata (capabilities, rate limits, cost)
        <vendor>.py                    Secondary vendor implementation (e.g. nvidia.py)
        pipeline.py                    Custom context pipeline (optional)
        logo.svg                       Model favicon (from open-source projects)

    providers/                         One directory per vendor
      <vendor>/
        __init__.py                    Provider module init
        base.py                        Vendor-specific base class (optional)
        data/
          .gitignore                   Prevents tracking of secrets
          keys.json                    API keys + key states for this vendor
          usage.db                     Per-provider usage tracking (SQLite)
        logo.svg                       Vendor favicon (from open-source projects)
      manager.py                       Unified ProviderManager facade
      guides/                          Provider-specific configuration guides

    rate/                              Rate control
      limiter.py                       Token-bucket RPM limiter with jitter + backoff
      queue.py                         Global rate queue manager (cross-provider)
      key_state.py                     Per-key health tracking, adaptive selection

    session/                           Session management
      context.py                       Multi-turn message array manager
      usage.py                         Per-provider usage monitoring (SQLite)
      brain.py                         Long-term memory / brain management
```

## Provider Architecture

### Base Class Hierarchy

```
LLMProvider (base/__init__.py)
  ├── OpenAICompatProvider (base/openai_compat.py)  ← Most models
  │     ├── Google Gemini models
  │     ├── Baidu ERNIE models
  │     ├── DeepSeek models
  │     ├── OpenAI GPT models
  │     ├── SiliconFlow models
  │     └── Tencent Hunyuan models
  ├── AnthropicProvider (providers/anthropic/base.py)
  │     ├── Claude Haiku 4.5
  │     └── Claude Sonnet 4.6
  └── Direct LLMProvider subclasses (custom SDK)
        ├── GLM-4-Flash (zhipu SDK + urllib fallback)
        ├── GLM-4.7 (zhipu SDK)
        ├── GLM-4.7-Flash (zhipu SDK)
        └── GLM-4.7 via NVIDIA (nvidia SDK)
```

### Data Storage

- **API keys & key states**: `providers/<vendor>/data/keys.json` (per-vendor, gitignored)
- **Usage DB**: `providers/<vendor>/data/usage.db` (per-provider SQLite, gitignored)
- **General settings**: `data/settings.json` (active_backend, turn limits, etc.)
- **Model metadata**: `models/<model>/model.json` (capabilities, pricing, rate limits)

### Auto Model Selection

The `auto` provider (`base/auto.py`) uses two preference lists:

- **PRIMARY_LIST (A)**: All models ranked by quality, free first. Used as the candidate pool.
- **FALLBACK_LIST (B)**: Fast non-thinking free models sorted by response speed. Used to make the routing decision.

Decision flow:
1. User prompt → first available model from B decides which model from A to use
2. Decision timeout: 10s. If all B models fail, first available from A is used.
3. Provider health (ProviderHealth) tracks errors with 10-minute sliding windows.
4. Recovery conditions (timed cooldown, user selection) re-enable disabled providers.

### Favicon / Logo Resources

Each model and provider directory can contain a `logo.svg` file. These are sourced from open-source icon projects. The GUI resolves icons in order:
1. `models/<model_name>/logo.svg` (model-specific)
2. `providers/<vendor>/logo.svg` (vendor fallback)
3. Default asset directory icons

To add a logo for a new model: download an SVG from the model's official branding or a reputable open-source icon set, and place it as `logo.svg` in the model directory.

## Creating a New Model

1. Create directory: `logic/models/<model_name>/`
2. Create `model.json` with metadata:
   ```json
   {
     "display_name": "Model Display Name",
     "vendor": "vendor_name",
     "model_id": "api-model-id",
     "capabilities": {
       "max_context_tokens": 128000,
       "max_output_tokens": 4096,
       "tool_calling": true,
       "vision": false,
       "reasoning": false
     },
     "cost": { "free_tier": true },
     "rate_limits": { "free": { "rpm": 30 } }
   }
   ```
3. Create `main.py` extending `OpenAICompatProvider` (or `LLMProvider` for custom APIs):
   ```python
   from tool.LLM.logic.base.openai_compat import OpenAICompatProvider
   from tool.LLM.logic.base import CostModel, ModelCapabilities

   class MyModelProvider(OpenAICompatProvider):
       name = "vendor-model-name"
       CONFIG_VENDOR = "vendor_name"
       API_URL = "https://api.example.com/v1/chat/completions"
       MODEL_ID = "model-id"
       # ... configure cost_model, capabilities, etc.
   ```
4. Register in `logic/registry.py`
5. Add `logo.svg` from the model's official branding

## Creating a New Provider (Vendor)

1. Create directory: `logic/providers/<vendor>/`
2. Add `__init__.py`, `data/` (with `.gitignore` containing `*\n!.gitignore`)
3. Optionally add `base.py` if the vendor has a non-standard API
4. Add `logo.svg` from the vendor's official branding
5. Configure API keys via `LLM setup` or directly in `data/keys.json`

## Cross-Tool Interface

```python
from tool.LLM.interface.main import send, get_provider, SessionContext

result = send("What is 2+2?", provider_name="zhipu-glm-4-flash")
print(result["text"])

provider = get_provider("nvidia-glm-4-7b")
ctx = SessionContext(system_prompt="You are helpful.")
ctx.add_user("Hello")
result = provider.send(ctx.get_messages_for_api())
```

## Rate Limiting

Every provider uses `RateLimiter` (logic/rate/limiter.py) with RPM cap, minimum interval, jitter, and adaptive 429 backoff. The `RateQueueManager` (logic/rate/queue.py) coordinates globally across providers.

`AdaptiveKeySelector` (logic/rate/key_state.py) selects API keys probabilistically based on health scores — success rate, latency, and consecutive failures. Stale keys (auth failures) are excluded until re-verified.

## Dependencies

- PYTHON (managed Python runtime)
