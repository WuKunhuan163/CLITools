# GLM-4.7-Flash Evaluation Round 3: Agent Capabilities

**Date**: 2026-03-13
**Model**: zhipu-glm-4.7-flash (via SDK + urllib)
**Tasks**: #14-#18 (Round 3 — harder than Round 2)

## Task Results

### Task 14: Multi-File Bug Fix with Verification (3/5 difficulty)
**Score: 5/10**
- (+) Agent provided explanatory text with tool calls (improved from Round 2)
- (+) Correctly searched for `stage.error_brief =` patterns across the project
- (+) Identified matches in logic/test/manager.py, logic/setup/engine.py, etc.
- (-) Drifted from target file (auto_save_remote.py) to unrelated files
- (-) Never synthesized conclusion that the bugs were already fixed
- (-) Produced empty response when forced to text-only mode
- (-) Follow-up with context failed

### Task 15: Cross-Tool Integration Research (3/5 difficulty)
**Score: 8/10**
- (+) Read the file and produced a well-structured analysis
- (+) Correctly identified `_git_bin()` → `get_system_git()` dependency
- (+) Correctly identified `get_interface("GIT")` → `get_git_engine()` chain
- (+) Explained two fallback scenarios (ImportError → hardcoded path, None → skip)
- (-) Summary slightly truncated at the end

### Task 16: Create a Working Python Script (4/5 difficulty)
**Score: 9/10**
- (+) Read JSON schema first (smart approach)
- (+) Created complete, working Python script (2573 bytes)
- (+) Script executed successfully with emoji-formatted output
- (+) Attempted edge case verification
- (-) Edge case test ran same command (didn't rename file to test missing case)

### Task 17: Debug a Failing Command (4/5 difficulty)
**Score: 4/10** (best attempt)
- (+) Correctly ran `python3 bin/BRAIN xxx` and identified the output
- (+) Read the source code
- (-) Got stuck in read loop — never transitioned to using edit_file
- (-) Produced content=None with tool calls despite system prompt
- (-) Read limit (3000 chars) prevented seeing the else branch (fixed to 12000)

### Task 18: Full Workflow — Audit, Fix, Test, Document (5/5 difficulty)
**Score: 3/10** (partial — API timeouts)
- (+) Read __init__.py and composition engine
- (+) Correctly identified file structure (guidelines, base, layers)
- (-) API timed out before agent could continue
- (-) Intermittent stream hangs prevented completion

## Aggregate Performance

| Metric | Round 2 (Tasks 9-13) | Round 3 (Tasks 14-18) |
|---|---|---|
| Average Score | 7.0/10 | 5.8/10 |
| Text with Tool Calls | Rarely | ~60% of turns |
| Successful Completions | 5/5 | 3/5 (2 incomplete) |
| Edit File Usage | Works but fragile | Unable to transition from read |
| Error Recovery | Medium | Low (loops instead of synthesizing) |
| Summary Production | Occasional | 2/5 tasks had good summaries |

## Root Causes of Issues Found & Fixed

### Critical Bugs Fixed
1. **`stream_options` not supported by SDK** — Zhipu SDK rejects `stream_options` parameter. The agent could never start because every LLM call failed. Fixed by removing it from SDK path.
2. **Streaming text not emitted to frontend** — Text chunks accumulated in `full_text` but were never emitted as events. Frontend showed no agent text. Fixed by emitting during stream.
3. **Thread exceptions silently swallowed** — Daemon threads die silently. Added `_safe_run` wrapper with traceback printing.
4. **read_file limit too small** (3000 chars) — Agent couldn't see full files. Critical for edit_file workflow. Increased to 12000.

### Behavioral Improvements
5. **Silent tool call nudge** — After 3 consecutive rounds of tool calls with no text, inject a nudge requesting explanation.
6. **Summary nudge misfiring** — `_should_nudge` incorrectly triggered write_file nudge on analysis/summary responses. Added summary detection.
7. **Turn-limit approach nudge too early** — Fired at round 1 for turn_limit=2. Now requires turn_limit > 3.
8. **Turn-limit losing context** — Final text response was emitted but not saved to session context. Fixed.
9. **SDK client timeout** — Added `httpx.Timeout(120s, connect=10s)` to prevent indefinite hangs.
10. **SDK stream chunk timeout** — 90s timeout between chunks via queue-based wrapper.

### System Prompt Improvements
11. **Stricter response guidelines** — "Every response MUST contain text" (was merely "should").
12. **Search limit** — "Maximum 2 search attempts" to prevent infinite search loops.
13. **Summary requirement** — "A task without a summary is considered incomplete."

## Model Capability Matrix (Updated)

| Capability | GLM-4-Flash | GLM-4.7-Flash (Round 2) | GLM-4.7-Flash (Round 3) |
|---|---|---|---|
| File reading | YES | YES | YES |
| Code analysis | NO | PARTIAL | GOOD (Task 15: 8/10) |
| Script creation | NO | YES | EXCELLENT (Task 16: 9/10) |
| edit_file usage | NO | Fragile | REGRESSION (stuck in read loop) |
| Text with tool calls | NEVER | RARELY | ~60% (improved by system prompt) |
| Multi-step research | NO | PARTIAL | GOOD (cross-tool tracing) |
| Follow-up response | N/A | N/A | POOR (context too long) |
| Error debugging | N/A | N/A | MODERATE (identifies but can't fix) |

## Recommendations

1. **API Reliability**: Zhipu API intermittently hangs. The SDK timeout (120s) and chunk timeout (90s) help but don't fully prevent it. Consider implementing automatic retry with exponential backoff at the ConversationManager level.

2. **Edit Workflow**: The agent struggles to transition from reading to editing. Consider adding a dedicated "edit_mode" nudge that triggers after 3 read operations of the same file, explicitly formatting the edit_file call.

3. **Context Length**: Performance degrades significantly when context exceeds ~20 messages. The compression system exists but may not trigger frequently enough.

4. **Model Fallback**: When the primary model (GLM-4.7-Flash) fails, implement automatic fallback to the urllib streaming path instead of retrying the same SDK call.
