# logic/

Shared core logic for the AITerminalTools framework. All code in this directory is **internal implementation** — tools import from `interface/*`, never directly from `logic/*`.

## Architecture (Post-Migration)

After the cleanup migration, `logic/` has a single organizational structure:

```
logic/
├── _/                    # ALL shared infrastructure lives here
│   ├── base/             # ToolBase, MCPToolBase, CliEndpoint (framework core)
│   ├── brain/            # Brain tasks, sessions, blueprints (---brain eco cmd)
│   ├── git/              # Git operations, .gitignore management, persistence
│   ├── agent/            # Agent loop, tools, context, guidelines
│   ├── assistant/        # LLM assistant GUI, prompts, std tools
│   ├── audit/            # Code quality, import rules, hooks validation
│   ├── config/           # Global configuration, colors, settings
│   ├── dev/              # Developer workflow (create, sync, archive)
│   ├── eco/              # Ecosystem navigation and search
│   ├── gui/              # Tkinter blueprint framework
│   ├── help/             # ---help eco command (DFS argparse.json tree)
│   ├── hooks/            # Event-driven hook engine
│   ├── install/          # Tool installation engine
│   ├── lang/             # Internationalization, language audit
│   ├── list/             # Tool listing
│   ├── migrate/          # Migration from external sources
│   ├── reinstall/        # Reinstallation logic
│   ├── search/           # Cross-project search index
│   ├── setup/            # Setup and dependency resolution
│   ├── skills/           # Skill management commands
│   ├── status/           # Tool status display
│   ├── test/             # Test runner with CPU monitoring
│   ├── translation/      # Root framework translations
│   ├── uninstall/        # Tool uninstallation
│   ├── utils/            # Shared utilities (display, logging, system, turing)
│   └── workspace/        # External project workspaces
├── _.py                  # EcoCommand alias for CliEndpoint
├── __init__.py           # Package marker
└── (top-level .py files) # resolve.py, cdmcp_loader.py, worker.py, lifecycle.py
```

## Key Rule: logic/_/ is the Command Map

Every directory under `logic/_/` with a `cli.py` file corresponds to a `---<name>` eco command:

```
logic/_/audit/cli.py    →  TOOL ---audit
logic/_/brain/cli.py    →  TOOL ---brain
logic/_/dev/cli.py      →  TOOL ---dev
logic/_/help/cli.py     →  TOOL ---help
```

This mapping is **automatic** — `ToolBase.handle_command_line()` discovers commands by traversing `logic/_/`. No registration needed.

Each directory should also contain `argparse.json` — a declarative schema that powers `---help` and enables audit.

## Three-Tier CLI Convention

```
---<eco>    Ecosystem commands shared across all tools (logic/_/<name>/cli.py)
--<tool>    Tool-specific commands (argparse in main.py)
-<modifier> Decorators that modify behavior (-no-warning, -tool-quiet)
```

## Import Convention

Within `logic/`, cross-references use:
- `from logic._.<module>...` for command modules
- `from logic._.<module>...` for infrastructure (everything is now under `_/`)

Outside `logic/`, tools always use `interface.*`.

## Top-Level Files

| File | Purpose |
|------|---------|
| `_.py` | Re-exports `CliEndpoint` as `EcoCommand` for convenience |
| `resolve.py` | Universal `sys.path` resolver |
| `cdmcp_loader.py` | CDMCP session bootstrap for Chrome-based tools |
| `lifecycle.py` | Tool install/uninstall/list operations |
| `worker.py` | Background worker/process utilities |
