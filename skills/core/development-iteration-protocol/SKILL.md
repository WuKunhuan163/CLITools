---
name: development-iteration-protocol
description: Escalating test requirements when fixes are reported as failing. Use when a user reports the same issue for the 2nd+ time, or when implementing fixes that previously failed.
---

# Development Iteration Protocol

## Why This Exists

When a user reports the same bug or missing feature twice, it means the first fix was insufficient. Each repeated report should escalate the agent's verification effort to prevent wasting user time on the same issue.

## Escalation Levels

| User Reports | Test Requirement | Before Moving On |
|---|---|---|
| 1st time | Implement fix. Self-test if complex; otherwise OK to proceed. | May continue to other tasks |
| 2nd time | Check existing fix for gaps. **Must self-test** and show passing result. | Must demonstrate fix works |
| 3rd+ time | Deep investigation. Test with **multiple failure cases**. Show evidence. | Must show evidence AND explain why previous fix failed |

## Core Workflow

### On 1st Report
1. Implement the fix
2. If the task is complex or has other pending tasks, decide whether to self-test
3. If simple, proceed. If risky, test.

### On 2nd Report
1. **Do NOT just re-implement** — first investigate why the previous fix failed
2. Read the previous implementation
3. Identify the gap (wrong file? wrong logic? not persisted? race condition?)
4. Fix the gap
5. **Test and show the result** before continuing

### On 3rd+ Report
1. Investigate thoroughly — check logs, test manually, verify end-to-end
2. Consider additional failure cases the user hasn't mentioned
3. Test ALL identified cases
4. Show evidence of each test passing
5. Document what was wrong and why it kept failing

## Anti-Patterns

**Bad**: Immediately re-writing the same code without investigating why it failed.
Why: Same logic = same bug. Always check the PREVIOUS implementation first.

**Bad**: Marking a task "done" without testing after 2nd report.
Why: The user already told you the first fix didn't work. Trust is lost; evidence rebuilds it.

**Bad**: Testing only the happy path.
Why: The user hit an edge case. Test the specific scenario they described.

## Integration with Brain Tasks

When a fix fails repeatedly, the brain task should track the failure count:
```
BRAIN add "Fix X (2nd attempt — must test before marking done)"
```

When marking done on 2nd+ attempt, include test evidence:
```
BRAIN done 42 "Fixed: [evidence]. Previous failure was due to [root cause]."
```

## See Also

- `error-recovery-patterns` — Retry and fallback strategies
- `exploratory-testing` — How to investigate unknowns with tmp/ scripts
- `openclaw` — Self-improvement loop (lesson capture)
