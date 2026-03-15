# GLM-4.7-Flash Evaluation Round 9: Tasks 33-35

**Date**: 2026-03-14
**Model**: zhipu-glm-4.7-flash
**Tasks**: #33-#35
**Infrastructure changes since Round 8**:
- Added `block_until_ms` protocol to EXEC tool (replaces fixed 60s timeout)
- Added `timeout_policy` parameter (ok/error on timeout)
- Fixed Auto provider streaming: error_code now propagated when all providers fail
- Fixed `base.stream()` to forward `_auto_switched` chunks
- Added `llm_response_end` with `error: true` + `error_code` on API failure
- GUI: spinner → red X icon on error responses
- Removed implicit `record_result`/`learn_from_result` calls from standard tool handlers

## Task #33: CSV Data Pipeline (5/10 difficulty)
**Score: 8/10**

**Prompt**: Read sales CSV, analyze with Python, generate markdown report with revenue per product, best seller, and monthly trend.

| Round | Action | Outcome |
|-------|--------|---------|
| 1 | `read_file(eval33_sales.csv)` | Read data structure |
| 2 | `write_file(analyze_sales.py)` | 3471 bytes, clean analysis script |
| 3 | `exec(python3 analyze_sales.py)` | "Analysis complete" |
| 4 | `read_file(eval33_report.md)` | Verified report |
| 5 | Text summary | Confirmed correctness |

**Analysis**:
- (+) Efficient 4-round workflow: read → write → execute → verify
- (+) All revenue calculations correct (verified: Widget A $9,240.75, B $8,120.00, C $4,990.00)
- (+) Clean markdown report with tables and growth rate calculation (+9.50%)
- (+) Script uses csv.DictReader, defaultdict, datetime — well-structured
- (-) Quantity bug on line 65: nested generator comprehension uses stale `month_key` variable (reports 2610 instead of 925 units for best seller)
- (-) Did not catch this bug during its own verification round

**Key Insight**: The agent excels at data pipeline tasks. Revenue math was perfect across all 18 rows. The quantity bug was a subtle Python generator scope issue — easy to miss even for experienced developers.

## Task #34: Multi-File Bug Fix (7/10 difficulty)
**Score: 9/10 (initial) → 8/10 (follow-up)**

**Setup**: 3 Python files (main.py, models.py, loader.py) with 4 planted bugs:
1. Import error: `from model` → `from models`
2. Off-by-one: `self.stock += amount - 1`
3. Discount logic: `discount_pct / 100` when called with fraction
4. Stale bug comments in code

**Initial response** (9 tool calls):

| Round | Action | Outcome |
|-------|--------|---------|
| 1 | `exec(python3 main.py)` | ImportError on loader.py |
| 2-4 | `read_file` (all 3 files) | Read all source code |
| 5 | `edit_file(loader.py)` | Fixed Bug #1: `model` → `models` |
| 6 | `edit_file(models.py)` | Fixed Bug #2: removed `- 1` |
| 7 | `edit_file(models.py)` | Fixed Bug #3: changed discount logic |
| 8 | `edit_file(main.py)` | Adjusted discount call |
| 9 | `exec(python3 main.py)` | All output correct |

**Follow-up** (format price, remove comments):

| Round | Action | Outcome |
|-------|--------|---------|
| 1 | `read_file(models.py)` | Check current state |
| 2 | `edit_file(models.py)` | Fixed `__repr__` to use `:.2f` |
| 3 | `exec(python3 main.py)` | Price shows $899.99 ✓ |
| 4 | `write_file(models.py)` | Removed bug comments from models.py |

**Analysis**:
- (+) **Excellent diagnostic flow**: ran script → read all files → fixed sequentially → verified
- (+) Found and fixed all 4 bugs correctly on first attempt
- (+) Follow-up was executed immediately (acting on corrections, as prompted)
- (-) Missed bug comment in loader.py (removed from models.py only)
- (-) Verified correct output but $899.991 rounding wasn't caught by agent itself

**Key Insight**: This is the best follow-up performance we've seen. The system prompt instruction to "execute immediately" on corrections is working. The agent went from 2/10 follow-up score in R8 Task 31 to 8/10 here.

## Task #35: CLI Tool from Spec (9/10 difficulty)
**Score: 6/10 (initial) → 6/10 (follow-up)**

