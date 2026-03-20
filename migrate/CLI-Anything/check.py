"""Check pending migrations for CLI-Anything domain."""
import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_TOOL_DIR = _PROJECT_ROOT / "tool"
_INFO = Path(__file__).resolve().parent / "info.json"

NAME_MAP = {
    "audacity": "AUDACITY",
    "blender": "BLENDER",
    "comfyui": "COMFYUI",
    "drawio": "DRAWIO",
    "gimp": "GIMP.CLI",
    "inkscape": "INKSCAPE",
    "kdenlive": "KDENLIVE",
    "libreoffice": "LIBREOFFICE",
    "mermaid": "MERMAID",
    "obs-studio": "OBS",
    "shotcut": "SHOTCUT",
    "zoom": "ZOOM.CLI",
    "anygen": "ANYGEN",
}


def check_pending():
    """Return pending and completed migrations."""
    pending = []
    completed = []
    for harness, tool_name in NAME_MAP.items():
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
        "total": len(NAME_MAP),
        "migrated": len(completed),
    }
