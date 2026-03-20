"""Check pending migrations for CLI-Anything domain."""
import importlib.util
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TOOL_DIR = _PROJECT_ROOT / "tool"
_THIS_DIR = Path(__file__).resolve().parent


def _load_draft_tool():
    """Load draft_tool module from same directory without relative imports."""
    spec = importlib.util.spec_from_file_location(
        "cli_anything_draft_tool", str(_THIS_DIR / "draft_tool.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_pending():
    """Return pending and completed migrations."""
    dt = _load_draft_tool()
    available = dt.scan_available()
    if not available:
        return {
            "pending": [],
            "completed": [],
            "up_to_date": True,
            "total": 0,
            "migrated": 0,
            "error": "Could not scan upstream (no clone cache)",
        }

    pending = []
    completed = []
    for harness in available:
        tool_name = dt.harness_to_tool_name(harness)
        tool_path = _TOOL_DIR / tool_name
        upstream = tool_path / "data" / "upstream" / "CLI-Anything"
        if upstream.exists():
            info_file = upstream / "migration_info.json"
            status = "draft"
            if info_file.exists():
                try:
                    info = json.loads(info_file.read_text())
                    status = info.get("status", "draft")
                except Exception:
                    pass
            completed.append({"harness": harness, "tool": tool_name, "status": status})
        else:
            pending.append({"harness": harness, "tool": tool_name})

    return {
        "pending": pending,
        "completed": completed,
        "up_to_date": len(pending) == 0,
        "total": len(available),
        "migrated": len(completed),
    }
