# Setup — Agent Reference

## ToolEngine

### __init__(tool_name, project_root, parent_tool_dir=None)
- tool_dir: parent_tool_dir/tool_name (default parent_tool_dir = project_root/tool)
- tool_internal: get_logic_dir(tool_dir)
- bin_dir: project_root/bin
- registry_path: project_root/tool.json

### install(is_dependency=False, visited=None) -> bool
Stages: validate_registry, fetch_source (if needed), handle_dependencies (recursive), handle_pip_deps, create_shortcut, run_setup. Uses ProgressTuringMachine. Returns True on success.

### uninstall() -> bool
Runs uninstall_action via TuringMachine: removes bin/<tool>/ dir, legacy shortcut, tool_dir.

### reinstall() -> bool
Calls uninstall() then install().

### create_shortcut(stage=None) -> bool
Creates bin/<shortcut_name>/<shortcut_name> bootstrap script. Uses PYTHON tool's get_python_exec if available. Registers path via register_path.

### is_installed() -> bool
Checks: tool_dir exists, shortcut exists (bin/<name>/<name> or legacy bin/<name>), all dependencies installed.

## Actions (internal)

- **validate_registry** — tool must be in tool.json "tools" (dict or list). Skipped for subtools (parent_tool_dir != project_root/tool).
- **fetch_source** — git checkout from dev/tool/origin branches; fallback to logic/_/install/archived/.
- **handle_pip_deps** — merges tool.json pip_dependencies and requirements.txt; uses PYTHON tool's python if available.
- **run_setup** — subprocess.run([sys.executable, setup.py]).
- **uninstall_action** — rmtree bin dir, remove legacy, rmtree tool_dir.

## Gotchas

- Shortcut name for "PARENT.SUBTOOL" is "SUBTOOL" (last segment).
- create_shortcut embeds project_root path in wrapper; use os.path.relpath for main_py.
- handle_dependencies is recursive; visited set prevents cycles.
- Partial install (dir exists, no shortcut) triggers uninstall stage before install.
