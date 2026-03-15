# logic/accessibility - Agent Reference

## Key Interfaces

### keyboard/monitor.py
- `is_available()` - pynput importable
- `start_paste_enter_listener(on_trigger)` - Fires after Cmd/Ctrl+V then Enter within 5s; returns listener (call .stop())
- `start_modifier_listener(on_modifier)` - Fires on any Cmd/Ctrl press
- `stop_listener(listener)`
- `request_accessibility_permission()` - macOS: show system dialog
- `check_accessibility_trusted()` - macOS: AXIsProcessTrusted
- Run `python -m logic.accessibility.keyboard.monitor` for interactive test GUI

### keyboard/settings.py
- `load_settings()` - Returns dict of paste, confirm
- `save_settings(settings)`
- `get_paste_combo()`, `get_confirm_key()`
- `open_settings_gui(parent)` - Tkinter GUI; macOS-style capture (click field, press key)

## Usage Patterns

1. **Paste+Enter**: Used by GUI windows to detect user pasted command in external app and pressed Enter
2. **Settings**: Stored in `logic/config/keyboard.json`; defaults: cmd+v/ctrl+v, return
3. **macOS**: Requires Accessibility permission for global capture

## Gotchas

- pynput required; `is_available()` checks before use
- Logs to `tmp/keyboard_log/kb_*.log`
- Settings GUI uses `_KeyCaptureEntry` - click to activate, press key to assign
