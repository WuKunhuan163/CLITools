---
name: agent-onboarding
description: Bootstrap protocol for context-free agents starting from zero. Covers initial orientation, self-iteration loop, session handoff, and knowledge accumulation.
---

# Agent Onboarding

## When to Use

Use this skill when:
- You are a new agent with no prior context about this project
- You are resuming work after a session break
- You are unsure what to do first

## Bootstrap Protocol

### Step 1: Check for Continuity

```bash
# Does the brain have state from a previous session?
cat runtime/brain/context.md
cat runtime/brain/tasks.md

# Read the reflection protocol (system improvement guide)
cat for_agent_reflection.md
```

If `context.md` has content, a previous agent left you a handoff. Read it carefully — it tells you:
- What was being worked on
- What's done and what's pending
- What to resume

### Step 2: Orient Yourself

```bash
# Search for anything relevant to your task
TOOL --search all "<task keywords>"

# List all available skills
SKILLS list

# Check installed tools
TOOL status
```

**The search command is your most powerful tool.** Run it before writing any code, before creating any file, before making any decision. It finds:
- Existing tools that might already do what you need
- Skills with guidance on how to approach the task
- Lessons learned from past mistakes

### Step 3: Load Relevant Skills

```bash
SKILLS show <name>
```

Common starting skills:
- `tool-development-workflow` — creating new tools
- `code-quality-review` — auditing code
- `avoid-duplicate-implementations` — before creating something new
- `naming-conventions` — project naming rules
- `standard-command-development` — three-layer architecture

### Step 4: Work

Execute your task. Follow these principles:
- **Search before create**: Always check if something exists before building it
- **Fix at source**: Don't work around bugs, fix them directly
- **Self-test**: After implementing code, always run it. Write `tmp/` test scripts for non-trivial changes
- **Iterate**: Don't stop at first implementation. Test, find issues, fix, test again
- **Record discoveries**: Use `SKILLS learn` to capture non-obvious findings
- **Log activity**: After each task, run `BRAIN log "User asked X. Did Y. Result: Z." --files "path1,path2"` (include `--files` for created artifacts)
- **Persist progress**: Run `BRAIN snapshot "summary"` after milestones
- **Digest periodically**: Run `BRAIN digest` between tasks — consolidate 3+ related lessons into skills

### Step 5: Handoff

Before your session ends (or when calling USERINPUT):
1. Run `BRAIN snapshot "what I did this session"` — auto-generates context.md
2. Mark completed tasks: `BRAIN done <id>`
3. Record any lessons via `SKILLS learn`

## Self-Iteration Loop

An agent session flows through named phases. Always know which phase you're in:

```
BOOTSTRAP   → Read brain/context.md, for_agent_reflection.md, run TOOL --search all
EXECUTE     → Implement the user's task (code, fix, investigate)
VERIFY      → Self-test: run the code, check edge cases, write tmp/ tests
CAPTURE     → BRAIN log "activity", SKILLS learn, BRAIN done <id>, update docs
FEEDBACK    → USERINPUT (present results, get direction)
  ↓ new task → back to EXECUTE
  ↓ no tasks or ecosystem request → META ACTIVITY
HANDOFF     → BRAIN snapshot "summary" (before session end)
```

**Meta activities** (ecosystem-level, between tasks or when requested):
- **Document** — enhance README.md / for_agent.md for agent discoverability
- **Curate** — audit, merge, refine skills; leave breadcrumbs for future agents
- **Audit** — run `TOOL --audit code`, `TOOL --lang audit`
- **Refactor** — clean up code, reorganize structure
- **Harden** — raise quality of working-but-imperfect infrastructure (fix latent bugs, generalize, align with conventions)
- **Improve** — fix ecosystem gaps from for_agent_reflection.md

**Phase awareness matters.** When executing a user task, focus on their goal. When doing meta activities, focus on ecosystem quality and future agent experience. When capturing, focus on what future agents need to know. Don't mix phases — finish one before starting another.

This loop is how agents accumulate institutional knowledge. Each iteration makes the next agent (or your next session) more effective.

## Key BRAIN Commands

```bash
BRAIN list              # See all tasks
BRAIN add "task"        # Add new task
BRAIN done <id>         # Mark task complete
BRAIN log "entry" [--files f1,f2]  # Record activity + artifacts
BRAIN digest            # Check lessons for distillation opportunities
BRAIN status            # Dashboard: tasks, lessons, context age, skills
BRAIN snapshot "msg"    # Auto-save context.md with state summary
BRAIN recall "keyword"  # Search lessons + context for past knowledge
BRAIN reflect           # Self-check protocol + system gaps (proactive self-improvement)
```

## Key Directories

| Path | Purpose |
|------|---------|
| `runtime/brain/context.md` | Current session state (handoff document) |
| `runtime/brain/tasks.md` | Task list with priorities |
| `runtime/experience/lessons.jsonl` | Accumulated lessons |
| `skills/core/` | Core skills (read with `SKILLS show`) |
| `tool/<NAME>/for_agent.md` | Tool-specific agent documentation |
| `for_agent.md` (root) | Full architecture guide |

## Anti-Patterns

- Starting to code without running `TOOL --search all`
- Creating a new tool/function without checking if one exists
- Ignoring `brain/context.md` when it has content
- Ending a session without updating the brain
- Making changes without recording non-obvious findings as lessons
- Not reading `for_agent_reflection.md` at session start (misses known gaps and improvement protocol)
- Not self-testing code after writing it
