"""Persistent JSON-backed store for TODO items.

Each item has: id, content, status, created_at, updated_at.
Status: pending | in_progress | completed | abandoned
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

MAX_ITEMS = 50
VALID_STATUSES = {"pending", "in_progress", "completed", "abandoned"}

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_FILE = _DATA_DIR / "todos.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load(path: Path) -> List[Dict[str, Any]]:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save(path: Path, items: List[Dict[str, Any]]) -> None:
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def _trim(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep at most MAX_ITEMS.  Evict oldest completed/abandoned first."""
    if len(items) <= MAX_ITEMS:
        return items
    done = [i for i in items if i["status"] in ("completed", "abandoned")]
    active = [i for i in items if i["status"] not in ("completed", "abandoned")]
    done.sort(key=lambda i: i.get("updated_at", 0))
    while len(done) + len(active) > MAX_ITEMS and done:
        done.pop(0)
    return active + done


def add(content: str, *, path: Optional[Path] = None, context: str = "default") -> Dict[str, Any]:
    """Add a new TODO item.  Returns the created item."""
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    item = {
        "id": uuid.uuid4().hex[:8],
        "content": content,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    items.append(item)
    items = _trim(items)
    _save(fp, items)
    return item


def update_status(item_id: str, status: str, *, path: Optional[Path] = None, context: str = "default") -> Optional[Dict[str, Any]]:
    """Update an item's status.  Returns the updated item or None."""
    if status not in VALID_STATUSES:
        return None
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    for item in items:
        if item["id"] == item_id:
            item["status"] = status
            item["updated_at"] = time.time()
            _save(fp, items)
            return item
    return None


def remove(item_id: str, *, path: Optional[Path] = None, context: str = "default") -> bool:
    """Remove an item by ID.  Returns True if found and removed."""
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    before = len(items)
    items = [i for i in items if i["id"] != item_id]
    if len(items) < before:
        _save(fp, items)
        return True
    return False


def list_items(*, path: Optional[Path] = None, context: str = "default",
               status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all items, optionally filtered by status."""
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    if status_filter and status_filter in VALID_STATUSES:
        items = [i for i in items if i["status"] == status_filter]
    return items


def clear(*, path: Optional[Path] = None, context: str = "default",
          only_done: bool = False) -> int:
    """Clear items.  Returns count removed."""
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    before = len(items)
    if only_done:
        items = [i for i in items if i["status"] not in ("completed", "abandoned")]
    else:
        items = []
    _save(fp, items)
    return before - len(items)


def get(item_id: str, *, path: Optional[Path] = None, context: str = "default") -> Optional[Dict[str, Any]]:
    """Get a single item by ID."""
    fp = path or (_DATA_DIR / f"{context}.json")
    items = _load(fp)
    for item in items:
        if item["id"] == item_id:
            return item
    return None
