# logic/turing

Turing Machine progress display system: stages, workers, multi-line status, parallel task execution, and interactive selectors.

## Contents

- **logic.py** - `TuringStage`, `TuringTask`, `StepResult`, `WorkerState`, `TuringError`
- **models/progress.py** - `ProgressTuringMachine` (runs stages with erasable display)
- **models/worker.py** - `DynamicStatusBar`, `ParallelWorkerPool`
- **display/manager.py** - `MultiLineManager` (singleton), `Slot`, `truncate_to_width`, `wrap_text`, `_get_configured_width`
- **worker.py** - `TuringWorker` (executes tasks with step generators)
- **utils.py** - `log_turing_error`
- **status.py** - `fmt_status`, `fmt_detail`, `fmt_stage` (minimal-emphasis status message formatters)
- **select.py** - `select_menu` (arrow-key list selector: up/down/Enter/Esc)
- **multiline_input.py** - `multiline_input` (multi-line terminal input with placeholder, submit color, and injection)
- **terminal/keyboard.py** - `KeyboardSuppressor`, `get_global_suppressor` (suppress echo during progress)

## Structure

```
turing/
  logic.py
  worker.py
  utils.py
  status.py
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

## Status Message Formatters

Reusable functions that enforce the **minimal-emphasis** styling rule:
bold/color only on the core phrase; complements and details in default or dim style.

```python
from logic.turing.status import fmt_status, fmt_detail, fmt_stage

# One-line status: bold label + optional complement + optional dim detail
print(fmt_status("Saved."))                                  #   **Saved.**
print(fmt_status("Saved.", dim="3 policies"))                #   **Saved.** 3 policies (dim)
print(fmt_status("Failed.", complement="Try /setup.", style="error"))  #   Failed. Try /setup.

# Detail line: auto-dimmed, indented 4 spaces
print(fmt_detail("Session be58ac60 is ready."))              #     Session be58ac60 is ready. (dim)
print(fmt_detail(f"{YELLOW}Warning{RESET}", styled=True))    #     Warning (caller styling)

# Stage indicator: > {label} {desc}   — colored by status
print(fmt_stage("Starting session...", status="active"))     #   > **Starting session...**
print(fmt_stage("Session started.", desc="be58ac60", status="done"))  #   >(green) **Session started.** be58ac60
```

All functions return formatted strings (no trailing newline) — the caller decides when to print.

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

| State | Indicator | Text color |
|-------|-----------|-----------|
| Input (idle) | `□` / `║` (default) | default |
| Submitted | `□` / `║` (default) | CYAN (command blue) |
| Running | `■` / `┃` (default) | CYAN (command blue) |
| Done (success) | `■` / `┃` (green) | CYAN (command blue) |
| Done (error) | `■` / `┃` (red) | CYAN (command blue) |
| Agent output | `>` / `\|` (dim) | dim |

**Command blue** (`CYAN` in `logic/config/colors.json`) is the centralized color for
user-submitted command text. Import via `get_color("CYAN", "\033[36m")`.
