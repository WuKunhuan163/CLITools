---
name: task-execution-order
description: Default task execution ordering when given multiple tasks. Use when receiving a batch of tasks from the user, or when deciding which pending task to work on next.
---

# Task Execution Order

## Why This Exists

Users often submit multiple tasks in a single message. Without a default ordering strategy, agents may cherry-pick easy tasks or work on the wrong priority, wasting user time.

## Default Rule

**Fix tasks in the order they appear**, unless:
1. The user explicitly specifies priority
2. You discover a dependency between tasks (e.g., task B requires task A's output)
3. A task is blocked and you can make progress on a later one

## Workflow

### When receiving multiple tasks:
1. **Record all tasks** in the brain immediately (`BRAIN add "..."` for each)
2. **Start with the first task** in the order given
3. **Complete each task** before moving to the next
4. **If blocked**, note the blocker in the brain and move to the next unblocked task
5. **After all tasks**, execute USERINPUT to report completion

### When the user says "按照顺序做" or "fix in order":
This is a standing instruction. For all future task batches in this session, apply the default sequential order unless overridden.

### Dependencies override order:
If task 5 is a prerequisite for tasks 1-4, do task 5 first and note why in your response.

## When This Skill Triggers

This skill is relevant when:
- User submits 3+ tasks in one message
- User says "按照顺序" / "in order" / "one by one"
- Brain has multiple pending tasks and you need to decide which to work on
- You're about to skip a task in favor of another

## Anti-Patterns

**Bad**: Doing easy tasks first to show quick progress.
Why: The user ordered them intentionally. Respect their ordering.

**Bad**: Working on multiple tasks simultaneously without completing any.
Why: Partial progress on 5 tasks is worse than complete progress on 3.

**Bad**: Skipping a task without noting why in the brain.
Why: The user will wonder why it was skipped. Always document.

## Context-Free Discovery

A context-free agent can discover this skill if they:
1. Search for "task order" or "execution order" in skills
2. Have it injected via the sessionStart hook (as part of agent behaviors)
3. See it referenced in the brain tasks

To ensure discovery, this skill should be referenced in `logic/agent/guidelines/base/conventions.py` as a default agent behavior.
