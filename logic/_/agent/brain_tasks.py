"""JSON-backed brain task manager with numeric IDs.

Stores tasks in data/_/runtime/_/eco/brain/tasks.json and renders a human-readable
tasks.md for agents to scan. Supports add, complete, clear, list, and
bulk operations via a simple API and CLI commands.

Task schema:
    {
        "id": 1,
        "content": "Fix the backup error",
        "status": "pending",    # pending | in_progress | done | verify_pending
        "created": "2026-03-10T14:00:00",
        "updated": "2026-03-10T14:30:00",
        "notes": ""
    }
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

STATUS_ORDER = ["in_progress", "verify_pending", "pending", "done"]


def _tasks_json(project_root: str) -> Path:
    return Path(project_root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "tasks.json"


def _tasks_md(project_root: str) -> Path:
    return Path(project_root) / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "tasks.md"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load(project_root: str) -> List[Dict]:
    p = _tasks_json(project_root)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(project_root: str, tasks: List[Dict]):
    p = _tasks_json(project_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    _render_md(project_root, tasks)


def _next_id(tasks: List[Dict]) -> int:
    if not tasks:
        return 1
    return max(t["id"] for t in tasks) + 1


def _render_md(project_root: str, tasks: List[Dict]):
    """Render tasks.json into a human-readable tasks.md for agent scanning."""
    lines = ["# Active Tasks", ""]

    active = [t for t in tasks if t["status"] != "done"]
    done = [t for t in tasks if t["status"] == "done"]

    active.sort(key=lambda t: STATUS_ORDER.index(t["status"])
                if t["status"] in STATUS_ORDER else 99)

    if not active and not done:
        lines.append("No active tasks.")
    else:
        for t in active:
            status_map = {
                "in_progress": "[ ] **IN_PROGRESS**",
                "pending": "[ ]",
                "verify_pending": "[ ] **VERIFY_PENDING**",
            }
            prefix = status_map.get(t["status"], "[ ]")
            lines.append(f"- {prefix} #{t['id']}: {t['content']}")
            if t.get("notes"):
                lines.append(f"  - Notes: {t['notes']}")

        if done:
            lines.append("")
            recent_done = done[-5:]
            for t in recent_done:
                lines.append(f"- [x] #{t['id']}: {t['content']}")

    lines.append("")
    _tasks_md(project_root).write_text("\n".join(lines), encoding="utf-8")


# ── Public API ──────────────────────────────────────────────

def add_task(project_root: str, content: str, status: str = "pending",
             notes: str = "") -> Dict:
    tasks = _load(project_root)
    task = {
        "id": _next_id(tasks),
        "content": content,
        "status": status,
        "created": _now(),
        "updated": _now(),
        "notes": notes,
    }
    tasks.append(task)
    _save(project_root, tasks)
    return task


def update_task(project_root: str, task_id: int,
                status: Optional[str] = None,
                content: Optional[str] = None,
                notes: Optional[str] = None) -> Optional[Dict]:
    tasks = _load(project_root)
    for t in tasks:
        if t["id"] == task_id:
            if status is not None:
                t["status"] = status
            if content is not None:
                t["content"] = content
            if notes is not None:
                t["notes"] = notes
            t["updated"] = _now()
            _save(project_root, tasks)
            return t
    return None


def complete_task(project_root: str, task_id: int) -> Optional[Dict]:
    return update_task(project_root, task_id, status="done")


def delete_task(project_root: str, task_id: int) -> bool:
    tasks = _load(project_root)
    before = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    if len(tasks) == before:
        return False
    _save(project_root, tasks)
    return True


def clear_done(project_root: str) -> int:
    """Remove all done tasks. Returns count removed."""
    tasks = _load(project_root)
    before = len(tasks)
    tasks = [t for t in tasks if t["status"] != "done"]
    _save(project_root, tasks)
    return before - len(tasks)


def clear_all(project_root: str) -> int:
    """Remove all tasks. Returns count removed."""
    tasks = _load(project_root)
    count = len(tasks)
    _save(project_root, [])
    return count


def list_tasks(project_root: str, status: Optional[str] = None) -> List[Dict]:
    tasks = _load(project_root)
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    return tasks


def migrate_from_md(project_root: str) -> int:
    """One-time migration: parse existing tasks.md into tasks.json."""
    md_path = _tasks_md(project_root)
    if not md_path.exists():
        return 0

    json_path = _tasks_json(project_root)
    if json_path.exists():
        existing = _load(project_root)
        if existing:
            return 0

    import re
    content = md_path.read_text(encoding="utf-8")
    tasks = []
    next_id = 1
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r'^-\s+\[([ xX])\]\s*(.*)', line)
        if not m:
            continue
        checked = m.group(1).lower() == "x"
        text = m.group(2).strip()

        text = re.sub(r'^\*\*\w+\*\*\s*', '', text)
        text = re.sub(r'^#\d+:\s*', '', text)

        if not text:
            continue

        tasks.append({
            "id": next_id,
            "content": text,
            "status": "done" if checked else "pending",
            "created": _now(),
            "updated": _now(),
            "notes": "",
        })
        next_id += 1

    if tasks:
        _save(project_root, tasks)
    return len(tasks)
