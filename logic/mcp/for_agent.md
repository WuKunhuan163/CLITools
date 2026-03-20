# logic/mcp - Agent Reference

## Key Interfaces

### config.py
- `is_cursor_environment()` - CURSOR_SESSION_ID, CURSOR_TRACE_ID, TERM_PROGRAM, or ~/.cursor/projects
- `get_mcp_descriptors_dir()` - ~/.cursor/projects/*/mcps
- `get_available_mcp_servers()` - List of server names from mcps dir
- `is_browser_mcp_available()` - "cursor-ide-browser" in servers
- `MCPToolConfig(tool_name, mcp_server, ...)` - `is_available()`, `check_env()`, `to_dict()`

### browser.py
- `BrowserSize` - COMPACT, DEFAULT, LARGE, DRIVE_MENU; `get_preset(name)`, `list_presets()`
- `build_resize_args(width, height, preset, view_id)` - For browser_resize MCP tool
- `BrowserMCPConfig` - SERVER_NAME, KNOWN_TOOLS, `is_available()`, `get_status()`, `colab_url(file_id)`, `drive_folder_url(folder_id)`

### drive_create.py
- `DRIVE_FILE_TYPES` - colab, doc, sheet, slide, form, drawing, mymap, site, ai_studio, apps_script, vid
- `build_create_workflow(folder_id, file_type, filename)` - Steps for AI agent to execute via MCP
- `build_upload_workflow(folder_id)` - File upload via Drive UI (file picker may require manual selection)

## Usage Patterns

1. Check MCP: `BrowserMCPConfig.is_available()` before browser automation
2. Create file: `build_create_workflow(folder_id, "colab", "MyNotebook")` returns workflow dict
3. Resize: `build_resize_args(preset="drive_menu")` for Drive context menus

## Gotchas

- MCP descriptors live in project-specific mcps folder
- Drive create workflow uses browser_navigate, browser_lock, browser_click, etc.
- File picker in upload workflow is OS-level; may not be automatable
