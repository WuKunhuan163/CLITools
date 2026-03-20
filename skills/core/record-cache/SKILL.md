---
name: record-cache
description: Caching and persistence patterns in AITerminalTools. Covers AuditManager, tool_cache, test cache, and log rotation.
---

# Record & Cache Patterns

## AuditManager

Central audit tracking for code quality:

```python
from logic.tool.audit.utils import AuditManager

manager = AuditManager(tool_name="MY_TOOL")
manager.record("IMP001", filepath, "Cross-tool import via logic/")
manager.summary()   # Print pass/fail counts
```

## Tool Cache (`data/` Directory)

Each tool can store persistent data in its `data/` directory (gitignored by default):

```
tool/<NAME>/data/
    cache.json         # Cached API responses
    config.json        # User configuration
    session.json       # Session state
```

### Access Pattern

```python
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CACHE_FILE = DATA_DIR / "cache.json"
```

## Test Cache

Test results are cached to speed up re-runs:

```
tool/<NAME>/data/test_cache/
    test_00_help.json     # Last result + timing
```

## Log Rotation

Session logs auto-rotate to prevent disk bloat using a "limit + delete half" strategy:
- Logs live in `tool/<NAME>/data/sessions/{id}/logs/` (or `data/logs/` for standalone)
- Default limit: 1024 entries per session
- When limit is reached, oldest half is deleted in one batch

See the **retention-rotation** skill for the full pattern and implementation template.

## Guidelines

1. Always use `data/` for tool-specific persistent state
2. Never commit `data/` contents (gitignored via `**/data/`)
3. Handle missing cache gracefully (first-run scenario)
4. Use JSON for human-readable caches, JSONL for append-only logs
