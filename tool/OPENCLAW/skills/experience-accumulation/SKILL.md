---
name: experience-accumulation
description: How agents record, refine, and promote experience into permanent project knowledge. Covers per-tool lesson recording, severity classification, and the promotion pipeline from lessons to skills to tools.
---

# Experience Accumulation

## The Learning Loop

```
Agent encounters surprise
  → Record lesson (immediate)
    → Lessons cluster around a theme (3+ related)
      → Promote to AGENT.md rule
        → Rule grows (>10 lines)
          → Extract into a Skill
            → Skill has automatable parts
              → Create a Tool or pre-commit hook
```

This loop is the project's institutional memory. Without it, every
session starts from zero.

## Per-Tool Lesson Recording

Every tool records its own lessons. This keeps context local:

```bash
# Tool-specific lesson (preferred)
TOOL_NAME --skill learn "Description" --severity warning

# General lesson (cross-cutting patterns only)
SKILLS learn "Description" --tool TOOL_NAME --severity info
```

### When to record

Record when ANY of these are true:
- You needed more than one attempt to get something right
- The correct behavior surprised you
- You discovered an undocumented constraint or quirk
- A workaround was needed for a library/API bug

### When NOT to record

- Obvious errors (typo, missing import)
- Things already documented in README or for_agent
- Session-specific state ("I was on the wrong branch")

## Severity Classification

| Severity | Trigger | Example |
|----------|---------|---------|
| **info** | Convention, saves 2-5 min | "Use `_git_bin()` helper, not bare `/usr/bin/git`" |
| **warning** | Caused a bug or wasted >10 min | "APFS case-insensitivity makes bin/GIT shadow system git" |
| **critical** | Data loss, security hole, infinite loop | "Bare `git` call from bin/GIT causes zombie processes" |

## Quality Standards

### Good lesson

> "On macOS APFS (case-insensitive), bin/GIT/GIT shadows /usr/bin/git
> when invoked as lowercase 'git'. Fix: guard in bootstrap script
> using os.execvp to pass through to real git binary."

Why: Specific platform, specific mechanism, specific fix.

### Bad lesson

> "git doesn't work on mac"

Why: No specifics, no mechanism, no fix.

## Promotion Pipeline

### Stage 1: Rule in AGENT.md

When 3+ lessons share a theme:

```markdown
<!-- tool/GIT/AGENT.md -->
## Path Shadowing
Never call `git` (lowercase) directly in subprocess calls.
Always use `get_system_git()` from the GIT interface.
```

### Stage 2: Skill

When a rule grows beyond 10 lines or applies across tools:

Create `skills/core/<skill-name>/SKILL.md` with the full guide.

### Stage 3: Automation

When a skill describes purely mechanical steps:

- Pre-commit hook (if it validates code)
- Audit command (if it checks structure)
- Tool (if it's a self-contained workflow)

## Reviewing Lessons

Periodically check accumulated lessons:

```bash
# Recent lessons across all tools
SKILLS lessons --last 20

# Lessons for a specific tool
SKILLS lessons --tool GIT

# Analyze patterns
SKILLS analyze --days 30
```

Look for:
- Repeated themes → promote to rule/skill
- Outdated lessons → remove or update
- Critical lessons without corresponding rules → act on them

## Anti-Patterns

- **Recording after fixing but not capturing the fix**: Include BOTH
  what went wrong AND how to avoid it.
- **Only recording critical issues**: Info-level lessons prevent
  warning-level bugs. Capture early.
- **Never promoting**: If you have 5+ lessons on the same topic and
  no rule or skill, you're wasting the knowledge.
- **Recording to SKILLS instead of the tool**: Use per-tool
  `TOOL_NAME --skill learn` for tool-specific knowledge.
