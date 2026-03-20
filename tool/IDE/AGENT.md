# IDE Tool — Agent Reference

## Section 0: Quick Start

```bash
IDE status           # Show detected IDEs + deployment state
IDE detect --json    # Machine-readable IDE detection
IDE deploy           # Deploy rules/hooks to detected IDEs
IDE deploy --force   # Force overwrite
IDE rules            # List deployed rules
IDE hooks            # List registered hooks
IDE rule inject      # Inject AITerminalTools rule into .cursor/rules/
```

## Architecture

The IDE tool centralizes all AI IDE integration that was previously scattered across:
- `logic/setup/IDE/cursor/` → now `tool/IDE/logic/setup/cursor/`
- `logic/setup/ide_detect.py` → now `tool/IDE/logic/detect.py`
- `logic/config/rule/manager.py` → now `tool/IDE/logic/rule.py`
- `hooks/instance/IDE/Cursor/` → now `tool/IDE/logic/instance/cursor/`

The root tool's `interface/tool.py` and `interface/config.py` delegate to the IDE tool's interface.

## Interface (Cross-Tool API)

```python
from tool.IDE.interface.main import (
    detect_ides,        # -> ['cursor', 'vscode']
    detect_cursor,      # -> bool
    deploy_cursor,      # -> {"deployed": [...], "skipped": [...]}
    list_cursor_rules,  # -> ['agent-brain', 'cli-message-styling', ...]
    list_cursor_hooks,  # -> [{"event": "sessionStart", "command": "..."}]
    generate_ai_rule,   # prints rule set
    inject_rule,        # writes .cursor/rules/AITerminalTools.mdc
)
```

## Cursor Hook Instances

Located in `logic/instance/cursor/`:

| Script | Event | Purpose |
|--------|-------|---------|
| `brain_inject.py` | sessionStart | Load brain + ecosystem into conversation |
| `brain_remind.py` | postToolUse, afterFileEdit | Anti-fatigue USERINPUT reminder |
| `userinput_flag.py` | afterShellExecution | Flag USERINPUT execution |
| `userinput_enforce.py` | stop | Force USERINPUT if not called |
| `file_search_fallback.py` | postToolUse | File search fallback |

## Rule Templates

Located in `logic/setup/cursor/rules/`:

| Rule | Purpose |
|------|---------|
| `agent-brain.mdc` | Brain read/write management |
| `cli-message-styling.mdc` | CLI output formatting |
| `core-loop.mdc` | Core agent loop guidance |
| `file-reading.mdc` | File reading commands |
| `metacognitive-mode.mdc` | Metacognitive development |
| `no-subagents.mdc` | Prohibit built-in subagents |
| `skills-to-infrastructure.mdc` | Skill conversion guidance |
| `strategy-pivot.mdc` | Strategy pivot after failures |
| `tos-compliance.mdc` | ToS compliance checks |
| `userinput-timeout.mdc` | USERINPUT long wait handling |

## Adding New IDE Support

1. Create `logic/instance/<ide>/` with hook scripts
2. Create `logic/setup/<ide>/` with template files
3. Add detection function to `logic/detect.py`
4. Add deployment function to `logic/setup/deploy.py`
5. Update `interface/main.py` with the new public API

## Dependencies

- Root TOOL depends on IDE (declared in root `tool.json`)
- `interface/tool.py` delegates `detect_ai_ides`, `deploy_cursor` to IDE
- `interface/config.py` delegates `generate_ai_rule`, `inject_rule` to IDE
