# TODO

Agent task management tool. Provides a persistent, JSON-backed todo list that agents and tools can use to track work items.

## CLI Usage

```bash
TODO add "Implement feature X"
TODO list
TODO list --status pending
TODO start <id>
TODO done <id>
TODO abandon <id>
TODO remove <id>
TODO clear
TODO clear --done
```

All commands accept `--context <name>` to isolate lists (e.g. per session).

## Programmatic Interface

```python
from tool.TODO.interface.main import todo_add, todo_list, todo_done

item = todo_add("Implement feature X", context="session-abc")
items = todo_list(context="session-abc", status_filter="pending")
todo_done(item["id"], context="session-abc")
```

## Design

- **Storage**: JSON files in `data/<context>.json`, one per context
- **Capacity**: Max 50 items per list. When exceeded, oldest completed/abandoned items are evicted first.
- **Statuses**: `pending`, `in_progress`, `completed`, `abandoned`
- **IDs**: 8-character hex strings (UUID-based)

## Item Schema

```json
{
  "id": "a1b2c3d4",
  "content": "Task description",
  "status": "pending",
  "created_at": 1709827200.0,
  "updated_at": 1709827200.0
}
```
