# logic/turing/terminal — Agent Reference

## keyboard.py

`KeyboardSuppressor` puts terminal in raw mode to suppress input echo:
- `suppress()`: Enter raw mode (no echo, no line buffering)
- `restore()`: Restore original terminal settings
- `get_global_suppressor()`: Returns singleton instance

Uses `termios`/`tty` (Unix only). Falls back to no-op on Windows.

## Gotchas

1. **Unix only**: `termios`/`tty` not available on Windows. Import guarded with try/except.
2. **Singleton**: Use `get_global_suppressor()` — do not create multiple instances.
3. **Signal safety**: Registers SIGINT handler to restore terminal on Ctrl+C.
