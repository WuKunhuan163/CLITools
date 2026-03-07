import json
import sys
import subprocess
from pathlib import Path
from typing import Optional

from logic.config import get_color
from logic.utils import get_logic_dir
from logic.lang.utils import get_translation

def generate_ai_rule(project_root: Path, target_tool: Optional[str] = None, translation_func = None):
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
        
    if not registry_path.exists(): return

    with open(registry_path, 'r') as f: registry = json.load(f)
    
    if target_tool and target_tool.upper() != "TOOL":
        name = target_tool.upper()
        info = registry
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose'))
        usage = info.get("usage", [])
        
        print(f"--- {BOLD}{name}{RESET} Rule ---")
        print(f"{BOLD}Description{RESET}: {desc}")
        print(f"{BOLD}Purpose{RESET}: {purpose}")
        if usage:
            print(f"\n{BOLD}Usage{RESET}:")
            for line in usage: print(f"- {line}")
        if name == "USERINPUT":
            ai_instr = get_translation(str(tool_logic_dir), "ai_instruction", "## Critical Directive: Feedback Acquisition\n...")
            print("\n" + ai_instr)
        print("--------------------------")
        return

    tools_raw = registry.get("tools", [])
    if isinstance(tools_raw, list):
        all_tool_names = tools_raw
    else:
        all_tool_names = list(tools_raw.keys())
    
    installed_tools = [n for n in all_tool_names if (project_root / "tool" / n).exists()]
    available_tools = [n for n in all_tool_names if not (project_root / "tool" / n).exists()]

    def _load_tool_info(name):
        tj = project_root / "tool" / name / "tool.json"
        if tj.exists():
            try:
                with open(tj, 'r') as f: return json.load(f)
            except Exception: pass
        return {}
            
    lines = []
    lines.append(_("rule_header_main", "--- AI AGENT TOOL RULES ---"))
    lines.append(_("rule_critical_note", "CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations."))
    lines.append("\n" + _("rule_installed_header", "[INSTALLED TOOLS - Use these directly]"))
    for name in installed_tools:
        info = _load_tool_info(name)
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description', name))
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose', ''))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_available_header", "[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]"))
    for name in available_tools:
        lines.append(f"- {name}")
        
    lines.append("\n" + _("rule_guidelines_header", "[LOCALIZATION & DEVELOPMENT GUIDELINES]"))
    lines.append("- " + _("rule_guideline_1", "**Multi-language Support**: Tools should support localization via a 'logic/translation/' directory."))
    lines.append("- " + _("rule_guideline_2", "**Fallback & Testing**: Always use the `_()` translation helper."))
    lines.append("- " + _("rule_guideline_3", "**Shared Logic**: Standardize utilities in root `logic/`."))
    lines.append("- " + _("rule_guideline_4", "**Dependency Management**: Define dependencies in 'tool.json'."))
    lines.append("- " + _("rule_guideline_7", "**Tool Structure**: main.py, setup.py, tool.json, README.md, logic/."))
    lines.append("- " + _("rule_guideline_6", "**Tool Creation**: Use 'TOOL dev create <NAME>'."))
    lines.append("- " + _("rule_guideline_5", "**Color & Status Style**: Bold labels, color unified status, Green (success), Blue (progress), Red (error), Yellow (warning)."))
    
    # Skills discovery section
    skills_dir = project_root / "tool" / "SKILLS" / "data" / "library"
    if skills_dir.exists():
        skill_names = sorted([d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
        if skill_names:
            lines.append("\n" + _("rule_skills_header", "[AVAILABLE SKILLS - Use 'SKILLS show <name>' to view]"))
            lines.append(_("rule_skills_note", "Skills provide detailed guides for development patterns. Read a skill before starting related work."))
            for sname in skill_names:
                lines.append(f"- {sname}")

    userinput_logic_dir = get_logic_dir(project_root / "tool" / "USERINPUT")
    ai_instr = get_translation(str(userinput_logic_dir), "ai_instruction", "## Critical Directive: Feedback Acquisition\n...")
    lines.append("\n" + ai_instr)
    lines.append("\n" + _("rule_note_execution", "NOTE: To use a tool, ensure its executable name (e.g., 'USERINPUT') is called directly in the terminal."))
    lines.append("--------------------------")
    
    output = "\n".join(lines)
    print(output)
    if sys.platform == "darwin":
        try: subprocess.run('pbcopy', input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
        except: pass


def inject_rule(project_root: Path, translation_func=None):
    """Inject TOOL rule into the project's .cursor/rules/ directory as an always-apply rule."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs) if kwargs else d)
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    rules_dir = project_root / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    rule_path = rules_dir / "AITerminalTools.mdc"

    import io
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    generate_ai_rule(project_root, translation_func=translation_func)
    rule_content = buffer.getvalue()
    sys.stdout = old_stdout

    mdc_content = f"""---
description: AITerminalTools framework rules for AI agents
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

