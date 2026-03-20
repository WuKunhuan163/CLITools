# Critical Fix: read_file Standard Tool Truncation

**Date**: 2026-03-14  
**Scope**: Cross-model — affects all agents regardless of provider  
**Impact**: Task #32 score 2/10 → 8/10; unlocked multi-file navigation

## Problem

The agent could not navigate large files or cross-reference multiple files. Symptoms:
- Repeated reading of the same file 5-10 times without progress
- Never extracting configuration values from provider files
- Inability to complete any task requiring > 3 file reads

Root cause: **Two `read_file` handlers existed**, and the wrong one took priority.

| Handler | Location | Char Limit | Registered |
|---------|----------|-----------|-----------|
| Standard tool | `logic/assistant/std/tools.py` | **3000** | Via `@register_tool("read_file")` decorator |
| Conversation fallback | `tool/LLM/logic/task/agent/conversation.py` | 12000 | As a method, never called |

The standard tool's `@register_tool` decorator registered it in the global `TOOL_HANDLERS` dict. When `ConversationManager._handle_tool_call()` dispatched tool calls, it checked `TOOL_HANDLERS` first, finding the 3000-char version. The 12000-char implementation in `conversation.py` (added 2026-03-13 fix #5) was dead code.

For a typical provider file (~183 lines, ~6500 chars), the agent saw only the first ~80 lines — missing class methods, configuration parameters, and `from_model_json()` patterns.

## Fix

Updated `logic/assistant/std/tools.py:handle_read_file`:

1. **Char limit**: 3000 → 12000
2. **start_line/end_line**: Added parameter support for targeted reads
3. **Truncation message**: Includes total lines/chars and suggests `start_line/end_line`
4. **exec output**: 3000 → 6000 chars (related fix in same file)

## Evidence

Task #32: Cross-File Config Audit (8/10 difficulty)

**Before** (session b2e1bd51): Agent searched for `RateLimiter`, found 4 files, then spent 10 rounds re-reading `rate_limiter.py` without ever reading provider files. Score: 2/10.

**After** (session 63ae023b): Agent searched, then methodically read each provider's `__init__.py` using `start_line`/`end_line`, extracted RPM/interval/jitter configs, wrote a structured report with table, findings, and recommendations. Score: 8/10.

## Lesson

When implementing a tool fix, verify which handler is actually dispatched. Multiple implementations of the same tool name in different modules can shadow each other via registration order. The fix must target the handler that the dispatch system actually calls.
