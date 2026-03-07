# logic/gui - Agent Guide

> **Import convention**: Tools should import from `interface.gui` (the facade), not directly from `logic.gui`. See `interface/for_agent.md`.

## engine.py

### is_sandboxed() -> bool

Detects Cursor seatbelt, restricted terminal, Docker, or missing display.

### get_safe_python_for_gui() -> str

Returns Python executable with tkinter. Tries PYTHON tool interface first, then manual install paths, then system fallback.

### setup_gui_environment()

Sets `RESOURCE_NAME`, `TK_APP_NAME`, `sys.argv[0]`, `__CFBundleIdentifier` for macOS. Call before `tk.Tk()` in sandboxed environments.

### play_notification_bell(project_root: Path)

Plays bell.mp3 in background thread. Falls back to system sound if file missing.

## manager.py

### handle_gui_remote_command(tool_name, project_root, command, unknown_args, translation_helper) -> int

Creates flag file in `data/run/stops/{pid}.{command}` for matching instances. Commands: "stop", "submit", "cancel", "add_time". Matching: by PID, custom_id (--id), or tool_name.

### run_gui_subprocess(tool_instance, python_exe, script_path, timeout, custom_id, args, waiting_label) -> Dict

Launches GUI as subprocess with `GDS_GUI_MANAGED=1`. Captures stdout for `GDS_GUI_RESULT_JSON:`. Relays `GDS_GUI_LOG:` lines to terminal. Handles add_time via `data/run/added_time/{pid}_{ts}_{inc}.add`. On Ctrl+C, creates stop flag and waits for graceful exit.

### run_file_fallback(tool_instance, initial_content, timeout) -> Optional[str]

When GUI is blocked (sandbox): creates file in `data/input/`, polls for modification, returns content or `__FALLBACK_TIMEOUT__` / `__FALLBACK_INTERRUPTED__`.

## Interface I (Result Protocol)

GUI scripts in managed mode print exactly one line:
```
GDS_GUI_RESULT_JSON:{"status": "success"|"cancelled"|"timeout"|"terminated"|"error", "data": ..., "reason": "..."}
```

Parent parses this from stdout. `data` is State A (current UI state at closure).

## HTML GUI (`logic/gui/html/`)

Browser-based GUI alternative to tkinter. Serves SPA locally via HTTP + WebSocket.

### Available HTML Blueprints

- `html/blueprint/chatbot/` — Multi-session chatbot (used by OPENCLAW)
  - `ChatbotServer(title, on_send, session_provider)` — drop-in replacement for `ChatbotWindow`
  - Opens in Chrome via CDMCP `open_tab()`, or falls back to `webbrowser.open()`
  - No Tcl/Tk dependency required

### When to Use HTML vs Tkinter

- **HTML**: For tools with complex styling needs, web-centric workflows, or CDMCP-dependent tools
- **Tkinter**: For simple dialogs, system-native look, or when browser is unavailable

## Gotchas

- `GDS_GUI_MANAGED=1` must be set for parent to expect JSON on stdout
- Instance registry: `data/run/instances/gui_{pid}.json` with pid, tool_name, custom_id, class, start_time
- Keyboard suppressor runs during GUI wait to avoid echo
- style.py: config from `{style_dir_parent}/data/config.json` under key `gui_style`
