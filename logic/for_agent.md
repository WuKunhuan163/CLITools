# logic/ — Technical Reference

## Path Resolution (CRITICAL)

Every tool entry point must call `setup_paths(__file__)` from `logic.resolve` before any other imports. This ensures:
- Project root is at `sys.path[0]`
- Tool-local `logic/` does not shadow root `logic/`
- Cross-tool imports via `tool.<NAME>.logic` work correctly

```python
from logic.resolve import setup_paths
setup_paths(__file__)
```

## Package Dependencies

```
tool/blueprint/ -> config/, gui/, turing/, utils/, lang/, git/
gui/ -> config/, turing/, accessibility/, asset/, translation/
test/ -> config/, turing/, utils/, tool/
turing/ -> config/, utils/
lang/ -> config/, translation/
cdmcp_loader.py -> chrome/, config/
```

## Key Gotchas

1. **`ToolBase` location**: Canonical at `logic.tool.blueprint.base`. Always import from `logic.tool.blueprint.base`.

2. **Config JSON files**: `config/colors.json` and `config/settings.json` are static defaults, not runtime data. Runtime config goes in `data/config.json` at the project root.

3. **`cdmcp_loader.py`**: Must be at the top level of `logic/` because it's imported as `logic.cdmcp_loader` by all Chrome-based tools. Do not move.

4. **Translation files**: Root `translation/` holds framework-wide translations. Per-tool translations go in `tool/<NAME>/logic/translation/`. GUI-specific translations go in `gui/translation/`.

5. **Turing Machine `print()` prohibition**: Never use `print()` inside a `TuringStage` action — it breaks erasable line tracking. Use `stage.refresh()` for live updates.

6. **Test CPU monitoring**: `TestManager` enforces CPU limits during tests. Default: 80% threshold, 30s timeout. Override per-test with `EXPECTED_CPU_LIMIT` and `EXPECTED_TIMEOUT` at file top.

## Dependency Discovery (MANDATORY)

Before building any new tool feature, read the `for_agent.md` of ALL dependencies:

- **Chrome/CDP tools**: Read `logic/chrome/for_agent.md` AND `tool/GOOGLE.CDMCP/for_agent.md`. Use `ensure_chrome()` and `boot_tool_session()` instead of manual Chrome management.
- **GUI tools**: Read `logic/gui/for_agent.md`. Check `logic/gui/tkinter/blueprint/` for reusable components before building custom UIs.
- **MCP tools**: Read `logic/mcp/for_agent.md`. Check `logic/cdmcp_loader.py` for loading CDMCP modules.

If a tool declares dependencies in `tool.json`, read each dependency's `for_agent.md` before writing code.

## Sub-Package Index

Every sub-package has `README.md` and `for_agent.md`. For details, read the sub-package docs directly:

```
logic/tool/for_agent.md       # ToolBase, MCPToolBase, hooks, lifecycle
logic/gui/for_agent.md        # GUI blueprints, widgets, style
logic/config/for_agent.md     # Global config, colors, rules
logic/turing/for_agent.md     # Progress display, stages, workers
logic/test/for_agent.md       # Test runner, CPU monitoring
logic/git/for_agent.md        # Git operations, persistence
logic/lang/for_agent.md       # i18n, audit
logic/utils/for_agent.md      # Display, logging, system
logic/chrome/for_agent.md     # Chrome session, CDP
logic/mcp/for_agent.md        # MCP infrastructure
logic/accessibility/for_agent.md  # Keyboard, paste detection
```
