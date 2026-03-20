---
name: naming-conventions
description: Naming conventions for the AITerminalTools project covering tools, commands, files, and variables.
---

# Naming Conventions

## Tool Names

- **UPPERCASE**: Tool names are always uppercase (e.g. `GOOGLE`, `GMAIL`, `OPENCLAW`).
- **Dot notation** for sub-tools: `PARENT.CHILD` (e.g. `GOOGLE.GD`, `GOOGLE.GDS`, `iCloud.iCloudPD`).
- Tool directories: `tool/<NAME>/` matching the tool name exactly.

## CLI Subcommands

- **kebab-case** (hyphens): All subcommands use hyphens, never underscores.
  - Correct: `GOOGLE open-tab`, `GOOGLE auth-status`, `OPENCLAW cli-status`
  - Wrong: `GOOGLE open_tab`, `GOOGLE auth_status`, `OPENCLAW cli_status`
- Single-word commands are lowercase: `boot`, `tabs`, `login`, `logout`, `status`.
- Multi-word commands use hyphens: `open-tab`, `auth-status`, `setup-llm`.

## File Naming

- **snake_case** for Python files: `session_manager.py`, `chat_html.py`.
- **UPPERCASE** for special files: `SKILL.md`, `BOOTSTRAP.md`, `README.md`.
- **kebab-case** for skill directories: `naming-conventions/`, `error-recovery-patterns/`.
- Config files: `tool.json`, `config.json` (snake_case JSON files).

## Python Code

- **snake_case** for functions, methods, variables: `get_api_key()`, `is_chrome_cdp_available()`.
- **PascalCase** for classes: `OpenClawCLI`, `SessionManager`, `NvidiaGLM47Provider`.
- **UPPER_SNAKE_CASE** for constants: `CDP_PORT`, `MAX_OUTPUT_LENGTH`, `BLOCKED_COMMANDS`.
- Private members prefixed with `_`: `_provider`, `_context`, `_load_policies()`.

## Agent Protocol Tokens

- Command execution: `<<EXEC: command_here >>`
- Experience: `<<EXPERIENCE: lesson >>`
- Termination: `<<OPENCLAW_TASK_COMPLETE>>`
- Special commands: `--openclaw-*` prefix (hyphenated).

## Color Constants

Use shared color constants from `logic.config.get_color()`:
- `BOLD`, `RESET`, `DIM`, `RED`, `GREEN`, `BLUE`, `YELLOW`, `CYAN`.
- Status pattern: `{BOLD}{COLOR}Label{RESET} details.`

## Common Mistakes

| Wrong | Correct | Rule |
|-------|---------|------|
| `GOOGLE open_tab` | `GOOGLE open-tab` | CLI subcommands use hyphens |
| `openclaw` | `OPENCLAW` | Tool names are UPPERCASE |
| `sessionManager` | `session_manager` | Python uses snake_case |
| `SessionManager.py` | `session_manager.py` | Files use snake_case |
| `open`, `osascript` | `GOOGLE open-tab` | Use project tools, not OS commands |
