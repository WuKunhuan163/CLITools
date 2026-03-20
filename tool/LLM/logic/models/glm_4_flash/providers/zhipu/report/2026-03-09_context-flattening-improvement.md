# Context Flattening Improvement: Preserving Read File Content

**Date**: 2026-03-09

## Problem

GLM-4-Flash hits the "empty response bug" after reading multiple files. After
context flattening (which compresses prior tool_call history into summaries),
the model lost the file content and either:
- Destroyed original content when rewriting (wrote generic placeholders)
- Failed to match old_text for edit_file
- Ran unrelated commands (ls, reading README)

## Root Cause

The `ZhipuContextPipeline._flatten_tool_history()` truncated tool results
(read file content) to 100 chars. After flattening, the model had no access
to the original file content it had read.

## Fix

1. **Preserve read_file results**: Tool outputs from `read_file` calls are
   now preserved up to 3000 chars in the flattened summary, wrapped as
   `[Content of /path/file.ext]`.

2. **Task reminder injection**: When retrying after empty responses, the
   original task prompt (from `session.initial_prompt`) is re-injected
   into the context.

3. **Increased max_retries**: From 2 to 3 for more recovery chances.

4. **Directive in retry**: Added "Do NOT run ls. Proceed directly with
   modifications." to prevent the agent from wasting rounds on exploration.

## Infrastructure Changes

- `logic/agent/state.py`: Added `initial_prompt` field to `AgentSession`
- `logic/agent/loop.py`: Inject task reminder in empty-response retry
- `logic/agent/context.py`: Re-inject original task + runtime header on follow-up turns
- `zhipu_glm4/pipeline/context.py`: Preserve read_file content in flattened summaries

## Remaining Limitations

GLM-4-Flash still cannot reliably:
- **edit_file**: Gets old_text wrong (confirmed in Task #5 and Task #6)
- **write_file with full file**: After reading, rewrites destroy original content
  because the model cannot faithfully reproduce large HTML/CSS files

These are model capability ceilings, not infrastructure issues.

## Recommendation

For GLM-4-Flash, avoid tasks that require "read + modify existing files".
Instead, design tasks as "create from scratch with specifications".
For read-modify tasks, use a more capable model (GLM-4.7, GPT-4, etc.).
