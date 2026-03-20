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

Hooks read from and interact with `runtime/_/eco/brain/`:
- `sessionStart` → injects `tasks.md` + `context.md` as additional_context
- `postToolUse` → every 10 calls, reminds agent to check brain and plan USERINPUT
- `afterShellExecution` (USERINPUT matcher) → flags that USERINPUT was called
- `stop` → if USERINPUT wasn't called, auto-submits followup forcing it

## Instance Location

All implementations: `hooks/instance/IDE/Cursor/`
Cursor config: `.cursor/hooks.json`

## Gotchas

- `postToolUse.additional_context` is injected into the conversation — the agent sees it as system context after the tool result.
- `stop.followup_message` auto-submits as a **user message**, starting a new agent turn. Subject to `loop_limit` (default 5).
- Scripts must read JSON from stdin and write JSON to stdout. Exit code 0 = success.
- `matcher` is a regex matched against the relevant field (command text, tool name, etc.).

## Known Cursor IDE Quirks

**Shell `block_until_ms` too short for USERINPUT:**
Cursor's Shell tool defaults to 30s timeout. USERINPUT can take 5+ minutes (user is typing). Always set `block_until_ms: 120000` when calling USERINPUT. If backgrounded, `sleep 30` and read the terminal file for the response. See rule `userinput-timeout.mdc`.

**Search tools fail with spaces in paths:**
Glob/Grep silently fail when paths contain spaces (e.g., `tmp/Screenshot 2026-03-13 at 19.03.44.png`). The `file_search_fallback.py` hook auto-triggers when search returns empty, suggesting `ls -la | grep` as fallback. See rule `file-reading.mdc`.

**Context summarization drops injected context:**
When Cursor summarizes long conversations, `sessionStart` injected context may be lost. The `brain_remind.py` postToolUse hook re-injects periodic reminders to compensate. The `brain_inject.py` CLI primer is intentionally concise to survive summarization.

**Agent may stop without USERINPUT:**
The `userinput_enforce.py` stop hook catches this and injects a `followup_message` forcing the agent to continue and call USERINPUT. Subject to `loop_limit: 2` to prevent infinite loops.
