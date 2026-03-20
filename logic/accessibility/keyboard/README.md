# logic/accessibility/keyboard

Keyboard monitoring and shortcut management. Provides paste-then-enter detection and customizable keyboard shortcut settings.

## Structure

| Module | Purpose |
|--------|---------|
| `monitor.py` | `KeyboardMonitor` — pynput-based global keyboard listener for paste+enter detection |
| `settings.py` | Keyboard shortcut settings GUI and config persistence |
