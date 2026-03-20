"""AI IDE rule management.

Generates and injects rules for AI agents into IDE-specific configuration
directories (e.g., .cursor/rules/).
"""
import json
import sys
import subprocess
from pathlib import Path
from typing import Optional


def _load_tool_info(project_root: Path, name: str) -> dict:
    tj = project_root / "tool" / name / "tool.json"
    if tj.exists():
        try:
            with open(tj, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _get_tool_status(info: dict, project_root: Path, name: str) -> str:
    """Determine tool status from tool.json 'status' field or heuristics."""
    explicit = info.get("status")
    if explicit:
        return explicit
    if not (project_root / "tool" / name / "main.py").exists():
        return "available"
    return "installed"


def generate_ai_rule(project_root: Path, target_tool: Optional[str] = None, translation_func=None):
    """Generate and display the AI agent rule set.

    New format:
    - TOOL_NAME [status]
      Purpose: ...
      (additional description)
    """
    from logic._.config import get_color
    from logic._.utils import get_logic_dir
    from logic._.lang.utils import get_translation

    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    RESET = get_color("RESET", "\033[0m")

    if target_tool and target_tool.upper() != "TOOL":
        tool_dir = project_root / "tool" / target_tool.upper()
        if not tool_dir.exists():
            print(f"{get_color('BOLD')}{get_color('RED')}Error{RESET}: Tool '{target_tool}' not found.")
            return
        registry_path = tool_dir / "tool.json"
    else:
        registry_path = project_root / "tool.json"

    if not registry_path.exists():
        return

    with open(registry_path, 'r') as f:
        registry = json.load(f)

    if target_tool and target_tool.upper() != "TOOL":
        name = target_tool.upper()
        info = registry
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose'))
        usage = info.get("usage", [])
        status = _get_tool_status(info, project_root, name)

        print(f"- {BOLD}{name}{RESET} [{status}]")
        print(f"  Purpose: {purpose}")
        if desc:
            print(f"  {desc}")
        if usage:
            print(f"\n  Usage:")
            for line in usage:
                print(f"  - {line}")
        return

    tools_raw = registry.get("tools", [])
    if isinstance(tools_raw, list):
        all_tool_names = tools_raw
    else:
        all_tool_names = list(tools_raw.keys())

    installed_tools = [n for n in all_tool_names if (project_root / "tool" / n).exists()]
    available_tools = [n for n in all_tool_names if not (project_root / "tool" / n).exists()]

    lines = []

    for name in installed_tools:
        info = _load_tool_info(project_root, name)
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose', ''))
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description', ''))
        status = _get_tool_status(info, project_root, name)

        lines.append(f"- {name} [{status}]")
        lines.append(f"  Purpose: {purpose}")
        if desc and desc != name:
            lines.append(f"  {desc}")
        lines.append("")

    if available_tools:
        lines.append("[Available — run TOOL install <NAME>]")
        for name in available_tools:
            lines.append(f"- {name}")
        lines.append("")

    output = "\n".join(lines)
    print(output)
    if sys.platform == "darwin":
        try:
            subprocess.run('pbcopy', input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def generate_cursor_rule(project_root: Path, translation_func=None) -> str:
    """Generate the Cursor-specific rule content for injection.

    This adds IDE-specific context around the tool listing.
    """
    import io

    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    generate_ai_rule(project_root, translation_func=translation_func)
    tool_listing = buffer.getvalue()
    sys.stdout = old_stdout

    rule_text = f"""# CLITools
An integrated CLI tool ecosystem. Each tool is a standalone command available in your terminal.

## Tools

{tool_listing}
## Usage

- **Entry point**: `TOOL --help` (or any TOOL_NAME --help)
- The user expects you to develop using a **meta-agent** workflow: search ecosystem first, then act.
- After each development round, run `USERINPUT` to collect user feedback.

## Vision

The next phase is assistant system support: design, develop, and test the built-in assistant
framework that enables LLM-powered agents to use these tools autonomously.
"""
    return rule_text


def inject_rule(project_root: Path, translation_func=None):
    """Inject TOOL rule into the project's .cursor/rules/ directory as an always-apply rule."""
    from logic._.config import get_color

    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs) if kwargs else d)
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RESET = get_color("RESET", "\033[0m")

    rules_dir = project_root / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    rule_path = rules_dir / "AITerminalTools.mdc"

    rule_content = generate_cursor_rule(project_root, translation_func=translation_func)

    mdc_content = f"""---
description: CLITools ecosystem — integrated CLI tools for AI agents
globs: 
alwaysApply: true
---

{rule_content}
"""

    if rule_path.exists():
        with open(rule_path, 'r') as f:
            existing = f.read()
        if existing.strip() == mdc_content.strip():
            print(f"{BOLD}{YELLOW}Already up to date{RESET}: {rule_path}")
            return

    with open(rule_path, 'w') as f:
        f.write(mdc_content)

    print(f"{BOLD}{GREEN}Successfully injected{RESET} rule to {rule_path}.")
