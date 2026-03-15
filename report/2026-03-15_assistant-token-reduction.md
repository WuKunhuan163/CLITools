# Assistant Token Consumption Reduction

## Summary

This report details the mechanisms implemented to reduce input/output token consumption and slow context length growth in the AITerminalTools agent assistant system.

## Current Mechanisms

### 1. Line-Range-Based Editing Protocol

**Before**: The `edit_file` tool accepted `old_text` (the original text to find and replace) and `new_text`. This required the LLM to echo potentially large blocks of original file content in its output, consuming output tokens proportional to the code being modified.

**After**: The protocol uses `start_line`, `end_line`, and `new_text`. The LLM only needs to specify line numbers and the replacement text — never echoing original content.

**Impact**:
- Output tokens per edit reduced by ~50-80% for typical edits (no longer echoing `old_text`)
- Context growth per tool call reduced proportionally since assistant messages are shorter

**Implementation**:
- `logic/assistant/std/tools.py:handle_edit_file` — removed `old_text` parameter, `start_line`/`end_line` mandatory for existing files
- `logic/assistant/gui/server.py:_SYSTEM_PROMPT` — updated editing instructions to only reference line-range parameters
- `tool/LLM/logic/task/agent/conversation.py` — nudge prompts updated to reference `start_line`/`end_line`/`new_text`

### 2. Provider Max Output Clamping

**Problem**: `ConversationManager` requested `max_tokens=16384` for all providers, but some (e.g., ERNIE Speed 8K) only support up to 4096. Unclamped values caused HTTP 400 errors.

**Fix**: `tool/LLM/logic/openai_compat.py` now clamps `max_tokens` to `min(requested, provider.DEFAULT_MAX_OUTPUT)` before sending to the API. This prevents wasted retries and ensures the LLM generates within bounds.

**Implementation**:
- `openai_compat.py:_send_request` and `send_streaming` — effective max = min(max_tokens, DEFAULT_MAX_OUTPUT)

### 3. Context Compression Pipeline

The existing `_compress_context` method (called when context exceeds thresholds) summarizes older messages. This was already in place but now works more effectively with the reduced per-round context additions from mechanism #1.

## Measured Results

From a 7-round agent session (fibonacci task, GLM-4.7-Flash):

| Metric | Value |
|--------|-------|
| Starting context (prompt tokens) | 3,581 |
| Final context (round 7) | 5,477 |
| Avg context growth per round | ~316 tokens |
| Total output tokens (7 rounds) | 1,395 |
| Avg output per round | ~199 tokens |

The ~316 tokens/round context growth includes the assistant's response text, tool call arguments, and tool results. With the old `old_text`-based protocol, a single file edit could add 500+ tokens just for the echoed original text.

## Future Work: Enterprise-Grade Implementations

### 1. Sliding Window Context with RAG

Instead of keeping all messages in context, maintain only the last N rounds in the LLM context window. Older messages are indexed in a vector store (e.g., ChromaDB, Pinecone) and retrieved on-demand when semantically relevant to the current task.

**Expected reduction**: 60-80% context size for long sessions (>10 rounds)

### 2. Structured Tool Result Compression

Tool results (file reads, command outputs) are often verbose. A dedicated compression step could:
- Summarize long file contents to relevant sections
- Truncate command output to the actionable portion
- Replace repeated file reads with cached references

**Expected reduction**: 30-50% reduction in tool result tokens

### 3. Semantic Deduplication

Detect when the same information appears multiple times in context (e.g., file read twice, same error repeated) and replace duplicates with back-references.

**Expected reduction**: 10-20% for typical multi-round sessions

### 4. Dynamic Max Output Budgeting

Instead of a fixed `max_tokens`, dynamically set the output budget based on:
- Remaining context window capacity
- Task complexity (simple Q&A vs. multi-file edit)
- Round number (later rounds should be more concise)

**Expected reduction**: 20-30% total output tokens

### 5. Progressive Prompt Compression (LLMLingua / AutoCompressor)

Use trained prompt compression models to reduce the token count of system prompts and historical context while preserving semantic content. Research systems like LLMLingua can achieve 2-5x compression ratios on instruction-heavy prompts.

**Expected reduction**: 50-80% system prompt tokens

### 6. Multi-Tier Context Architecture

Implement a three-tier context system:
- **Hot tier**: Last 3 rounds + current tool state (always in context)
- **Warm tier**: Summarized older rounds (included when relevant)
- **Cold tier**: Full history in external storage (retrieved on explicit need)

This mirrors database caching strategies and could reduce steady-state context by 70%+ for long sessions.

### 7. Speculative Execution with Cheaper Models

For routine operations (file reads, simple edits), use a smaller/cheaper model and only escalate to the primary model for complex reasoning. The Auto model selection mechanism already provides the infrastructure for this — it could be extended to make per-round model choices based on task complexity.

### 8. Token-Aware Streaming Batching

Batch multiple small tool calls into a single round where possible, reducing the overhead of per-round context additions (system scaffolding, round markers, etc.).

**Expected reduction**: 15-25% overhead tokens for tool-heavy sessions
