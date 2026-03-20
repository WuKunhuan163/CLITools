---
name: tool-resilience
description: How to handle buggy tools, missing tools, and when to build vs. skip tool creation. Decision framework for tool-related obstacles.
---

# Tool Resilience

## When to Use

Apply this skill when:
- A tool command fails unexpectedly (works differently than documented)
- No tool exists for the current task
- You're unsure whether to build a tool or use a simpler approach

## Scenario 1: A Tool Has a Bug

A bug is when a tool's behavior contradicts its documented purpose.

### Diagnosis

1. Confirm the bug: re-read the tool's `AGENT.md` to verify expected behavior.
2. Read the relevant source file:
   ```
   <<EXEC: cat tool/TOOLNAME/main.py >>
   <<EXEC: cat tool/TOOLNAME/logic/engine.py >>
   ```
3. Identify the broken logic (wrong condition, missing fallback, bad parsing, etc.).

### Fix

1. Edit the file to fix the bug. Keep the fix minimal and focused.
2. If the tool has tests, run them: `<<EXEC: TOOLNAME --test >>`
3. Record the fix:
   ```
   <<EXEC: TOOLNAME --skill learn "Bug: <what broke>. Fix: <what you changed>." --severity warning >>
   ```

### Anti-Patterns

- **Do NOT** work around a bug with a shell command when the fix is straightforward.
- **Do NOT** silently swallow errors. If you can't fix it, report it clearly.
- **Do NOT** refactor the entire tool. Fix the specific bug.

## Scenario 2: No Tool Exists

### Search Thoroughly First

Before concluding no tool exists:

```
<<EXEC: TOOL --search tools "what you need" >>
<<EXEC: TOOL --search interfaces "what you need" >>
<<EXEC: TOOL --search skills "what you need" >>
```

Try different phrasings. "open Chrome tab" vs "browser automation" vs "CDP navigate" may return different results.

### Check If an Existing Tool Can Be Extended

Read `AGENT.md` for the closest match. Sometimes the capability exists but isn't documented, or it can be added with a small change.

### The Build-or-Skip Decision

```
                  Will this be done more than once?
                      /                  \
                    Yes                   No
                    /                       \
           Is it complex?              → Use a shell one-liner
            /        \                   or a tmp/ script
          Yes         No
          /             \
    Build a tool    Add a simple
    (read skill:    function to an
    tool-dev-       existing tool
    workflow)
```

Key signals for building a tool:
- The task requires multi-step orchestration (boot → navigate → extract → save)
- Error handling is non-trivial (retries, fallbacks, session recovery)
- Multiple users or agents will benefit from it

Key signals for NOT building:
- A `python3 -c "..."` one-liner does the job
- The task is genuinely one-off
- The complexity of wrapping it in a tool exceeds the task itself

## Scenario 3: Tool Exists but Is Incomplete

The tool works for simple cases but your use case requires extra parameters or modes.

1. Check the tool's interface: `<<EXEC: TOOL --search interfaces "TOOLNAME" >>`
2. If the interface exposes what you need, use it directly from Python.
3. If not, consider adding the missing capability:
   - Small addition → edit the tool's `main.py` or `logic/`
   - Large feature → read `tool-development-workflow` skill first

## Decision Summary

| Situation | Action |
|-----------|--------|
| Tool fails with clear bug | Fix the source, record lesson |
| Tool fails, unclear why | Read source, debug, then fix or report |
| No tool found | Search more, then decide build vs. skip |
| Task is one-off | Shell command or tmp/ script |
| Task is recurring | Build or extend a tool |
| Tool exists but lacks feature | Add the feature, or use its interface directly |
