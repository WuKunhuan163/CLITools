"""Deploy IDE configuration from templates.

Handles deploying rule templates, hooks configuration, and other IDE-specific
files to the project's IDE configuration directory.
"""
import shutil
from pathlib import Path


def deploy_cursor(project_root: Path, force: bool = False) -> dict:
    """Deploy Cursor config templates. Returns {"deployed": [...], "skipped": [...]}."""
    template_dir = Path(__file__).parent / "cursor"
    result = {"deployed": [], "skipped": []}

    rules_src = template_dir / "rules"
    rules_dst = project_root / ".cursor" / "rules"
    if rules_src.is_dir():
        rules_dst.mkdir(parents=True, exist_ok=True)
        for src_file in sorted(rules_src.glob("*.mdc")):
            dst_file = rules_dst / src_file.name
            if force or not dst_file.exists() or src_file.stat().st_mtime > dst_file.stat().st_mtime:
                shutil.copy2(src_file, dst_file)
                result["deployed"].append(f".cursor/rules/{src_file.name}")
            else:
                result["skipped"].append(f".cursor/rules/{src_file.name}")

    hooks_src = template_dir / "hooks" / "hooks.json"
    hooks_dst = project_root / ".cursor" / "hooks.json"
    if hooks_src.exists():
        hooks_dst.parent.mkdir(parents=True, exist_ok=True)
        if force or not hooks_dst.exists() or hooks_src.stat().st_mtime > hooks_dst.stat().st_mtime:
            shutil.copy2(hooks_src, hooks_dst)
            result["deployed"].append(".cursor/hooks.json")
        else:
            result["skipped"].append(".cursor/hooks.json")

    return result


def list_rules(project_root: Path) -> list:
    """List all deployed Cursor rules in .cursor/rules/."""
    rules_dir = project_root / ".cursor" / "rules"
    if not rules_dir.is_dir():
        return []
    return sorted([f.stem for f in rules_dir.glob("*.mdc")])


def list_hooks(project_root: Path) -> list:
    """List registered hooks from .cursor/hooks.json."""
    import json
    hooks_file = project_root / ".cursor" / "hooks.json"
    if not hooks_file.exists():
        return []
    try:
        data = json.loads(hooks_file.read_text())
        hooks = data.get("hooks", [])
        return [{"event": h.get("event"), "command": h.get("command")} for h in hooks]
    except Exception:
        return []
