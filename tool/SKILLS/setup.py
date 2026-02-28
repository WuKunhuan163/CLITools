#!/usr/bin/env python3
"""Post-installation setup for SKILLS tool. Syncs skills to Cursor."""
import sys
from pathlib import Path

def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    sys.path.insert(0, str(project_root))

def setup(**kwargs):
    library_dir = Path(__file__).resolve().parent / "data" / "library"
    cursor_dir = Path.home() / ".cursor" / "skills"
    cursor_dir.mkdir(parents=True, exist_ok=True)

    for skill_dir in library_dir.iterdir():
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
            continue
        target = cursor_dir / skill_dir.name
        if target.is_symlink():
            if target.resolve() == skill_dir.resolve():
                continue
            target.unlink()
        elif target.exists():
            continue
        target.symlink_to(skill_dir)

if __name__ == "__main__":
    setup()
