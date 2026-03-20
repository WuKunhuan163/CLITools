# Cursor IDE Internals Analysis

**Date**: 2026-03-17  
**Purpose**: Document Cursor IDE's internal file structure, tools, and mechanisms found in `.cursor/` directories.

## Directory Layout

### User-level: `~/.cursor/`

| Path | Purpose |
|------|---------|
| `argv.json` | CLI arguments for Cursor (crash reporter, hardware acceleration) |
| `ide_state.json` | Recently viewed files across all projects |
| `extensions/` | VS Code extensions (Python, Edge DevTools, PDF viewer, etc.) |
| `extensions/extensions.json` | Extension manifest with install timestamps and metadata |
| `skills/` | User-created agent skills (40 skills in this installation) |
| `skills-cursor/` | Cursor's built-in agent skills (6 skills, managed via manifest) |
| `plugins/local/` | Plugin cache (currently empty) |
| `ai-tracking/` | AI code tracking SQLite database (~60MB) |
| `browser-logs/` | Browser automation snapshots (from MCP browser tool) |
| `chrome-cdp-profile/` | Chrome DevTools Protocol profile (full Chrome data dir) |
| `projects/` | Per-project agent data (transcripts, tools, terminals, MCPs) |

### Project-level: `~/.cursor/projects/<project-slug>/`

| Path | Purpose |
|------|---------|
| `agent-tools/` | Cached tool outputs (research papers, large search results) |
| `agent-transcripts/` | Conversation histories as JSONL files |
| `terminals/` | Terminal state files (pid, cwd, last_command, exit_code, output) |
| `mcps/` | MCP server tool descriptors (JSON schemas for browser tools) |
| `rules/` | Project-specific rules (currently empty for this project) |
| `tmp/` | Temporary files for agent operations |

### Workspace-level: `.cursor/`

| Path | Purpose |
|------|---------|
| `hooks.json` | Lifecycle hooks (sessionStart, postToolUse, afterFileEdit, stop) |
| `rules/` | Always-applied rules (.mdc files) for agent behavior |

## Built-in Skills (skills-cursor/)

Cursor ships 6 managed skills:

| Skill | Description |
|-------|-------------|
| `create-rule` | Create persistent AI behavior rules (.mdc files) |
| `create-skill` | Author new agent skills (SKILL.md format) |
| `create-subagent` | Create custom subagents (`.cursor/agents/*.md`) |
| `migrate-to-skills` | Convert existing patterns to skill format |
| `shell` | Direct shell command execution via `/shell` |
| `update-cursor-settings` | Modify VS Code/Cursor settings.json |

### Subagent Architecture (from create-subagent skill)

Cursor supports custom subagents defined as `.md` files with YAML frontmatter:

```yaml
---
name: code-reviewer
description: Expert code review specialist. Use proactively after code changes.
---
System prompt here...
```

Locations: `.cursor/agents/` (project) or `~/.cursor/agents/` (user). Project-level takes priority.

## Hooks System (.cursor/hooks.json)

Five lifecycle events are supported:

| Hook | Trigger | Current Usage |
|------|---------|---------------|
| `sessionStart` | Chat session begins | `brain_inject.py` — inject brain context |
| `postToolUse` | After any tool call | `brain_remind.py` + `file_search_fallback.py` |
| `afterFileEdit` | After file modification | `brain_remind.py` |
| `afterShellExecution` | After shell command (with matcher) | `userinput_flag.py` (matches "USERINPUT") |
| `stop` | Agent attempts to stop | `userinput_enforce.py` (loop_limit: 2) |

Key insight: `stop` hook with `loop_limit` can force the agent to retry up to 2 times before actually stopping — used to enforce the USERINPUT feedback loop.

## Rules System (.cursor/rules/*.mdc)

12 active rules controlling agent behavior:

