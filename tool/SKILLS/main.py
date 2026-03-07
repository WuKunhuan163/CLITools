#!/usr/bin/env python3 -u
import sys
import os
import argparse
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
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
else:
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.interface.tool import ToolBase
from logic.interface.config import get_color

CURSOR_SKILLS_DIR = Path.home() / ".cursor" / "skills"
LIBRARY_DIR = Path(__file__).resolve().parent / "logic" / "library"
PROJECT_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


def _collect_skills_from(directory):
    """Return list of (name, description) for all skills in a directory."""
    skills = []
    if not directory.exists():
        return skills
    for skill_dir in sorted(directory.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if skill_dir.is_dir() and skill_file.exists():
            desc = _parse_description(skill_file)
            skills.append((skill_dir.name, desc))
    return skills


def get_skills():
    """Return list of (name, description) for all skills across all sources."""
    skills = _collect_skills_from(LIBRARY_DIR)
    skills.extend(_collect_skills_from(PROJECT_SKILLS_DIR))
    return sorted(skills, key=lambda x: x[0])


def _parse_description(skill_file: Path) -> str:
    """Extract description from SKILL.md YAML frontmatter."""
    in_frontmatter = False
    for line in skill_file.read_text().splitlines():
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter and line.startswith("description:"):
            return line[len("description:"):].strip()
    return ""


def sync_skills():
    """Create symlinks from ~/.cursor/skills/ to project skills only.
    
    Library skills (100 general CS topics) are NOT synced to Cursor
    to avoid excessive context. Use 'SKILLS show <name>' to read them.
    """
    CURSOR_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    synced = 0
    for source_dir in [PROJECT_SKILLS_DIR]:
        if not source_dir.exists():
            continue
        for skill_dir in source_dir.iterdir():
            if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").exists():
                continue
            target = CURSOR_SKILLS_DIR / skill_dir.name
            if target.is_symlink():
                if target.resolve() == skill_dir.resolve():
                    synced += 1
                    continue
                target.unlink()
            elif target.exists():
                continue
            target.symlink_to(skill_dir)
            synced += 1
    return synced


def main():
    tool = ToolBase("SKILLS")

    parser = argparse.ArgumentParser(description="Manage AI Agent Skills", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    subparsers.add_parser("list", help="List all available skills")
    show_p = subparsers.add_parser("show", help="Show a skill's content")
    show_p.add_argument("name", help="Skill name")
    subparsers.add_parser("sync", help="Sync skills to Cursor's skills directory")
    subparsers.add_parser("path", help="Show skills library path")

    if tool.handle_command_line(parser):
        return
    args, _ = parser.parse_known_args()

    BOLD = get_color("BOLD")
    RED = get_color("RED")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    if args.command == "list":
        skills = get_skills()
        if not skills:
            print("No skills found.")
            return
        for name, desc in skills:
            linked = (CURSOR_SKILLS_DIR / name).is_symlink()
            status = f"{GREEN}linked{RESET}" if linked else f"{RED}not linked{RESET}"
            print(f"  {BOLD}{name}{RESET}  [{status}]")
            if desc:
                print(f"    {desc}")
        return

    if args.command == "show":
        skill_file = LIBRARY_DIR / args.name / "SKILL.md"
        if not skill_file.exists():
            skill_file = PROJECT_SKILLS_DIR / args.name / "SKILL.md"
        if not skill_file.exists():
            print(f"{BOLD}{RED}Error{RESET}: Skill '{args.name}' not found.")
            return
        print(skill_file.read_text())
        return

    if args.command == "sync":
        count = sync_skills()
        print(f"{BOLD}{GREEN}Synced{RESET} {count} skill(s) to {CURSOR_SKILLS_DIR}/")
        return

    if args.command == "path":
        print(str(LIBRARY_DIR))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
