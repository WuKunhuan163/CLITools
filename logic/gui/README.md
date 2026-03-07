# logic/gui

GUI layer for AITerminalTools: engine setup, subprocess management, and Tkinter blueprints.

## Purpose

Provide a unified GUI subsystem for tools that need user input via windows. Handles sandbox detection, Python/tkinter availability, subprocess launch, result capture, and file-based fallback when GUI is blocked.

## Structure

- `engine.py`: Sandbox detection, safe Python resolution, GUI environment setup, notification bell
- `manager.py`: Remote command handling, GUI subprocess launcher, file fallback
- `tkinter/`: Tkinter blueprints, widgets, style
- `translation/`: Shared GUI translation files (ar.json, zh.json)

## Key Exports

- `engine`: `setup_gui_environment`, `get_safe_python_for_gui`, `play_notification_bell`, `is_sandboxed`, `get_sandbox_type`
- `manager`: `handle_gui_remote_command`, `run_gui_subprocess`, `run_file_fallback`

## Usage

Tools typically call `tool.run_gui(python_exe, script_path, timeout)` which uses `manager.run_gui_subprocess`. GUI scripts run in a child process, print `GDS_GUI_RESULT_JSON:{...}` on exit, and are controlled via flag files in `data/run/stops/`.
