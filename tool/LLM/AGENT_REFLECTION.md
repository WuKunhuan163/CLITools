# LLM — Agent Self-Reflection

## Purpose

This file is a **stable reflection guide** for agents working on the LLM tool. It prompts self-evaluation and identifies improvement opportunities. It is NOT a recording file — session discoveries go to `BRAIN log` / `SKILLS learn`, not here.

## How to Update This File

This file should be **refined, not grown**:
- **Fix a gap** → remove it and briefly note the replacement
- **Discover a tool-level gap** → add it, keep to 3-5 gaps
- **Session-specific notes** → `BRAIN log`, `SKILLS learn`, `runtime/experience/lessons.jsonl`
- **Never add a changelog** — that belongs in git history

## Self-Check (after each task on this tool)

- **Discovery**: Did I read `tool/LLM/AGENT.md` and search for related skills before coding?
- **Interface**: Did I expose reusable functionality in `interface/main.py`?
- **Testing**: Did I run existing tests and test new changes (at least via `tmp/` scripts)?
- **Documentation**: Did I update `README.md` and `AGENT.md` to reflect my changes?
- **Model config**: Did I update `model.json` with correct pricing, rate limits, and capabilities?
- **Frontend sync**: Did I add model logos and display names to `live.html`?
- **Registry**: Did I register new models and aliases in `registry.py`?

## Known Gaps

- **Token counter not wired into streaming pipeline**: `token_counter.py` supports tiktoken but isn't called automatically during streaming for real-time cost tracking.
- **Baidu rate limits are estimates**: Official per-model RPM/TPM for Qianfan V2 are undocumented. Current values (200-300 RPM) are conservative. Monitor 429 responses.
- **Stale key state recovery**: When a provider's auth method changes, old `key_states` in `config.json` may have stale failure counts requiring manual reset.

## Design Notes

- All Baidu ERNIE models use `OpenAICompatProvider` with `MAX_TOKENS_PARAM = "max_completion_tokens"`. The Qianfan V2 API is fully OpenAI-compatible.
- Gemini free/paid is at the GCP project level, not per-request. Cannot programmatically tag "free" vs "paid" calls.
- `model.json` prices are per 1M tokens (not 1K). The frontend reads `input_per_1m` / `output_per_1m` directly.
- ERNIE-5.0 (reasoning model) consumes thinking tokens within the max_tokens budget. Use >= 100 max_tokens for testing.
