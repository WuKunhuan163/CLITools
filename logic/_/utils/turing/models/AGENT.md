# logic/turing/models — Agent Reference

## progress.py — ProgressTuringMachine

Sequential multi-stage progress:
```python
pm = ProgressTuringMachine("Task Name", stages=[stage1, stage2, ...])
pm.run()
```

Each stage is a `TuringStage` with an action callback. Stages run sequentially, displaying erasable progress lines.

## worker.py — TuringWorker

Parallel task execution with ThreadPoolExecutor:
```python
worker = TuringWorker(tasks=[...], max_workers=4)
worker.run()
```

Live display of per-task progress. Uses `KeyboardSuppressor` to prevent raw input during display.

## Gotchas

1. **Never use `print()` in stages**: Use `stage.refresh()` for live updates. `print()` breaks erasable line tracking.
2. **Thread safety**: Worker display is coordinated via display manager locks.
3. **Keyboard suppression**: Active during Turing Machine execution to prevent terminal echo corruption.
