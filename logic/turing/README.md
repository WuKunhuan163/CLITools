# logic/turing

Turing Machine progress display system: stages, workers, multi-line status, and parallel task execution.

## Contents

- **logic.py** - `TuringStage`, `TuringTask`, `StepResult`, `WorkerState`, `TuringError`
- **models/progress.py** - `ProgressTuringMachine` (runs stages with erasable display)
- **models/worker.py** - `DynamicStatusBar`, `ParallelWorkerPool`
- **display/manager.py** - `MultiLineManager` (singleton), `Slot`, `truncate_to_width`, `wrap_text`, `_get_configured_width`
- **worker.py** - `TuringWorker` (executes tasks with step generators)
- **utils.py** - `log_turing_error`
- **terminal/keyboard.py** - `KeyboardSuppressor`, `get_global_suppressor` (suppress echo during progress)

## Structure

```
turing/
  logic.py
  worker.py
  utils.py
  display/
    manager.py
  models/
    progress.py
    worker.py
  terminal/
    __init__.py
    keyboard.py
```
