"""
Queue management for USERINPUT --queue mechanism.

Stores queued prompts in a JSON file. Each prompt is a plain text string
(no system prompts or feedback directives are stored).

File: tool/USERINPUT/logic/queue.json
Format: {"prompts": ["prompt1", "prompt2", ...]}
"""
import json
from pathlib import Path
from typing import List, Optional

QUEUE_FILE = Path(__file__).resolve().parent / "queue.json"


def _load() -> List[str]:
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("prompts", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save(prompts: List[str]):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump({"prompts": prompts}, f, indent=2, ensure_ascii=False)


def add(text: str):
    """Append a prompt to the queue."""
    prompts = _load()
    prompts.append(text)
    _save(prompts)


def list_all() -> List[str]:
    """Return all queued prompts."""
    return _load()


def claim() -> Optional[str]:
    """Remove and return the first prompt from the queue, or None if empty."""
    prompts = _load()
    if not prompts:
        return None
    first = prompts.pop(0)
    _save(prompts)
    return first


def move_up(index: int) -> bool:
    """Move item at index one position up. Returns True on success."""
    prompts = _load()
    if index <= 0 or index >= len(prompts):
        return False
    prompts[index - 1], prompts[index] = prompts[index], prompts[index - 1]
    _save(prompts)
    return True


def move_down(index: int) -> bool:
    """Move item at index one position down. Returns True on success."""
    prompts = _load()
    if index < 0 or index >= len(prompts) - 1:
        return False
    prompts[index], prompts[index + 1] = prompts[index + 1], prompts[index]
    _save(prompts)
    return True


def move_to_top(index: int) -> bool:
    """Move item at index to the top. Returns True on success."""
    prompts = _load()
    if index <= 0 or index >= len(prompts):
        return False
    item = prompts.pop(index)
    prompts.insert(0, item)
    _save(prompts)
    return True


def move_to_bottom(index: int) -> bool:
    """Move item at index to the bottom. Returns True on success."""
    prompts = _load()
    if index < 0 or index >= len(prompts) - 1:
        return False
    item = prompts.pop(index)
    prompts.append(item)
    _save(prompts)
    return True


def replace_all(prompts: List[str]):
    """Replace the entire queue with a new list (used by GUI save)."""
    _save(prompts)


def remove(index: int) -> bool:
    """Remove item at index. Returns True on success."""
    prompts = _load()
    if 0 <= index < len(prompts):
        prompts.pop(index)
        _save(prompts)
        return True
    return False


def count() -> int:
    """Return the number of queued prompts."""
    return len(_load())
