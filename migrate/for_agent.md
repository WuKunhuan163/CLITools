# migrate/ — Agent Guide

## Purpose

Symmetric directory for external resource migration. Each subdirectory is a "domain" representing an external source (GitHub project, API, marketplace).

## Architecture

```
migrate/<domain>/
  info.json   — Required. Domain metadata:
    {
      "name": str,
      "source": str (URL),
      "description": str,
      "levels": [str],       # Supported migration levels
      "target_tool": str,    # Optional: default target tool
      "last_checked": str,   # ISO timestamp or null
    }
  __init__.py
  <level>.py  — Migration module. Must expose execute(args: list) -> int
  check.py    — Optional. Must expose check_pending() -> dict
```

## Adding a New Domain

1. Create `migrate/<domain>/`
2. Write `info.json` with metadata
3. Implement level-specific `<level>.py` modules
4. Each module must have `execute(args: list) -> int`

## Entry Points

- CLI: `TOOL --migrate --<level> <domain> [args]`
- Python: `logic.command.migrate.execute_migration(domain, level, args)`
- Discovery: `logic.command.migrate.list_domains()`

## Draft vs. Final

Draft migrations (`--draft-*`) download upstream code and scaffold a directory structure, but the code needs manual adaptation to ecosystem conventions. Final migrations (`--tool`, `--infrastructure`, etc.) produce ready-to-use results.
