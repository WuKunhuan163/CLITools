# Infrastructure Improvements: Agent GUI & ConversationManager

**Date**: 2026-03-13
**Scope**: Cross-model improvements to agent infrastructure

## Critical Fixes

### 1. Streaming Text Emission (conversation.py)
**Problem**: Text chunks from streaming LLM responses were accumulated in `full_text` but never emitted as `{"type": "text", "tokens": ...}` events. The HTML GUI showed no agent text during streaming.

**Fix**: Added `self._emit({"type": "text", "tokens": t})` in the streaming loop. Added guard `if full_text and not use_streaming` to prevent double-emission for non-streaming path.

### 2. Thread Exception Handling (conversation.py)
**Problem**: `send_message` spawned daemon threads for `_run_turn`. Any uncaught exception killed the thread silently — no error message, no status update. Session stayed in limbo.

**Fix**: Wrapped thread target in `_safe_run` that catches exceptions, prints traceback to stderr, emits error event, and sets session status to "idle".

### 3. Pre-Try Code Protection (conversation.py)
**Problem**: Lines 1130-1178 (ecosystem build, message packaging) were outside the `try/except` block. Exceptions here killed the thread silently.

**Fix**: Moved the `try:` block to cover the entire function body after session validation.

### 4. Turn-Limit Context Loss (conversation.py)
**Problem**: When the turn limit was reached, the `return` statement executed before `session.context.add_assistant(full_text)`. The final text response was streamed to the frontend but lost from context.

**Fix**: Added `session.context.add_assistant(full_text)` before the turn-limit return.

### 5. Read File Limit (conversation.py)
**Problem**: `read_file` truncated at 3000 characters. Many real files (5-14KB) lost critical code beyond the cutoff. Agents couldn't see the code they needed to edit.

**Fix**: Increased to 12000 characters.

## Zhipu SDK Fixes

### 6. stream_options Not Supported
**Problem**: `stream_options: {"include_usage": True}` passed to SDK's `chat.completions.create()` raised `TypeError: unexpected keyword argument`. Every streaming call failed.

**Fix**: Removed `stream_options` from SDK path (kept in urllib path where the API accepts it).

**Affected files**: 
- `models/glm_4_7_flash/providers/zhipu/interface/__init__.py`
- `models/glm_4_7/providers/zhipu/interface/__init__.py`

### 7. SDK Client Timeout
**Problem**: `ZhipuAI()` initialized without timeout. API calls could hang indefinitely.

**Fix**: Added `httpx.Timeout(timeout=120.0, connect=10.0)` to client initialization with fallback to no-timeout if httpx not available.

### 8. SDK Stream Chunk Timeout
**Problem**: `for chunk in response:` could block forever if the API stalled mid-stream.

**Fix**: Wrapped the stream iterator in a background thread with a queue. Main thread reads from queue with 90s timeout per chunk.

## Behavioral Improvements

### 9. Silent Tool Call Nudge
After 3 consecutive rounds of tool calls with `content=None` (no explanatory text), inject: "[System] You made 3+ rounds of tool calls without any explanatory text. Write a text response describing what you've found so far."

### 10. Summary Detection in Nudge Logic
`_should_nudge()` incorrectly triggered "apply your fix" nudge on research/analysis responses. Added summary indicators ("总结", "分析", "结论", etc.) to skip nudge when response is clearly an analysis.

### 11. Turn-Limit Approach Nudge Threshold
The "approaching turn limit" nudge fired at round 1 for `turn_limit=2`. Changed to only fire when `turn_limit > 3`.

### 12. System Prompt Strengthening
- "**KEY RULE**: Every response MUST contain text" (was merely "should include")
- "Maximum 2 search attempts" (prevent infinite search loops)
- "A task without a summary is considered incomplete"
