# Quality Feedback Loop: Infrastructure-Driven Agent Improvement

## Summary

Implemented automated quality feedback mechanisms in the write_file tool and conversation
manager to compensate for GLM-4-Flash's limited self-evaluation capabilities. This raised
the multi-turn web design task score from 5/14 to 12.5/14.

## Task Design

**Task #4: Team Members Page with Iterative Improvement**

Turn 1: Create a 4-card Team Members page with professional design (HTML + CSS, separate files).
Turn 2: Add dark/light mode toggle, glassmorphism, entrance animation.

Scoring: Turn 1 (0-8 points), Turn 2 (0-6 points), Total 14 points, pass threshold 10.

## Findings

### Gap #1: Placeholder Content (Model Limitation)

GLM-4-Flash defaults to "Name", "Role", "Short bio" for all cards. It also generates
generic grey/white color palettes (#333, #f4f4f4, #fff) even when explicitly told not to.

**Root cause**: The model lacks design intuition. System prompt quality guidelines are
ignored because the model doesn't reason about them before generating.

**Fix**: Moved quality evaluation from model reasoning to tool infrastructure.
`_check_write_quality()` in `conversation.py` performs automated checks:

- HTML: Detects placeholder text patterns (">Name<", "Short bio", etc.)
- HTML: Detects nonexistent placeholder image references
- HTML: Checks for Google Fonts import
- CSS: Detects all-generic color palettes
- CSS: Checks for transition properties
- CSS: Checks for padding

Quality warnings are returned as part of the write_file tool result, making them
immediately visible to the model in the same context window.

```
conversation.py:L543-L603 - _check_write_quality() static method
```

### Gap #2: Agent Forgets Earlier Warnings

When writing HTML then CSS sequentially, the agent would fix the CSS (most recent warning)
but forget the HTML warnings.

**Fix**: Track quality warnings per file in `_quality_warnings` dict. When the agent tries
to end its turn with text (no more tool calls), check for unresolved warnings and inject
a nudge:

```
"UNRESOLVED QUALITY ISSUES — fix these before finishing:
team_members.html: Contains placeholder text..."
```

This forces the agent back into a tool-calling loop to fix all issues, not just the last one.

### Gap #3: Agent Rewrites From Memory, Losing Features

In Turn 2, the agent would rewrite files from memory rather than reading existing content,
causing loss of Turn 1 features (initials circles, grid layout, etc.).

**Fix**: For `session.message_count >= 2`, inject a `[IMPORTANT]` directive:

```
[IMPORTANT] Before modifying any file, you MUST read_file first to see current content.
Files in directory: team_members.html, style.css
```

This changed behavior: the agent now reads both files before modifying.

### Gap #4: Content Hallucination

In one test, the agent's final response claimed "Added a card background with padding"
but the actual CSS file contained neither.

**Fix**: The quality warning system acts as an indirect hallucination detector — if the
model claims a change was made, the write_file quality check would have flagged it if
it wasn't present. The verification nudge (for Turn 2+) also forces a read-back.

## Results Comparison

| Metric | Baseline (no quality feedback) | With Quality Feedback Loop |
|--------|:---:|:---:|
| Turn 1: Distinct card content | 0/1 | 1/1 |
| Turn 1: Non-generic colors | 0/1 | 0.5/1 |
| Turn 1: Hover effects + transitions | 0.5/1 | 1/1 |
| Turn 1: Google Fonts | 0/1 | 1/1 |
| Turn 1: CSS avatar placeholders | 0/1 | 1/1 |
| Turn 1: Responsive layout | 1/1 | 1/1 |
| **Turn 1 Total** | **3/8** | **7.5/8** |
| Turn 2: Dark/light toggle | N/A | 1/1 |
| Turn 2: Glassmorphism | N/A | 1/1 |
| Turn 2: Entrance animation | N/A | 0.5/1 (all-at-once, not staggered) |
| Turn 2: Content preserved | N/A | 1/1 |
| Turn 2: Read before write | 0 | 1/1 |
| Turn 2: No regression | 0 | 0.5/1 |
| **Turn 2 Total** | **2/6** | **5/6** |
| **Combined** | **5/14 (FAIL)** | **12.5/14 (PASS)** |

## Architecture

The quality feedback loop follows this flow:

```
Agent writes file → write_file handler → _check_write_quality()
  ↓                                          ↓
Tool result returned                    Warnings appended to result
  ↓                                          ↓
Agent tries to finish → _get_unfixed_quality_warnings()
  ↓                                          ↓
If warnings remain → inject nudge → Agent fixes file → loop
  ↓
If clean → end turn
```

For Turn 2+:
```
User sends follow-up → _package_message() injects [IMPORTANT] read first
  ↓
Agent reads existing files → writes updated files → quality check → finish
```

## Files Changed

- `tool/LLM/logic/gui/agent_server.py` — Enhanced system prompts (zh/en) with quality
  standards, verification requirements, and forbidden behaviors
- `tool/LLM/logic/gui/conversation.py` — Added `_check_write_quality()`,
  `_quality_warnings` tracking, unresolved warning nudge, "read first" injection
  for Turn 2+, turn write/read tracking

## Remaining Gaps

1. CSS body background still uses generic #f4f4f9 (the accent colors in avatars prevent
   the "all generic" warning from firing — technically correct but aesthetically borderline)
2. Entrance animation is fade-in-all-at-once, not staggered one-by-one
3. Avatar initials sometimes don't match the person's name (e.g., "JM" for "John Doe")
4. Dark mode card styling could be better (same rgba on dark bg = barely visible)

## Lessons

1. **Weak models need infrastructure support, not just prompt engineering.** Quality
   guidelines in system prompts are ignored by GLM-4-Flash. Moving quality checking to
   the tool layer (where results are directly fed back) is far more effective.
2. **Multi-file operations need explicit ordering cues.** The agent fixes the most recent
   warning but forgets earlier ones. An "unresolved issues" safety net catches this.
3. **Turn 2+ context needs explicit "read first" reminders.** Without this, the agent
   rewrites from memory and loses features — even with "read before write" in the system prompt.
