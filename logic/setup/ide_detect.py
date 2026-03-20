"""AI IDE detection utilities.

Detects which AI-powered IDE the project is being used in, enabling
automatic configuration of hooks, rules, and skills at setup time.

Supported IDEs:
- Cursor (hooks.json, .cursor/rules/*.mdc)
- VS Code + GitHub Copilot (future: .vscode/ config)
- Windsurf (future: .windsurf/ config)
"""
import os
from pathlib import Path
from typing import List


def detect_cursor(project_root: Path) -> bool:
    if os.environ.get("CURSOR_VERSION"):
        return True
    if (Path.home() / ".cursor").is_dir():
        return True
    if (project_root / ".cursor").is_dir():
        return True
    return False


def detect_vscode(project_root: Path) -> bool:
    if os.environ.get("VSCODE_PID") or os.environ.get("TERM_PROGRAM") == "vscode":
        return True
    if (Path.home() / ".vscode").is_dir():
        return True
    if (project_root / ".vscode").is_dir():
        return True
    return False


def detect_windsurf(project_root: Path) -> bool:
    if os.environ.get("WINDSURF_VERSION"):
        return True
    home = Path.home()
    for name in (".windsurf", ".codeium"):
        if (home / name).is_dir():
            return True
    if (project_root / ".windsurf").is_dir():
        return True
    return False


def detect_all(project_root: Path) -> List[str]:
    """Return list of detected AI IDEs (e.g., ['cursor', 'vscode'])."""
    detected = []
    if detect_cursor(project_root):
        detected.append("cursor")
    if detect_vscode(project_root):
        detected.append("vscode")
    if detect_windsurf(project_root):
        detected.append("windsurf")
    return detected
