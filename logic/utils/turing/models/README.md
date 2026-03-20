# logic/turing/models

Core Turing Machine implementations: single-stage progress display and parallel worker execution.

## Structure

| Module | Purpose |
|--------|---------|
| `progress.py` | `ProgressTuringMachine` — sequential multi-stage progress with erasable lines |
| `worker.py` | `TuringWorker` — parallel task execution with live progress display |
