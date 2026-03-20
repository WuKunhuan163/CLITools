# logic/ — Technical Reference for Agents

## Import Convention (CRITICAL)

**Tools MUST import from `interface.*`, not directly from `logic.*`.** The `interface/` directory re-exports stable symbols. Direct `logic.*` imports are only for code inside `logic/` itself.

```python
# CORRECT (in tools):
from interface.status import fmt_status, fmt_warning
from interface.utils import retry, preflight
from interface.tool import ToolBase

# WRONG (in tools):
from logic._.utils import retry               # DO NOT
from logic._.base.blueprint.base import ToolBase  # DO NOT (use interface.tool)
```

## Path Resolution (CRITICAL)

Every tool entry point must call `setup_paths(__file__)` before other imports:

```python
from interface.resolve import setup_paths
setup_paths(__file__)
```

## Post-Migration Architecture

All shared code now lives under `logic/_/`. The legacy top-level directories (`logic/base/`, `logic/brain/`, `logic/git/`, `logic/tool/`) have been removed. Their contents were consolidated into `logic/_/` and all imports updated to use `logic._.*`.

### Command Map Rule

Each `logic/_/<name>/` directory with a `cli.py` file **automatically** maps to a `---<name>` eco command. This is the stateless router's core mechanism — the directory structure IS the routing state.

Files in each command directory:
- `cli.py` — The command endpoint (subclass of `EcoCommand`/`CliEndpoint`)
- `argparse.json` — Declarative schema for `---help` generation and audit
- `__init__.py` — Package marker

### Three-Tier CLI Convention

```
---<name>    Eco commands (logic/_/<name>/cli.py) — shared across all tools
--<name>     Tool commands (argparse in tool main.py) — tool-specific
-<name>      Decorators (-no-warning, -tool-quiet) — behavioral modifiers
```

### Key Locations

| What | Where | Accessed via |
|------|-------|-------------|
| ToolBase | `logic/_/base/blueprint/base.py` | `interface.tool.ToolBase` |
| MCPToolBase | `logic/_/base/blueprint/mcp.py` | `interface.tool.MCPToolBase` |
| CliEndpoint | `logic/_/base/cli.py` | `interface.tool.CliEndpoint` |
| Brain tasks | `logic/_/agent/brain_tasks.py` | `TOOL ---brain` or `bin/BRAIN` |
| Brain sessions | `logic/_/brain/instance/` | `logic._.brain.instance.BrainSessionManager` |
| Git ops | `logic/_/git/` | `interface.git` |
| GUI blueprints | `logic/_/gui/tkinter/blueprint/` | `interface.gui` |
| Test runner | `logic/_/test/manager.py` | `TOOL ---test` |
| Help tree | `logic/_/help/cli.py` | `TOOL ---help` |

### Brain as Eco Infrastructure

BRAIN is NOT a standalone tool — it is ecosystem infrastructure accessible via:
- `TOOL ---brain <command>` (eco command)
- `bin/BRAIN <command>` (backward-compatible shorthand, delegates to eco)

Brain data lives in `data/_/runtime/_/eco/brain/` (shared across all tools). Each tool gets its brain experience stored in `data/_/brain/` at the tool level.

### __/ Co-Located Data Convention

Directories named `__/` within a command endpoint hold **co-located data** specific to that endpoint: test fixtures, schema files, templates. Constraints:
- Only the parent `cli.py` may import from `__/`
- `__/` directories are auditable: `TOOL ---audit` checks referential integrity
- No business logic in `__/` — only data, fixtures, and templates

### Tool-Internal CLI Decomposition

Tools with complex CLIs can decompose their `logic/` directory using the same pattern as eco commands. Each subcommand gets its own `cli.py` and `argparse.json`:

```
tool/USERINPUT/logic/
├── cli.py               ← Root entry point (no-args default)
├── argparse.json         ← Root schema
├── queue/cli.py          ← --queue subcommand
├── prompt/cli.py         ← --system-prompt subcommand
├── config/cli.py         ← --config subcommand
└── main.py routes to the appropriate cli.py
```

`main.py` becomes a thin router: create ToolBase, detect mode, dispatch.

### Parallel Hierarchy Pattern

Command directories (`logic/_/<name>/cli.py`) have parallel data directories (`data/_/<name>/`). This mapping is auditable:

| Command | Data | Description |
|---------|------|-------------|
| `logic/_/brain/cli.py` | `data/_/runtime/_/eco/brain/` | Brain state |
| `logic/_/audit/cli.py` | `data/_/audit/` | Audit cache |
| `logic/_/assistant/` | `data/_/runtime/sessions/` | Session data |
| `logic/_/test/cli.py` | `data/_/test/` | Test results |

Root-level data directories follow the same pattern:
- `report/` → user reports (mapped to `---dev` or future `---report`)
- `skills/` → skill guides (mapped to `---skills`)
- `migrate/` → migration data (mapped to `---migrate`)

### argparse.json Schema

```json
{
  "$schema": "argparse/v1",
  "name": "command-name",
  "description": "What this command does",
  "subcommands": {
    "sub": {
      "description": "What this subcommand does",
      "args": [
        {"name": "positional_arg", "type": "positional", "help": "Description"},
        {"name": "--flag", "help": "Description"}
      ]
    }
  }
}
```

## Key Gotchas

1. **Config JSON files**: `config/colors.json` and `config/settings.json` are static defaults. Runtime config goes in `data/config.json`.

2. **`cdmcp_loader.py`**: Must stay at `logic/` top level — imported as `logic.cdmcp_loader` by Chrome-based tools.

3. **Translation files**: Root `logic/_/translation/` holds framework-wide translations. Per-tool translations in `tool/<NAME>/logic/translation/`.

4. **Turing Machine `print()` prohibition**: Never `print()` inside a `TuringStage` action.

5. **No `logic/` top-level directories**: After migration, only `logic/_/` contains subdirectories. Any new shared code goes under `logic/_/<name>/`. Top-level directories that violate this rule will be flagged by `TOOL ---audit argparse`.

## Sub-Package Navigation

Run `TOOL ---help` for the full command tree with descriptions.

For specific module docs:
```
logic/_/base/AGENT.md       # ToolBase, MCPToolBase, CliEndpoint
logic/_/brain/AGENT.md      # Brain sessions, blueprints
logic/_/git/AGENT.md        # Git operations, .gitignore
logic/_/gui/AGENT.md        # GUI blueprints, widgets
logic/_/agent/AGENT.md      # Agent loop, tools, context
logic/_/assistant/AGENT.md  # GUI assistant, prompts
logic/_/audit/AGENT.md      # Quality auditing
logic/_/config/AGENT.md     # Configuration, colors
logic/_/dev/AGENT.md        # Developer commands
logic/_/test/AGENT.md       # Test runner
logic/_/utils/AGENT.md      # Utilities
```
