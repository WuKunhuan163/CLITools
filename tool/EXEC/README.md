# EXEC

Lightweight shell command execution tool with timeout and output capture.

## Commands

```bash
EXEC run "ls -la"              # Execute a command
EXEC run "sleep 5" --timeout 3 # With timeout
EXEC run "make" --cwd /path    # With working directory
EXEC which python3             # Find command path
```

## Purpose

Provides a standardized interface for shell command execution. Used by agents as a primitive exploration tool for running shell commands with structured error handling and timeout support.
