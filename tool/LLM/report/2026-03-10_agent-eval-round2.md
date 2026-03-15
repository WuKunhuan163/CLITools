# Agent Evaluation Round 2: GLM-4.7-Flash with Ecosystem Enhancements

**Date**: 2026-03-10
**Model**: zhipu-glm-4.7-flash
**Turn Limit**: 10 rounds (new configurable feature)
**Infrastructure**: Compressed ecosystem feed, contextual suggestions, loop detection, turn-limit mechanism

## Summary

| Task | Type | Score | Pass? |
|------|------|-------|-------|
| #9 Ecosystem Discovery | Search + Read + Synthesize | 8/10 | Yes (with follow-up) |
| #10 Read + Fix Bug | Read + Edit + Verify | 10/10 | Yes (perfect) |
| #11 Create Tests | Read + Write + Debug | 5/10 | Partial |
| #12 Audit + Fix + Lesson | Explore + Edit + Record | 5/10 | Partial |
| #13 Full Tool Creation | Multi-file Create | 7/10 | Partial |

**Overall: 35/50 (70%)**

## Comparison with Round 1 (GLM-4-Flash)

| Capability | GLM-4-Flash (Round 1) | GLM-4.7-Flash (Round 2) |
|---|---|---|
| File creation | YES (with quality nudges) | YES (higher quality) |
| Read + Edit (Python) | NO (0% — infinite loops) | YES (10/10 — perfect) |
| Multi-turn context | Limited (regression on Turn 2) | Good (follow-up works) |
| Ecosystem search | N/A (not tested) | Yes (TOOL --search used) |
| experience() recording | N/A | Yes (lesson recorded) |
| Multi-file creation | N/A | Yes (5/5 files created) |
| Test writing accuracy | N/A | Partial (correct structure, wrong assertions) |

**Key finding**: GLM-4.7-Flash is a major upgrade from GLM-4-Flash. The read+edit pattern that completely failed before (0%) now works perfectly (10/10).

## Infrastructure Improvements Validated

### 1. Turn-Limit Mechanism (NEW)
- Configurable rounds (1, 2, 3, 5, 10, 20, 50, unlimited)
- HTML GUI selector added
- Correctly stops agent after N rounds of text-only responses
- Grace period: allows tool calls beyond limit before hard ceiling at limit+3

### 2. Loop Detection (NEW)
- Detects repetitive tool call patterns (4+ calls with <= 2 unique signatures)
- Injects synthesis nudge: "Stop reading and SYNTHESIZE"
- In Task #9 v3, this improved output from zero synthesis to a 450-char structured summary

### 3. Contextual Suggestions (NEW)
- `build_contextual_suggestions()` provides per-turn relevant tools/skills/lessons
- Verified in Task #9: suggestions included "GIT" tool for a git-related query
- Reduces cold-start time for agent exploration

### 4. Compressed Ecosystem Feed
- Core feed: 568 tokens (68% reduction from 1789)
- With skill catalog + lessons: 1238 tokens total
- Agent still successfully navigated ecosystem (TOOL --search tools-deep)

## Detailed Findings

### Task #9: Ecosystem Discovery
**Prompt**: Find all git-related tools, describe their purpose, search for "commit" handling.

Turn 1 (6/10):
- Used `TOOL --search tools-deep 'git'` correctly (ecosystem integration works!)
- Read GIT README.md and extracted features
- Got stuck in read loop before producing summary
- Loop detection nudge helped produce structured output
- Did not complete "commit search" part within turn limit

Turn 2 (10/10):
- Excellent follow-up: synthesized commit handling from context
- Covered 4 aspects: CLI command, history maintenance, UI feedback, tool integration

### Task #10: Read + Fix Python Bug
**Prompt**: Fix the off-by-one bug in merge_sort.

Perfect execution:
1. Read file → identified `mid = len(arr) // 2 + 1` bug
2. Used edit_file → changed to `mid = len(arr) // 2`
3. Ran tests → all 5 passed
4. Explained bug cause and fix clearly

This validates that GLM-4.7-Flash can handle read+edit tasks that GLM-4-Flash
completely failed at.

### Task #11: Create Tests for Real Code
**Prompt**: Read cleanup.py, create test file, run tests.

Partial success:
- Read the function correctly
- Created 7595-byte test file (comprehensive structure)
- Fixed import error (added sys.path — good debugging)
- Made 6 edit_file iterations to debug
- **Failed**: Test assertions wrong (expected 2 files, got 5)
  - Misunderstood: cleanup deletes batch_size files, not all above limit

### Task #12: Audit + Fix + Record Lesson
**Prompt**: Audit EXEC tool, find issue, fix it, record lesson.

Mixed result:
- Found the EXEC tool and read its code
- Identified what it thought was a bug (`sys.exit` without `()`)
- Actually introduced a regression: changed `sys.exit(124)` to `sys.exit(1)(124)`
- The edit_file tool matched the wrong occurrence
- **Positive**: Used experience() tool and recorded a "critical" lesson
- Lesson content was meaningful: "sys.exit() must include exit code parameter"

### Task #13: Full Tool Creation (TIMER)
**Prompt**: Create a TIMER tool with proper architecture.

Good architecture, missing persistence:
- Studied BILIBILI tool as reference (correct approach)
- Created all 5 files: main.py, logic/core.py, tool.json, README.md, for_agent.md
- Clean Python code with docstrings and proper class structure
- **Critical gap**: No file-based state persistence between invocations
- Tool uses in-memory singleton that resets with each process

## Remaining Gaps

1. **Multi-part task completion**: Agent struggles to complete all sub-tasks in one turn.
   The first sub-task consumes most rounds, leaving insufficient for subsequent parts.

2. **edit_file precision**: Agent sometimes matches wrong occurrences when multiple
   similar patterns exist (Task #12 regression).

3. **Complex assertion logic**: Agent can write tests but sometimes gets edge-case
   math wrong (Task #11 batch_size calculation).

4. **State persistence awareness**: Agent doesn't consider that CLI tools run as
   separate processes (Task #13 in-memory state).

5. **Tool call efficiency**: Agent makes excessive read_file calls for the same file,
   even after loop detection nudges.

## Recommendations

1. **Add edit_file context validation**: Before applying, show the edit context and
   confirm it's the right occurrence.
2. **Add a "wrap-up" nudge**: When approaching turn limit, inject a nudge to complete
   remaining sub-tasks before time runs out.
3. **System prompt enhancement**: Add guidance about CLI tool state persistence patterns.
4. **Consider model-specific tool filtering**: GLM-4.7-Flash can handle edit_file but
   may need additional guidance about multi-occurrence editing.
