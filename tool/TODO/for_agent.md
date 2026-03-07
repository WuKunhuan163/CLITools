# TODO — Agent Reference

## Quick Start

```python
from tool.TODO.interface.main import todo_add, todo_list, todo_done, todo_start, todo_abandon
```

## Functions

| Function | Signature | Returns |
|----------|-----------|---------|
| `todo_add` | `(content, context="default")` | item dict |
| `todo_list` | `(context="default", status_filter=None)` | list of item dicts |
| `todo_done` | `(item_id, context="default")` | updated item or None |
| `todo_start` | `(item_id, context="default")` | updated item or None |
| `todo_abandon` | `(item_id, context="default")` | updated item or None |
| `todo_remove` | `(item_id, context="default")` | bool |
| `todo_clear` | `(context="default", only_done=False)` | int (count removed) |
| `todo_get` | `(item_id, context="default")` | item dict or None |

## Context Isolation

Use `context` to isolate todo lists per session:
```python
todo_add("Fix bug", context="session-abc123")
todo_list(context="session-abc123")
```

## CLI

```bash
TODO add "Fix the bug"
TODO list --status pending
TODO done a1b2c3d4
TODO clear --done
```

## Capacity

Max 50 items per context. When exceeded, oldest completed/abandoned items are auto-evicted.