| Rule | Purpose |
|------|---------|
| `agent-brain.mdc` | Brain system integration (context, tasks, lessons) |
| `cli-message-styling.mdc` | Terminal output formatting (bold status, dim details) |
| `core-loop.mdc` | BRAIN reflect + USERINPUT mandatory loop |
| `file-reading.mdc` | Use `cat` not `strings` for file reading |
| `file-search-fallback.mdc` | Fallback search strategies |
| `metacognitive-mode.mdc` | Self-improvement mode activation keywords |
| `no-subagents.mdc` | Prohibit Cursor's built-in Task/subagent tool |
| `skills-to-infrastructure.mdc` | Conversion tracking (skill → automated function) |
| `strategy-pivot.mdc` | Pivot after 3+ failed attempts |
| `tos-compliance.mdc` | ToS checks before web automation |
| `userinput-invocation.mdc` | USERINPUT CLI tool invocation rules |
| `userinput-timeout.mdc` | USERINPUT timeout handling |

## MCP (Model Context Protocol) Tools

One MCP server enabled: `cursor-ide-browser` with 33 browser automation tools:

**Navigation**: `browser_navigate`, `browser_navigate_back`, `browser_navigate_forward`, `browser_reload`  
**Interaction**: `browser_click`, `browser_type`, `browser_fill`, `browser_fill_form`, `browser_drag`, `browser_hover`, `browser_press_key`, `browser_select_option`  
**Inspection**: `browser_snapshot`, `browser_take_screenshot`, `browser_get_attribute`, `browser_get_bounding_box`, `browser_get_input_value`, `browser_is_checked`, `browser_is_enabled`, `browser_is_visible`  
**State**: `browser_tabs`, `browser_lock`, `browser_unlock`, `browser_handle_dialog`, `browser_console_messages`, `browser_network_requests`  
**Performance**: `browser_profile_start`, `browser_profile_stop`  
**Other**: `browser_scroll`, `browser_search`, `browser_highlight`, `browser_resize`, `browser_wait_for`

Lock/unlock workflow is critical: `browser_navigate → browser_lock → interactions → browser_unlock`.

## AI Tracking Database

`ai-tracking/ai-code-tracking.db` is a 60MB SQLite database tracking AI-assisted code changes. This provides Cursor with history of what code was AI-generated vs human-written.

## Extensions

| Extension | Purpose |
|-----------|---------|
| `anysphere.cursorpyright` | Cursor's Python type checker |
| `ms-python.python` | Python language support |
| `ms-python.debugpy` | Python debugging |
| `ms-edgedevtools.vscode-edge-devtools` | Browser DevTools integration |
| `tomoki1207.pdf` | PDF viewer |
| `yzane.markdown-pdf` | Markdown → PDF export |

## Key Findings for Our System

1. **Subagent system**: Cursor's subagent mechanism (`.cursor/agents/`) uses simple Markdown files with YAML frontmatter. Our system already has a more sophisticated equivalent via the OPENCLAW pipeline, but we could adopt the simple `.md` format for lightweight agent definitions.

2. **Hooks are powerful**: The `stop` hook with `loop_limit` is a pattern we use to enforce USERINPUT calls. Consider extending hooks with more lifecycle events (e.g., `beforeToolCall`, `afterModeSwitch`).

3. **MCP browser tools**: 33 tools for browser automation, well-structured with JSON schemas. Our CDMCP system parallels this but our tools are integrated differently.

4. **AI code tracking**: The 60MB SQLite DB suggests Cursor tracks significant metadata about AI-generated code. We don't have an equivalent — could be useful for quality auditing.

5. **Skills manifest**: `skills-cursor/.cursor-managed-skills-manifest.json` separates built-in from user-managed skills. Clean separation model.

6. **Terminal files**: Per-terminal text files in `terminals/` with metadata headers (pid, cwd, last_command, exit_code) followed by raw output. This is how Cursor provides terminal context to the AI.

## Recommendations

- Consider implementing a code tracking database similar to `ai-code-tracking.db` for our assistant sessions
- The subagent `.md` format could be adopted for lightweight tool/agent definitions
- The hooks `loop_limit` pattern is valuable — ensure our hooks system supports it
- Browser MCP tools could be integrated more tightly with our CDMCP system
