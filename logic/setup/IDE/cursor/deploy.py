"""Deploy Cursor IDE configuration from templates.

Called by setup.py when Cursor IDE is detected. Copies rule templates
and hooks configuration to .cursor/ in the project root.
"""
import shutil
from pathlib import Path


def detect_cursor_ide(project_root: Path) -> bool:
    from logic.setup.ide_detect import detect_cursor
    return detect_cursor(project_root)


def deploy(project_root: Path, force: bool = False) -> dict:
    """Deploy Cursor config templates. Returns {"deployed": [...], "skipped": [...]}."""
    template_dir = Path(__file__).parent
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
