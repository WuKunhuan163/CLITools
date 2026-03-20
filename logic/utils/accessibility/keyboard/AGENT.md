# logic/accessibility/keyboard — Agent Reference

## monitor.py — KeyboardMonitor

Global keyboard listener via pynput:
- Detects Cmd/Ctrl+V followed by Enter (paste-then-execute sequence)
- Used by GUI windows to detect when user pastes into external apps
- macOS: Requires Accessibility permissions (`request_accessibility_permission()`)

## settings.py

Keyboard shortcut configuration:
- Settings persisted to `logic/config/keyboard.json`
- macOS-style capture GUI: click field, press combo, click elsewhere to lock
- `load_settings()` returns current shortcut config for all tools

## Gotchas

1. **macOS Accessibility permissions**: Required for pynput global monitoring. Prompt user during setup.
2. **Config location**: `logic/config/keyboard.json` — shared across all tools.
