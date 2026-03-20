# Eval Task #11: Python Email Validator with Unit Tests

**Model**: GLM-4.7-Flash (zhipu)  
**Date**: 2026-03-09  
**Difficulty**: Medium-Hard (multi-file creation + test execution + self-debug)  
**Session ID**: 3978e27e  

## Task Description

Create a Python email validator utility with three functions (`validate_email`, `validate_password`, `normalize_email`), a comprehensive test file (`test_validator.py`), and run the tests to verify they pass.

## Result: PARTIAL PASS

### What Worked

1. **Immediate file creation**: Agent created `validator.py` as its first action, followed by `test_validator.py` — perfect "act immediately" behavior.
2. **Code quality**: Both files are well-structured with proper docstrings, type hints, and comprehensive logic.
3. **Test coverage**: 32 tests across 3 test classes (7 normalize, 13 email, 12 password), covering valid/invalid/edge cases including None inputs.
4. **Test execution**: Agent ran `python3 test_validator.py` after creation — followed the full workflow.
5. **Self-debugging**: Agent detected 6 test failures and began an iterative fix cycle using `edit_file`.

### What Failed

1. **Self-debugging oscillation**: The agent repeatedly fixed `validator.py` → `test_validator.py` → `validator.py` without converging. After 6 debug iterations, it reverted a working fix, increasing failures from 1 to 5.
2. **`assertIn` misunderstanding**: The core bug was `assertIn("substring", [list])` — which checks list membership (equality), not substring matching. The agent never identified this root cause.
3. **Reasoning budget exhaustion**: 18 of 21 API calls produced 0 output tokens. Only calls #1 (7 tokens), #7 (122 tokens), and #8 (10 tokens) generated output. The reasoning model consumed its budget on context processing.
4. **Inefficient token usage**: 21 API calls total, ~700s cumulative latency, for a task that should take 3-4 calls.

### API Call Breakdown

| Call | Output Tokens | Latency | Action |
|------|--------------|---------|--------|
| 1 | 7 | 71.2s | Initial response (brief) |
| 2-6 | 0 | 35-55s | Reasoning budget exhaustion |
| 7 | 122 | 37.6s | write_file(validator.py) |
| 8 | 10 | 40.3s | write_file(test_validator.py) |
| 9-10 | 0 | 46-76s | Budget exhaustion |
| 11-21 | 0 | 3-16s | Debug attempts (all empty) |

### Intermediate State (Best)

At one point (after round 8), only 1 test failed: `test_custom_min_length` had a subtle `assertIn` vs list-equality mismatch. 31/32 tests passed. But the agent's subsequent debug attempts made it worse.

## Root Cause Analysis

### Primary: Reasoning Token Budget

The conversation context grows rapidly with tool results (file contents, test output). By round 3, the context includes:
- System prompt (~2.5K tokens)
- User message with file listing (~500 tokens)  
- Full validator.py content (~700 tokens)
- Full test_validator.py content (~2K tokens)
- Test execution output (~1K tokens)
- Multiple edit_file calls and results

For a reasoning model that uses `max_tokens` for both reasoning AND output, this leaves insufficient budget for generating actual responses.

### Secondary: Debug Loop Instability

The agent's fix strategy lacked a clear mental model:
1. Initial fix: Removed "Password " prefix from `validator.py` errors → caused new mismatches
2. Fixed test data for `StrongPass` → still had `assertIn` issue
3. Multiple attempts at the `assertIn` fix → never grasped the list vs substring distinction
4. Read validator.py → reverted error messages back to "Password must..." → broke 4 previously-passing tests

## Recommendations

1. **Context compression for reasoning models**: Summarize previous tool results instead of keeping full text. After round 3+, replace full file contents with "validator.py: 91 lines, 3 functions defined" summaries.
2. **Max context limit for multi-round**: Cap total context at ~16K tokens for reasoning models (vs 32K for non-reasoning).
3. **Self-debug guidance in system prompt**: Add "When fixing test failures, first identify whether the bug is in the test or the implementation. Fix ONE file consistently, not both."
4. **Early termination**: If 3+ consecutive calls produce 0 output tokens, stop the round and report partial completion instead of burning more calls.

## Files Created

- `validator.py` (91 lines): 3 functions with regex validation, type hints, edge case handling
- `test_validator.py` (188 lines): 32 unit tests across 3 test classes

## Comparison with Previous Tasks

| Task | Calls | Output Calls | Files | Success |
|------|-------|-------------|-------|---------|
| #9 Config Gen | 5 | 4 | 2 | PASS |
| #10 Portfolio R1 | 5 | 5 | 3 | PASS |
| #10 Portfolio R2 | 2 | 0 | 0 | FAIL |
| #11 Validator | 21 | 3 | 2 | PARTIAL |

Pattern: The model excels at initial creation but degrades rapidly in iterative/debug workflows where context grows.
