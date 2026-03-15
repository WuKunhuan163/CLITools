# runtime/brain/

Persistent task and context memory for AI agents. Read at session start, updated during work, saved before session end.

## Files

| File | Purpose | Updated by |
|------|---------|------------|
| `tasks.md` | Active task list with status tracking | Agent (manually) |
| `context.md` | Current working context and resumption state | Agent (manually) |

## How It Works

1. **Session start**: Cursor hook (`sessionStart`) reads brain files and injects content into the agent's context via `additional_context`.
2. **During work**: Cursor hook (`postToolUse`) periodically reminds the agent to check and update brain files.
3. **Session end**: Cursor hook (`stop`) enforces USERINPUT and reminds the agent to save brain state.

## Relationship to experience/

| Aspect | `brain/` | `experience/` |
|--------|----------|---------------|
| Scope | Current session tasks | Cross-session institutional memory |
| Lifespan | Active during work, cleared when done | Permanent, accumulative |
| Content | Task list, working context | Lessons, SOUL, MEMORY, daily logs |
| Updated | Every significant step | When learning something new |

## Integration

Brain files are read by Cursor IDE hooks at `hooks/instance/AI-IDE/Cursor/`. The `.cursor/rules/agent-brain.mdc` rule encourages agents to read and update brain files.