**Prompt**: Create word frequency CLI with argparse, --top/--ignore-case/--min-count, plus 7 unittest cases and sample text.

**Initial response** (12 tool calls):

| Round | Action | Outcome |
|-------|--------|---------|
| 1 | `write_file(wordfreq.py)` | 2897 bytes, initial version |
| 2 | `write_file(wordfreq.py)` | Revised version (2891 bytes) |
| 3 | `write_file(test_wordfreq.py)` | 5987 bytes, 7 test cases |
| 4 | `write_file(sample.txt)` | 1029 bytes sample text |
| 5 | `exec(python3 test)` | 3/7 pass (.FF..FF) |
| 6 | `read_file`, `edit_file` | Fixed format_output |
| 7 | `exec(python3 test)` | 5/7 pass (..F..F.) |
| 8-12 | Various debug attempts | Hit round limit |

**Follow-up** (read tests, investigate):
- Read test file and wordfreq.py multiple times
- Did NOT apply fixes within allotted rounds
- Follow-up score: 6/10 (investigated but couldn't close)

**Remaining Bugs (test-side)**:
1. `test_empty_file`: `''.strip().split('\n')` → `['']` (len=1), test expects 0
2. `test_punctuation_stripping`: Test expects `hello: 2` without `--ignore-case` flag, but tool correctly outputs `Hello: 2`

**Analysis**:
- (+) The CLI tool itself is **correct and fully functional**
- (+) Good argparse usage, proper error handling, clean code structure
- (+) Demo command `--top 5 --ignore-case` produces correct output
- (+) Test infrastructure (subprocess-based CLI testing) is sound
- (-) **Same pattern as Task 31**: creates tests with unreasonable expectations
- (-) Spent 5+ rounds debugging without identifying the test as the problem
- (-) Follow-up investigation was thorough but didn't result in fixes

**Key Insight**: The "unreasonable test design" pattern persists. The agent creates tests expecting case-insensitive results without using the case-insensitive flag, and uses `''.split('\n')` expecting an empty list. System prompt could add: "When tests fail, verify the test's assumptions first."

## Infrastructure Impact

### block_until_ms Protocol
Not directly exercised by these tasks (all commands finished within default 30s). Needs a specific test with long-running processes.

### Auto Fallback
Not triggered during R9 — no 429 errors encountered. The error_code propagation fix is ready but untested in production.

### Spinner → Error Icon
Not triggered (no API errors during testing). The fix is deployed and ready.

### Removed Auto-Recording
The removal of `record_result`/`learn_from_result` from tool handlers had no observable effect on agent behavior. This is expected — these calls were invisible to the agent anyway.

## Score Summary

| Task | Difficulty | Initial | Follow-up | Key Factor |
|------|-----------|---------|-----------|-----------|
| #33: CSV Pipeline | 5/10 | 8/10 | — | Correct analysis, minor quantity bug |
| #34: Bug Fix Chain | 7/10 | 9/10 | 8/10 | All 4 bugs fixed, good follow-up |
| #35: CLI Tool | 9/10 | 6/10 | 6/10 | Working tool, unreasonable tests |

**Average**: 7.4/10 (up from 7.0 in R8)

## Cumulative Improvements Since R6

| Metric | R6 (Tasks 27-29) | R8 (Tasks 30-32) | R9 (Tasks 33-35) |
|--------|-----------------|-----------------|-----------------|
| Average Score | 5.3/10 | 7.0/10 | 7.4/10 |
| Follow-up Performance | 2/10 | 2/10 | 8/10 |
| Rounds Wasted on Re-reads | 4+ per task | 1-2 per task | 0-1 per task |
| Test Quality | — | 4/10 | 5/10 (tests are reasonable but edge cases wrong) |

## Remaining Known Issues

1. **Test design quality**: The agent creates tests with wrong assumptions (case sensitivity, empty string splitting). Recommendation: Add to system prompt "When a test fails, first verify that the test's expected values match the tool's documented behavior."

2. **Quantity calculation bug in Task 33**: Stale variable scope in generator comprehension. The agent didn't catch this in its verification round. Could be addressed by: "After generating data with a script, spot-check at least one specific number against manual calculation."

3. **block_until_ms untested**: Need a specific task requiring long-running background processes.

4. **Auto fallback untested in streaming**: The error_code propagation fix hasn't been validated in production. Next round should include a stress test or simulated 429.
