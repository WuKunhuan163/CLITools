# logic/ — Technical Reference

## Import Convention (CRITICAL)

**Tools MUST import from `interface.*`, not directly from `logic.*`.** The `interface/` directory re-exports stable symbols. Direct `logic.*` imports are only for code inside `logic/` itself.

```python
# CORRECT (in tools):
from interface.status import fmt_status, fmt_warning
from interface.utils import retry, preflight

# WRONG (in tools):
from logic.turing.status import fmt_status  # DO NOT
from logic._.utils import retry               # DO NOT
```

## Path Resolution (CRITICAL)

Every tool entry point must call `setup_paths(__file__)` from `logic.resolve` before any other imports. This ensures:
- Project root is at `sys.path[0]`
- Tool-local `logic/` does not shadow root `logic/`
- Cross-tool imports via `tool.<NAME>.logic` work correctly

```python
from logic.resolve import setup_paths
setup_paths(__file__)
```

## Directory Organization

Root `logic/` is split into two tiers:

- **`logic/_/`** — Ecosystem command modules that back symmetric CLI flags (`TOOL --<name>`):
  `agent`, `assistant`, `audit`, `config`, `dev`, `eco`, `hooks`, `lang`, `search`, `setup`, `test`, `workspace`

- **`logic/`** (top-level) — Infrastructure modules shared by tools and command modules:
  `utils`, `turing`, `gui`, `tool`, `git`, `data`, `command`, `mcp`, `llm`, `brain`, `chrome`, `serve`, `translation`, `tutorial`, `accessibility`, `asset`

Internal cross-references use `logic._.<module>` for command modules and `logic.<module>` for infrastructure.

## Package Dependencies

```
tool/blueprint/ -> _/config/, gui/, turing/, utils/, _/lang/, git/
gui/ -> _/config/, turing/, accessibility/, asset/, translation/
_/test/ -> _/config/, turing/, utils/, tool/
turing/ -> _/config/, utils/
_/lang/ -> _/config/, translation/
cdmcp_loader.py -> chrome/, _/config/
```

## Key Gotchas

1. **`ToolBase` location**: Canonical at `logic.tool.blueprint.base`. Always import from `logic.tool.blueprint.base`.

2. **Config JSON files**: `config/colors.json` and `config/settings.json` are static defaults, not runtime data. Runtime config goes in `data/config.json` at the project root.

3. **`cdmcp_loader.py`**: Must be at the top level of `logic/` because it's imported as `logic.cdmcp_loader` by all Chrome-based tools. Do not move.

4. **Translation files**: Root `translation/` holds framework-wide translations. Per-tool translations go in `tool/<NAME>/logic/_/translation/`. GUI-specific translations go in `gui/translation/`.

5. **Turing Machine `print()` prohibition**: Never use `print()` inside a `TuringStage` action — it breaks erasable line tracking. Use `stage.refresh()` for live updates.

6. **Test CPU monitoring**: `TestManager` enforces CPU limits during tests. Default: 80% threshold, 30s timeout. Override per-test with `EXPECTED_CPU_LIMIT` and `EXPECTED_TIMEOUT` at file top.

## Dependency Discovery (MANDATORY)

Before building any new tool feature, read the `AGENT.md` of ALL dependencies:

- **Chrome/CDP tools**: Read `logic/chrome/AGENT.md` AND `tool/GOOGLE.CDMCP/AGENT.md`. Use `ensure_chrome()` and `boot_tool_session()` instead of manual Chrome management.
- **GUI tools**: Read `logic/_/gui/AGENT.md`. Check `logic/_/gui/tkinter/blueprint/` for reusable components before building custom UIs.
- **MCP tools**: Read `logic/mcp/AGENT.md`. Check `logic/cdmcp_loader.py` for loading CDMCP modules.

If a tool declares dependencies in `tool.json`, read each dependency's `AGENT.md` before writing code.

## Sub-Package Index

Every sub-package has `README.md` and `AGENT.md`. For details, read the sub-package docs directly:

```
interface/AGENT.md           # FACADE LAYER — import from here in tools

# Infrastructure (logic/)
logic/tool/AGENT.md          # ToolBase, MCPToolBase, hooks, lifecycle
logic/_/gui/AGENT.md           # GUI blueprints, widgets, style
logic/turing/AGENT.md        # Progress display, stages, workers
logic/git/AGENT.md           # Git operations, .gitignore auto-gen, persistence
logic/_/utils/AGENT.md         # Display, logging, system
logic/chrome/AGENT.md        # Chrome session, CDP
logic/mcp/AGENT.md           # MCP infrastructure
logic/accessibility/AGENT.md # Keyboard, paste detection

# Ecosystem commands (logic/_/)
logic/_/config/AGENT.md      # Global config, colors, rules
logic/_/test/AGENT.md        # Test runner, CPU monitoring
logic/_/lang/AGENT.md        # i18n, audit
logic/_/audit/AGENT.md       # Code quality auditing
logic/_/agent/AGENT.md       # Agent loop, tools, context
logic/_/assistant/AGENT.md   # GUI assistant, std chat
logic/_/dev/AGENT.md         # Developer commands
logic/_/hooks/AGENT.md       # Hook engine, lifecycle hooks
```
