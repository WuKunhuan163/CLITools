# BACKGROUND Tool

Manage long-running tasks in the background.

## Features

- **Non-blocking Execution**: Run time-consuming commands in the background.
- **Lifecycle Management**: List, stop, and wait for background processes.
- **Logging**: Automatically capture and view background output logs in `data/log/`.
- **Isolated Runtime**: Automatically uses the `PYTHON` tool environment.

## Usage

### Run a command in background
```bash
BACKGROUND run "sleep 60 && echo Done"
```

### List running processes
```bash
BACKGROUND list
```

### Stop a process
```bash
BACKGROUND stop <ID>
```

### Wait for a process to finish
```bash
BACKGROUND wait <ID>
```

