# Cursor IDE Hooks — Agent Reference

## What Are Cursor Hooks?

External scripts that Cursor IDE calls at specific lifecycle events during agent execution. They communicate via JSON over stdin/stdout.

## Available Events (most useful for agent self-management)

| Event | When | Best For |
|-------|------|----------|
| `sessionStart` | New conversation begins | Load brain, set environment |
| `postToolUse` | After any tool call succeeds | Inject periodic reminders |
| `afterShellExecution` | After shell command completes | Track specific commands (e.g., USERINPUT) |
| `stop` | Agent loop ends | Enforce USERINPUT, auto-continue |
| `preCompact` | Before context summarization | Alert agent to save state |

## Brain Integration

Hooks read from and interact with `runtime/brain/`:
- `sessionStart` → injects `tasks.md` + `context.md` as additional_context
- `postToolUse` → every 10 calls, reminds agent to check brain and plan USERINPUT
- `afterShellExecution` (USERINPUT matcher) → flags that USERINPUT was called
- `stop` → if USERINPUT wasn't called, auto-submits followup forcing it

## Instance Location

All implementations: `hooks/instance/AI-IDE/Cursor/`
Cursor config: `.cursor/hooks.json`

## Gotchas

- `postToolUse.additional_context` is injected into the conversation — the agent sees it as system context after the tool result.
- `stop.followup_message` auto-submits as a **user message**, starting a new agent turn. Subject to `loop_limit` (default 5).
- Scripts must read JSON from stdin and write JSON to stdout. Exit code 0 = success.
- `matcher` is a regex matched against the relevant field (command text, tool name, etc.).
