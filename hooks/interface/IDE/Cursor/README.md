# Cursor IDE Hooks — Interface Blueprint

Defines all available lifecycle hook events in Cursor IDE's agent system. Instances at `hooks/instance/IDE/Cursor/` implement specific behaviors for these events.

## Configuration

Cursor hooks are configured in `.cursor/hooks.json` (project-level) or `~/.cursor/hooks.json` (user-level). Scripts run from the project root for project hooks.

## All Lifecycle Events

### Agent Hooks

| Event | Phase | Can Block? | Key Output Fields |
|-------|-------|------------|-------------------|
| `sessionStart` | Session begins | No (fire-and-forget) | `env`, `additional_context` |
| `sessionEnd` | Session ends | No (fire-and-forget) | (none) |
| `beforeSubmitPrompt` | After user hits send, before backend | Yes (`continue: false`) | `continue`, `user_message` |
| `preToolUse` | Before any tool executes | Yes (`permission: deny`) | `permission`, `agent_message`, `updated_input` |
| `postToolUse` | After successful tool execution | No | `additional_context`, `updated_mcp_tool_output` |
| `postToolUseFailure` | After tool fails/times out | No | (none) |
| `beforeReadFile` | Before agent reads a file | Yes (`permission: deny`) | `permission`, `user_message` |
| `afterFileEdit` | After agent edits a file | No | (none) |
| `beforeShellExecution` | Before shell command runs | Yes (`permission: deny/ask`) | `permission`, `user_message`, `agent_message` |
| `afterShellExecution` | After shell command completes | No | (none) |
| `beforeMCPExecution` | Before MCP tool runs | Yes (`permission: deny/ask`) | `permission`, `user_message`, `agent_message` |
| `afterMCPExecution` | After MCP tool completes | No | (none) |
| `afterAgentResponse` | After assistant message | No | (none) |
| `afterAgentThought` | After thinking block | No | (none) |
| `preCompact` | Before context summarization | No (observational) | `user_message` |
| `stop` | Agent loop ends | Can auto-continue | `followup_message` |
| `subagentStart` | Before subagent spawns | Yes (`permission: deny`) | `permission`, `user_message` |
| `subagentStop` | After subagent completes | Can auto-continue | `followup_message` |

### Tab Hooks

| Event | Phase | Can Block? | Key Output Fields |
|-------|-------|------------|-------------------|
| `beforeTabFileRead` | Before Tab reads file | Yes (`permission: deny`) | `permission` |
| `afterTabFileEdit` | After Tab edits file | No | (none) |

## Common Input Schema (all hooks)

```json
{
  "conversation_id": "string",
  "generation_id": "string",
  "model": "string",
  "hook_event_name": "string",
  "cursor_version": "string",
  "workspace_roots": ["<path>"],
  "user_email": "string | null",
  "transcript_path": "string | null"
}
```

## Per-Script Config Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `command` | string | required | Script path or command |
| `type` | `"command"` \| `"prompt"` | `"command"` | Execution type |
| `timeout` | number | platform default | Timeout in seconds |
| `loop_limit` | number \| null | 5 | Max auto follow-ups for stop/subagentStop |
| `failClosed` | boolean | false | Block action on hook failure |
| `matcher` | string | - | Regex filter for when hook runs |

## Matcher Targets

| Hook | Matcher matches against |
|------|------------------------|
| `beforeShellExecution` / `afterShellExecution` | Full command string |
| `preToolUse` / `postToolUse` / `postToolUseFailure` | Tool type (`Shell`, `Read`, `Write`, `Task`, `MCP: <name>`) |
| `subagentStart` / `subagentStop` | Subagent type (`generalPurpose`, `explore`, `shell`) |
| `afterFileEdit` / `beforeReadFile` | Tool type (`TabWrite`, `Write`, `TabRead`, `Read`) |

## Exit Code Behavior (command hooks)

- `0` — Success, use JSON output
- `2` — Block action (equivalent to `permission: "deny"`)
- Other — Hook failed, action proceeds (unless `failClosed: true`)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CURSOR_PROJECT_DIR` | Workspace root |
| `CURSOR_VERSION` | Cursor version |
| `CURSOR_USER_EMAIL` | Authenticated user email |
| `CURSOR_TRANSCRIPT_PATH` | Path to conversation transcript |

## Key Output Fields by Event

### sessionStart
```json
{
  "env": {"KEY": "value"},
  "additional_context": "Context injected into conversation"
}
```

### postToolUse
```json
{
  "additional_context": "Extra context after tool result",
  "updated_mcp_tool_output": {"modified": "output"}
}
```

### stop
```json
{
  "followup_message": "Auto-submitted as next user message"
}
```

### preToolUse / beforeShellExecution / beforeMCPExecution
```json
{
  "permission": "allow | deny | ask",
  "user_message": "Shown to user when denied",
  "agent_message": "Fed back to agent when denied",
  "updated_input": {"modified": "tool input"}
}
```
