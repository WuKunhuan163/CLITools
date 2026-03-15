# logic/turing/terminal

Terminal keyboard control for the Turing Machine system. Suppresses keyboard input during progress display to prevent echo corruption.

## Structure

| Module | Purpose |
|--------|---------|
| `keyboard.py` | `KeyboardSuppressor`, `get_global_suppressor()` — raw terminal mode control |
