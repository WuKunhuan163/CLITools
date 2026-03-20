# logic/mcp

MCP (Model Context Protocol) utilities: browser config, environment detection, and Drive file creation workflows.

## Contents

- **config.py** - `is_cursor_environment`, `get_mcp_descriptors_dir`, `get_available_mcp_servers`, `is_browser_mcp_available`, `MCPToolConfig`
- **browser.py** - `BrowserSize`, `BrowserMCPConfig`, `build_resize_args`
- **drive_create.py** - `DRIVE_FILE_TYPES`, `get_supported_types`, `build_create_workflow`, `build_upload_workflow`

## Structure

```
mcp/
  __init__.py
  config.py
  browser.py
  drive_create.py
```
