# Blueprint — Agent Reference

## ToolBase (base.py)

Base for all tools. Handles:
- Path resolution (project_root, tool_dir, tool_module_path)
- Dependencies from tool.json
- CPU limit/timeout from data/config.json
- Hooks engine (lazy), fire_hook()
- CLI: --dev, --test, --setup, --config, --install, --uninstall, --skills, --hooks, --rule
- Subtool delegation (tool/<cmd>/main.py)
- System fallback (GIT, PYTHON, shutil.which)
- Session logging, progress machine, GUI helpers

### Key Methods
- **get_hooks_engine()**, **fire_hook(event_name, **kwargs)**
- **handle_command_line(parser, dev_handler, test_handler)** — returns True if handled
- **run_setup()**, **run_subtool_install(name)**, **run_subtool_uninstall(name, force_yes)**
- **call_other_tool(name, args, capture_output)**
- **get_data_dir()**, **get_log_dir()**, **get_session_logger()**, **log(msg, extra, include_stack)**

### Parameters
- **__init__(tool_name)** — tool_name is the display name (e.g. "GIT", "PYTHON")

## MCPToolBase (mcp.py)

Extends ToolBase for CDMCP browser MCP. Adds:
- Session management (create, boot, list, checkout)
- Overlay (badge, focus, favicon, lock)
- ensure_locked(), apply_overlays(), cleanup_overlays()
- get_mcp_state(), print_mcp_state()
- --mcp-state flag, --mcp-* subcommand rewriting for help

### Key Methods
- **get_session()**, **get_session_window_id()**
- **handle_mcp_commands(args)** — handles `session create|boot|list|checkout`
- **_collect_mcp_state(session, tab_label)** — override in subclass for tool-specific state

### Parameters
- **__init__(tool_name, session_name="")** — session_name defaults to tool_name.lower()

## Gotchas

- `logic.tool.base` re-exports ToolBase from blueprint.base for backward compatibility.
- MCPToolBase loads CDMCP via `logic.cdmcp_loader`; failures are silent (overlay/interact/session_mgr may be None).
- handle_command_line rewrites `--mcp-*` to bare subcommands before argparse sees them.
