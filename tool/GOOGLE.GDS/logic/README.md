# GOOGLE.GDS Logic

Google Drive Remote Controller for Colab. Provides a shell-like interface to interact with files on Google Drive through Google Colab's runtime.

## Structure

| Module | Purpose |
|--------|---------|
| `auth.py` | Service account authentication, JWT token generation, key validation |
| `utils.py` | GDS config loading, service account credentials, Drive API helpers |
| `state.py` | `GDSStateManager` — persistent shell state (cwd, history, shell type) |
| `executor.py` | Generate remote command scripts (bash/Python) for Colab execution |
| `remount.py` | Drive remount script generation (API reconnection) |
| `reconnection_manager.py` | Auto-remount trigger based on command count/duration thresholds |
| `upload_gui.py` | GUI for large file upload with drag-and-drop instructions |

## Sub-Packages

| Directory | Purpose |
|-----------|---------|
| `command/` | Individual CLI commands (ls, cd, cat, grep, edit, upload, shell, etc.) |
| `mcp/` | MCP server: CDP-based notebook creation and remote execution |
| `tutorial/` | Interactive setup wizards (setup_guide, mcp_setup) |
| `translation/` | Localized strings (zh.json) |
