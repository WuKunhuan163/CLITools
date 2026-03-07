# logic/turing

Turing Machine progress display system: stages, workers, multi-line status, parallel task execution, and interactive selectors.

## Contents

- **logic.py** - `TuringStage`, `TuringTask`, `StepResult`, `WorkerState`, `TuringError`
- **models/progress.py** - `ProgressTuringMachine` (runs stages with erasable display)
- **models/worker.py** - `DynamicStatusBar`, `ParallelWorkerPool`
- **display/manager.py** - `MultiLineManager` (singleton), `Slot`, `truncate_to_width`, `wrap_text`, `_get_configured_width`
- **worker.py** - `TuringWorker` (executes tasks with step generators)
- **utils.py** - `log_turing_error`
- **select.py** - `select_menu` (arrow-key list selector: up/down/Enter/Esc)
- **multiline_input.py** - `multiline_input` (multi-line terminal input with placeholder, submit color, and injection)
- **terminal/keyboard.py** - `KeyboardSuppressor`, `get_global_suppressor` (suppress echo during progress)

## Structure

```
turing/
  logic.py
  worker.py
  utils.py
  select.py
  multiline_input.py
  display/
    manager.py
  models/
    progress.py
    worker.py
  terminal/
    __init__.py
    keyboard.py
```

## Interactive Selectors

### Vertical list (up/down/Enter)

```python
from logic.turing.select import select_menu

choice = select_menu("Pick a color:", [
    {"label": "Red", "value": "red"},
    {"label": "Blue", "value": "blue", "detail": "recommended"},
])
# Returns selected dict or None if cancelled (Esc/Ctrl+C)
```

### Horizontal inline (left/right/Enter)

```python
from logic.turing.select import select_horizontal

idx = select_horizontal("Allow?", ["Run Always", "Run Once", "Reject"], default_index=2)
# Returns index (0/1/2) or None if cancelled
```

### Masked input

```python
from logic.turing.select import read_masked

key = read_masked("Enter API key:", allow_empty=True)
# Returns string or None if cancelled
```

Terminal raw mode is saved/restored automatically with `atexit` guard.

### Multi-line input (CLI blueprint)

```python
from logic.turing.multiline_input import multiline_input

text = multiline_input(
    prompt="\n\u25A1 ",                    # □ idle indicator
    continuation="\u2551 ",                # ║ continuation prefix
    placeholder="Type command here, Ctrl+D to submit.",
    submit_color="\033[34m",               # BLUE after submit
    inject_check=my_inject_fn,             # () -> str|None for external injection
    poll_interval=0.1,
)
```

Features:
- **Gray placeholder** shown when buffer is empty; disappears on first keystroke
- **Enter** creates a new line; **Ctrl+D** (or Ctrl+J, Ctrl+Enter) submits
- **Continuation prefix**: multi-line input uses `║` (or custom prefix) for lines after the first
- **Backspace** on an empty line removes that line (and its `║`); when all lines cleared, placeholder reappears
- After submit, the input text is reprinted in `submit_color` (default: BLUE)
- **External injection** via `inject_check` callable polled every `poll_interval` seconds
- Falls back to `input()` when termios is unavailable (e.g., non-TTY environments)

#### Visual indicator system

| State | First line | Continuation lines |
|-------|-----------|-------------------|
| Input (idle) | `□ text` | `║ text` |
| Running | `■ text` | `┃ text` |
| Done (success) | `■ text` (green) | `┃ text` (green) |
| Done (error) | `■ text` (red) | `┃ text` (red) |
| Agent output | `> text` (dim) | `\| text` (dim) |
