---
name: retention-rotation
description: Retention and rotation patterns for logs, caches, and file-based storage. Use when implementing limit-based cleanup, log rotation, or cache eviction.
triggers:
  - log rotation
  - cache limit
  - retention policy
  - delete old logs
  - prune
  - evict
  - cleanup old entries
  - max entries
  - log management
---

# Retention & Rotation Architecture

## Core Pattern: "Limit + Delete Half"

When a collection of files or entries reaches a configured limit, **delete the oldest half** in one batch. This amortizes cleanup cost — each item is only touched twice across its lifetime (created once, deleted once), giving O(1) amortized cost per item.

### Infrastructure

**Use the built-in `cleanup_old_files` function**:

```python
from interface.utils import cleanup_old_files

cleanup_old_files("/path/to/logs", pattern="*.log", limit=100)
```

This function applies the "limit + delete half" pattern automatically.

### Reference Implementation (for custom cases)

`logic/git/persistence.py` — `GitPersistenceManager._cleanup_old_caches`:

```python
def _cleanup_old_caches(self):
    """Deletes half when limit exceeded."""
    caches = sorted(
        [d for d in self.temp_base.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
    )
    if len(caches) >= self.limit:
        to_delete = len(caches) // 2
        for i in range(to_delete):
            try:
                shutil.rmtree(caches[i])
            except:
                pass
```

### When to Apply

Use this pattern whenever you need bounded storage:

| Use Case | Sort Key | Item Type | Default Limit |
|---|---|---|---|
| Session operation logs | `st_mtime` | `.log.md` files | 1024 |
| Git persistence caches | `st_mtime` | directories | 8 |
| API response caches | insertion order | JSON entries | configurable |
| Temp test artifacts | `st_mtime` | files | configurable |

## Implementation Template

```python
from pathlib import Path

DEFAULT_LIMIT = 1024

def rotate(directory: Path, glob_pattern: str, max_items: int = DEFAULT_LIMIT) -> int:
    """Delete oldest half of matching items when limit is reached.
    
    Returns the number of items removed.
    """
    items = sorted(directory.glob(glob_pattern), key=lambda p: p.stat().st_mtime)
    if len(items) < max_items:
        return 0
    to_delete = len(items) // 2
    removed = 0
    for i in range(to_delete):
        try:
            items[i].unlink()
            removed += 1
        except OSError:
            pass
    return removed
```

For directories instead of files, use `shutil.rmtree(items[i])`.

## Configuration Pattern

Expose the limit as a user-configurable setting:

```python
# In tool's main.py or config system
_CONFIG_KEYS = {
    "log_limit": ("int", 1024, "Max operation logs per session (deletes half when exceeded)."),
}
```

The "delete half" ratio is fixed by convention — do not expose it as a separate config key. This keeps the interface simple and the amortized cost optimal.

## Design Principles

1. **Sort by `st_mtime`** — oldest items are deleted first.
2. **Delete half, not one-by-one** — amortizes the cost so cleanup is infrequent but effective.
3. **Check `len(items) < max_items` first** — do nothing if under limit (fast path).
4. **Tolerate OSError** — individual file deletions may fail; skip and continue.
5. **Return count of removed items** — callers can log or report if needed.
6. **Static method or free function** — rotation logic should be callable without instantiating a manager.

## Live Examples

- `tool/OPENCLAW/logic/session.py` — `SessionLog.rotate()`: per-session log retention.
- `logic/git/persistence.py` — `GitPersistenceManager._cleanup_old_caches()`: branch-switch persistence caches.

## Anti-Patterns

- **Deleting one at a time in a loop until under limit** — O(n) cleanup on every insertion.
- **Exposing "batch size" as a config** — adds complexity without benefit; half is optimal.
- **Not sorting before deletion** — risks deleting recent items instead of oldest.
- **Blocking I/O in the main thread** — for real-time UIs, run rotation in a background thread.
