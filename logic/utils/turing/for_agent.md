# logic/turing - Agent Reference

> **Import convention**: Tools should import from `interface.turing` and `interface.status` (the facade), not directly from `logic.turing`. See `interface/for_agent.md`.

## Key Interfaces

### logic.py
- `TuringStage(name, action, active_status, success_status, fail_status, success_color, fail_color, bold_part, stealth, ...)` - Action can accept `(stage)` for refresh/error reporting
- `TuringTask(name, steps)` - steps = list of callables returning StepResult or generator of StepResult
- `StepResult(display_text, state, is_final)` - state: WorkerState.CONTINUE, SUCCESS, ERROR, EXIT
- `TuringError(brief, full)` - For detailed failure reporting
- `stage.report_error(brief, full)`, `stage.set_captured_output(output)`, `stage.refresh()`

### models/progress.py
- `ProgressTuringMachine(project_root, tool_name, no_warning, manager)` - `add_stage(stage)`, `run(ephemeral, final_newline, final_msg)`
- `refresh_stage(stage)` - Updates active line; use from within action
- Ephemeral: removes stage lines after success; final_msg replaces last stage

### display/manager.py
- `MultiLineManager()` - Singleton; `update(worker_id, text, is_final, truncate)`, `finalize()`
- `truncate_to_width(text, max_width)` - For active slots
- `_get_configured_width()` - From config or terminal detection
- `wrap_text(text, width)` - CJK-aware, ANSI-stripped

### worker.py
- `TuringWorker(worker_id, manager)` - `execute(task)` - Runs step funcs; supports generators yielding StepResult

### models/worker.py
- `DynamicStatusBar(label, manager)` - `set_counts`, `increment_completed`, `update(item_id, action)`, `print_above(msg)`, `clear()`
- `ParallelWorkerPool(max_workers, status_label, manager)` - `map(tasks)`, `run(tasks, success_callback, timeout)` - Tasks: `[{"id", "action", "args", "kwargs"}]`

### terminal/keyboard.py
- `KeyboardSuppressor` - `start()`, `stop(force)`, `suspend()`, `resume()`; context manager
- `get_global_suppressor()` - Shared instance; reference-counted

## Usage Patterns

1. **Stages**: `tm.add_stage(TuringStage(...)); tm.run(ephemeral=True)`
2. **Generators**: Step func yields `StepResult(msg, WorkerState.CONTINUE)` then `StepResult(final, WorkerState.SUCCESS, is_final=True)`
3. **Parallel**: Use `ParallelWorkerPool` or `TuringWorker` + `MultiLineManager` with task queue

### multiline_input.py
- `multiline_input(prompt, placeholder, submit_color, inject_check, poll_interval)` - Multi-line terminal input widget
- Gray placeholder when buffer empty; disappears on first keystroke; reappears when buffer cleared
- Enter = new line; Ctrl+Enter = submit; Backspace on empty line = delete line
- `submit_color` (default BLUE): re-renders submitted text in this color
- `inject_check`: `() -> str|None`; returns injected text or None. Polled every `poll_interval` (0.1s)
- Falls back to `input()` when termios unavailable
- Used by: OPENCLAW CLI (`tool/OPENCLAW/logic/gui/cli.py`)

## Gotchas

- MultiLineManager is singleton; concurrent use shares slots
- `stealth` stages don't print; `no_warning` skips YELLOW/warning stages
- KeyboardSuppressor uses termios; ECHO off, ISIG on for Ctrl+C
- RTL mode affects padding in display manager
- multiline_input uses raw terminal mode; always wrapped in termios save/restore
