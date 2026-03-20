# EXEC -- Agent Reference

## Commands

```bash
EXEC run "command"       # Run a shell command
EXEC run "cmd" --timeout 30  # With timeout (default: 60s)
EXEC run "cmd" --cwd /dir    # In a specific directory
EXEC which NAME          # Find where a command lives
```

## Notes

- Commands run in a subprocess with captured stdout/stderr
- Non-zero exit codes are reported
- Timeout returns exit code 124
