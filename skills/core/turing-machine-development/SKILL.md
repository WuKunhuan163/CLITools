---
name: turing-machine-development
description: Progress display system using TuringStage and ProgressTuringMachine. Covers single-stage, multi-stage, parallel workers, and multi-line display.
---

# Turing Machine Development

## Overview

The Turing machine system provides rich terminal progress displays. It supports single-stage spinners, multi-stage pipelines, parallel worker pools, and multi-line dynamic output.

## Core Classes

```python
from logic.interface.turing import (
    TuringStage,              # Single stage definition
    ProgressTuringMachine,    # Sequential stage runner
    TuringWorker,             # Task executor with step generators
    TuringTask, StepResult, WorkerState,  # Worker primitives
    ParallelWorkerPool,       # Parallel execution
    MultiLineManager,         # Multi-line terminal output
    TuringError,              # Structured error reporting
)
```

## Single-Stage Progress

```python
from logic.interface.turing import ProgressTuringMachine, TuringStage

def download_action(stage):
    for i in range(100):
        stage.refresh(f"Downloading... {i+1}%")
        do_work()
    return True

stage = TuringStage(
    name="download",
    action=download_action,
    active_status="Downloading files",
    success_status="Download complete",
    fail_status="Download failed",
    success_color="GREEN",
    fail_color="RED",
)

machine = ProgressTuringMachine(stages=[stage])
machine.run()
```

## Multi-Stage Pipeline

```python
stages = [
    TuringStage(name="fetch",   action=fetch_data,   active_status="Fetching..."),
    TuringStage(name="parse",   action=parse_data,    active_status="Parsing..."),
    TuringStage(name="upload",  action=upload_results, active_status="Uploading..."),
]

machine = ProgressTuringMachine(stages=stages)
machine.run(ephemeral=False, final_newline=True)
```

## Stage Action Signature

```python
def my_action(stage: TuringStage) -> bool:
    """Return True on success, False on failure."""
    try:
        result = do_work()
        stage.refresh(f"Processed {result.count} items")
        return True
    except Exception as e:
        stage.report_error(brief="Connection failed", full=str(e))
        return False
```

### Key Stage Methods

- `stage.refresh(text)` — Update the display text
- `stage.report_error(brief, full)` — Record a `TuringError`
- `stage.machine` — Reference to the parent machine

### Stage Options

- `is_sticky=True` — Keep the stage visible after completion
- `stealth=True` — Don't display the stage (background work)

## Via ToolBase

```python
machine = tool.create_progress_machine(stages=[...])
machine.run()
```

## Parallel Workers

For concurrent tasks with a shared progress display:

```python
from logic.interface.turing import ParallelWorkerPool, TuringTask, StepResult

def download_step(task):
    yield StepResult(success=True, message=f"Downloaded {task.name}")

tasks = [TuringTask(name=f"file_{i}", steps=[download_step]) for i in range(10)]

pool = ParallelWorkerPool(max_workers=4)
results = pool.run(tasks)
```

## Multi-Line Manager

For dynamic multi-line terminal output (e.g., parallel progress bars):

```python
from logic.interface.turing import MultiLineManager

mlm = MultiLineManager.get_instance()
mlm.update(worker_id="dl_1", text="Downloading A... 45%")
mlm.update(worker_id="dl_2", text="Downloading B... 72%")
mlm.update(worker_id="dl_1", text="Downloaded A ✓", is_final=True)
```

## Display Utilities

```python
from logic.interface.turing import _get_configured_width, truncate_to_width

width = _get_configured_width()          # Terminal width (default 80)
text = truncate_to_width("long text", width)  # Fit to terminal
```

## Error Handling

```python
from logic.interface.turing import TuringError

error = TuringError(brief="Auth failed", full="HTTP 401: Invalid token\n...")
stage.report_error(brief=error.brief, full=error.full)
```

Errors are automatically logged to the session log via `log_turing_error()`.

## Guidelines

1. Always provide `active_status`, `success_status`, and `fail_status` for user clarity
2. Use `stage.refresh()` inside long-running actions to show progress
3. Use `report_error()` instead of raising exceptions — it preserves structured error info
4. Prefer `ParallelWorkerPool` for I/O-bound tasks (downloads, API calls)
5. Use `ephemeral=True` for transient progress that clears after completion
6. Test Turing stages in isolation before composing into pipelines
