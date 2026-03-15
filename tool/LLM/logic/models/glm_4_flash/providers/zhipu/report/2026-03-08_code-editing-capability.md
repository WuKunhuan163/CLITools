# Code Editing Capability Assessment: GLM-4-Flash

## Summary

Tested GLM-4-Flash on a Python bug-fix task (bookmark manager search function).
The model can identify bugs correctly but cannot apply fixes — it fails at both
`write_file` (writes fragments, introduces syntax errors) and `edit_file` (wrong
parameters, infinite loops). This is a model capability ceiling.

## Task Design

**Task #5: Python Bug Fix**

A bookmark manager with an exact-match search bug (`bm["title"] == query`).
The agent must change it to case-insensitive partial matching.

## Findings

### Bug Diagnosis: PASS

In every test run, GLM-4-Flash correctly identified the bug:
- Read the file
- Identified `bm["title"] == query` as the problem
- Proposed the correct fix: `query.lower() in bm["title"].lower()`

### Bug Fix Application: FAIL (all approaches)

#### Approach 1: write_file (complete file rewrite)

The model consistently wrote only the `cmd_search` function (~377 bytes) instead
of the complete file (~2134 bytes). This triggered the fragment detection system.

When forced to write the complete file, it introduced Python f-string syntax errors:
```python
print(f"  {bm["title"]} — {bm["url"]}")   # BROKEN: nested double quotes
```
The original used single quotes: `{bm['title']}`. GLM-4-Flash cannot maintain correct
quoting in f-strings when rewriting code.

#### Approach 2: edit_file (targeted replacement)

The model used edit_file with:
- `old_text: "db = load_db()"` (wrong line — this appears in 4 functions)
- `new_text: "db = load_db()"` (identical to old_text!)

This was repeated 14 times in a loop, never correcting the parameters.

### Infrastructure Improvements Made

Despite the model limitation, several infrastructure improvements were implemented:

1. **Fragment detection** in `_handle_write_file`: Rejects writes where new content
   is <40% of existing file size, preventing data loss.

2. **Python syntax checking** in `_check_write_quality`: Compiles Python files and
   returns specific error messages with fix suggestions.

3. **edit_file tool**: New tool for targeted text replacement with:
   - Uniqueness check (rejects ambiguous matches)
   - Pre-write syntax validation for .py files
   - Diff preview in tool results

4. **Duplicate write loop breaker**: After 3 consecutive identical writes, injects
   a "STUCK IN LOOP" message suggesting a different approach.

5. **Smarter nudge**: Detects whether the agent already read the file and adjusts
   nudge text accordingly.

6. **Empty retry fix**: Adds synthetic assistant acknowledgment between consecutive
   user messages to maintain proper alternation for the model.

## Model Capability Matrix

| Capability | GLM-4-Flash | Notes |
|------------|:-----------:|-------|
| Bug identification | YES | Consistently correct |
| Web file creation | YES* | With quality feedback |
| Web file modification | YES* | With read-first injection |
| Python file creation | NO | f-string syntax errors |
| Python file modification | NO | Fragment writes or wrong edit_file params |
| Tool parameter accuracy | LOW | Wrong parameters, identical old/new text |
| Error recovery | LOW | Loops instead of trying different approach |

\* Requires infrastructure support (quality warnings, nudges)

## Recommendations

1. **Python editing tasks require a more capable model** (GPT-4, Claude, etc.)
2. **The edit_file tool is correctly designed** but needs a model that can:
   - Extract the exact text to replace from read_file output
   - Generate different replacement text
   - Provide sufficient context for unique matching
3. **Consider model-specific tool filtering**: Don't provide edit_file to models that
   can't use it correctly (add to ContextPipeline.prepare_tools)
4. **Web design tasks are viable with GLM-4-Flash** when paired with the quality
   feedback loop infrastructure

## Files Changed

- `tool/LLM/logic/gui/conversation.py`:
  - Added `edit_file` tool definition and `_handle_edit_file` handler
  - Added fragment detection in `_handle_write_file`
  - Added Python syntax checking in `_check_write_quality`
  - Added duplicate write loop breaker (3-strike escalation)
  - Extended nudge threshold from round 2 to round 6
  - Smarter nudge text (checks if file already read)
  - Empty retry: adds synthetic assistant ack for proper alternation
- `tool/LLM/logic/gui/agent_server.py`:
  - Updated system prompts (zh/en) to document edit_file tool
  - Updated file modification rules to recommend edit_file
