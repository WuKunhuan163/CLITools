---
name: memory-recall
description: Institutional memory and lesson recall for agent workflows. Use BEFORE starting any non-trivial task to avoid repeating past mistakes. Covers lesson search, context-aware recall, post-task capture, and memory-to-skill promotion.
---

# Memory Recall

## Why This Exists

Agent sessions are stateless. Past mistakes, architectural decisions, API quirks, and timing gotchas live in `runtime/experience/lessons.jsonl` — but only if the agent actually reads them. Without recall, the same errors recur every session.

This is not about grep. This is about building a habit: **check what the project already knows before acting.**

## Pre-Task Recall (Mandatory)

Before starting any task that touches tools, APIs, or multi-step workflows:

```bash
# Broad: what has the project learned about this area?
SKILLS lessons --tool WHATSAPP

# Narrow: specific pattern you're about to use
SKILLS lessons --last 30 | grep -i "rate limit"
```

### What to search for

The goal is to find *non-obvious* knowledge. Don't search for things the docs already cover.

**Good searches** (things that catch real mistakes):
- Before CDMCP work: `SKILLS lessons --tool GOOGLE.CDMCP` → discovers "Chrome session must be closed before re-booting"
- Before bulk messaging: `SKILLS lessons --last 50 | grep -i "bulk\|batch\|rate"` → discovers "WhatsApp enforces 20msg/min"
- Before GUI work: `SKILLS lessons --last 50 | grep -i "tkinter\|gui\|blueprint"` → discovers "Use get_safe_python_for_gui()"

**Bad searches** (waste of time):
- `SKILLS lessons` with no filter → too noisy
- Searching for "how to use ls" → agent already knows this
- Searching after you've already made the mistake → too late

### When to skip

- Single-line edits (typo fix, comment update)
- Reading/exploring code without changing anything
- Tasks you've done successfully in this same session

## During-Task Capture

When you encounter something non-obvious — meaning you needed more than one attempt, or the correct behavior surprised you:

```bash
SKILLS learn "CDMCP boot_tool_session requires closing stale sessions first, otherwise duplicate tabs appear" \
  --tool GOOGLE.CDMCP --severity warning --context "OPENCLAW boot_yuanbao was opening 2 tabs"
```

### Lesson quality rubric

| Quality | Example | Why |
|---------|---------|-----|
| **Good** | "Google ListAccounts returns 200 even when auth cookie is expired — check response body for actual auth state" | Specific, actionable, names the function and the gotcha |
| **Good** | "Tkinter init.tcl error when launching from managed Python — use logic.gui.engine.get_safe_python_for_gui() instead" | Points to the solution, not just the problem |
| **Bad** | "Chrome doesn't work sometimes" | Vague, not actionable |
| **Bad** | "Be careful with rate limits" | No specifics about which API, what limit, or what to do |
| **Bad** | "Fixed the bug" | Doesn't say what the bug was or how to avoid it |

### Severity guide

- **info**: Convention or best practice that saves time. "Always use `_` prefix for private test fixtures."
- **warning**: Pattern that caused a bug or wasted >10 minutes. "Cross-process in-memory state doesn't persist — use file persistence."
- **critical**: Data loss, security hole, or breaks other tools. "rm -rf on a symlink with trailing slash destroys the target, not the link."

## Post-Task Promotion

Lessons accumulate. When 3+ lessons cluster around the same theme, they should be promoted:

```
3+ lessons on same theme
  → Consolidate into a rule in AGENT.md or .cursor/rules/
    → If rule grows beyond 10 lines
      → Extract into a SKILL
        → If behavior can be automated
          → Create a pre-commit hook
```

This is the Error→Lesson→Rule→Skill→Hook pipeline from the `openclaw` skill.

### Example promotion chain

```
Lesson: "CDMCP ensure_chrome() must be called before any tab operation"
Lesson: "CDMCP boot_tool_session closes stale sessions automatically"
Lesson: "CDMCP session.require_tab() handles both create and navigate"
  ↓
Rule added to tool/GOOGLE.CDMCP/AGENT.md:
  "Always use boot_tool_session() + require_tab(). Never manage Chrome lifecycle manually."
  ↓
Skill created: skills/core/mcp-development/SKILL.md
  (full guide for CDMCP tool development)
```

## Within OPENCLAW Remote Agent

The remote agent uses special commands instead of `SKILLS`:

| Project Agent | OPENCLAW Remote Agent |
|--------------|----------------------|
| `SKILLS lessons --tool X` | `<<EXEC: --openclaw-memory-search "X" >>` |
| `SKILLS learn "lesson" --tool X` | `<<EXPERIENCE: lesson >>` |
| Read lessons.jsonl directly | `<<EXEC: --openclaw-status >>` |

The OPENCLAW system prompt mandates memory search as the first execution step. This is structural enforcement, not optional guidance.

## Anti-Patterns

- **Searching after failing**: Memory recall prevents failures. Searching after you've already broken something only helps next time.
- **Recording obvious things**: "Python uses indentation" is not a lesson. Only record things that surprised you.
- **Never searching at all**: The most common failure mode. If you skip recall, you WILL repeat a documented mistake within 3 sessions.
- **Recording without context**: `--context` matters. Future-you needs to know WHEN this lesson applies.
