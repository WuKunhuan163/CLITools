"""
IDE Tool Interface

Cross-tool API for IDE detection, configuration deployment, rule management,
and hook orchestration. Other tools access this via:
    from interface import get_interface
    iface = get_interface("IDE")

Or directly:
    from tool.IDE.interface.main import detect_ides, deploy_cursor, inject_rule
"""
from pathlib import Path
from typing import List, Optional


def get_info():
    """Return basic tool info dict."""
    return {"name": "IDE", "version": "2.0.0"}


def detect_ides(project_root: Path) -> List[str]:
    """Return list of detected AI IDEs (e.g., ['cursor', 'vscode'])."""
    from tool.IDE.logic.detect import detect_all
    return detect_all(project_root)


def detect_cursor(project_root: Path) -> bool:
    """Check if Cursor IDE is detected."""
    from tool.IDE.logic.detect import detect_cursor as _detect
    return _detect(project_root)


def deploy_cursor(project_root: Path, force: bool = False) -> dict:
    """Deploy Cursor rules and hooks templates. Returns deployment summary."""
    from tool.IDE.logic.setup.deploy import deploy_cursor as _deploy
    return _deploy(project_root, force=force)


def list_cursor_rules(project_root: Path) -> list:
    """List all deployed Cursor rules."""
    from tool.IDE.logic.setup.deploy import list_rules
    return list_rules(project_root)


def list_cursor_hooks(project_root: Path) -> list:
    """List registered Cursor hooks."""
    from tool.IDE.logic.setup.deploy import list_hooks
    return list_hooks(project_root)


def generate_ai_rule(project_root: Path, target_tool: Optional[str] = None,
                     translation_func=None):
    """Generate and display the AI agent rule set."""
    from tool.IDE.logic.rule import generate_ai_rule as _gen
    _gen(project_root, target_tool=target_tool, translation_func=translation_func)


def inject_rule(project_root: Path, translation_func=None):
    """Inject TOOL rule into .cursor/rules/ as an always-apply rule."""
    from tool.IDE.logic.rule import inject_rule as _inject
    _inject(project_root, translation_func=translation_func)
