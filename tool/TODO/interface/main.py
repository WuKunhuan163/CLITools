"""Public interface for the TODO tool.

Provides programmatic access to task management for other tools
(especially OPENCLAW agent).

Usage::

    from tool.TODO.interface.main import todo_add, todo_list, todo_done

    item = todo_add("Implement feature X", context="session-abc123")
    items = todo_list(context="session-abc123")
    todo_done(item["id"], context="session-abc123")
"""

from tool.TODO.logic.store import (
    add as _add,
    update_status as _update,
    remove as _remove,
    list_items as _list,
    clear as _clear,
    get as _get,
)


def todo_add(content: str, context: str = "default"):
    """Add a new task.  Returns the created item dict."""
    return _add(content, context=context)


def todo_list(context: str = "default", status_filter: str = None):
    """List all tasks.  Returns list of item dicts."""
    return _list(context=context, status_filter=status_filter)


def todo_done(item_id: str, context: str = "default"):
    """Mark a task as completed.  Returns updated item or None."""
    return _update(item_id, "completed", context=context)


def todo_start(item_id: str, context: str = "default"):
    """Mark a task as in-progress.  Returns updated item or None."""
    return _update(item_id, "in_progress", context=context)


def todo_abandon(item_id: str, context: str = "default"):
    """Mark a task as abandoned.  Returns updated item or None."""
    return _update(item_id, "abandoned", context=context)


def todo_remove(item_id: str, context: str = "default"):
    """Permanently remove a task.  Returns True if found."""
    return _remove(item_id, context=context)


def todo_clear(context: str = "default", only_done: bool = False):
    """Clear tasks.  Returns count removed."""
    return _clear(context=context, only_done=only_done)


def todo_get(item_id: str, context: str = "default"):
    """Get a single task by ID.  Returns item dict or None."""
    return _get(item_id, context=context)
