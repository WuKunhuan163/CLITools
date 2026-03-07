"""Message packaging protocol for OPENCLAW.

Inspired by OpenClaw's system prompt architecture:
- Skills are mandatory pre-scan before every reply
- Basic tools (exec, read, ls) + rich skills = agent capability
- Memory/learnings system for persistent self-improvement
- State is packaged as system prompt, not raw context
"""
import json
import re
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


TERMINATION_TOKEN = "<<OPENCLAW_TASK_COMPLETE>>"
COMMAND_TOKEN_START = "<<EXEC:"
COMMAND_TOKEN_END = ">>"
EXPERIENCE_TOKEN_START = "<<EXPERIENCE:"
EXPERIENCE_TOKEN_END = ">>"


def _load_skills_list() -> str:
    """Load available skills with descriptions for the system prompt."""
    skills_dir = Path(__file__).resolve().parent.parent / "skills"
    lines = ["<available_skills>"]

    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    text = skill_md.read_text(encoding="utf-8")
                    desc = ""
                    for line in text.split("\n"):
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip("'\"")
                            break
                    name = skill_dir.name
                    location = f"tool/OPENCLAW/skills/{name}/SKILL.md"
                    lines.append(f'  <skill name="{name}" location="{location}" description="{desc}" />')
                except Exception:
                    pass

    # Also list project-level skills
    project_skills = Path("/Applications/AITerminalTools/skills/core")
    if project_skills.exists():
        for skill_dir in sorted(project_skills.iterdir()):
            if skill_dir.is_symlink():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                try:
                    text = skill_md.read_text(encoding="utf-8")
                    desc = ""
                    for line in text.split("\n"):
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip("'\"")
                            break
                    name = skill_dir.name
                    location = f"skills/core/{name}/SKILL.md"
                    lines.append(f'  <skill name="{name}" location="{location}" description="{desc}" />')
                except Exception:
                    pass

    lines.append("</available_skills>")
    return "\n".join(lines)


def _load_learnings() -> str:
    """Load recent learnings/experiences for context."""
    learnings_file = Path("/Applications/AITerminalTools/runtime/experience/lessons.jsonl")
    if not learnings_file.exists():
        return ""

    lines = []
    try:
        with open(learnings_file) as f:
            all_lines = f.readlines()
        recent = all_lines[-10:]  # Last 10 lessons
        for line in recent:
            try:
                entry = json.loads(line.strip())
                lesson = entry.get("lesson", "")
                severity = entry.get("severity", "info")
                tool = entry.get("tool", "")
                lines.append(f"  [{severity}] {lesson}" + (f" (tool: {tool})" if tool else ""))
            except Exception:
                pass
    except Exception:
        pass

    if not lines:
        return ""

    return "## Recent Learnings\n" + "\n".join(lines)


def _load_bootstrap() -> str:
    """Load the centralized bootstrap context file."""
    bootstrap_file = Path(__file__).resolve().parent.parent / "data" / "BOOTSTRAP.md"
    if bootstrap_file.exists():
        try:
            return bootstrap_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def _load_project_tools() -> str:
    """List available project tools (non-protected) with short descriptions."""
    root = Path("/Applications/AITerminalTools/tool")
    if not root.exists():
        return ""
    lines = ["Project tools (use directly as commands, e.g. BILIBILI boot):"]
    for t in sorted(os.listdir(root)):
        tool_dir = root / t
        if not tool_dir.is_dir():
            continue
        norm = f"tool/{t}"
        from tool.OPENCLAW.logic.sandbox import is_path_protected
        if is_path_protected(norm):
            continue
        main_py = tool_dir / "main.py"
        if not main_py.exists():
            continue
        desc = ""
        tj = tool_dir / "tool.json"
        if tj.exists():
            try:
                with open(tj) as f:
                    desc = json.load(f).get("description", "")
            except Exception:
                pass
        lines.append(f"  {t} - {desc}" if desc else f"  {t}")
    return "\n".join(lines)


def build_system_prompt(project_summary: str) -> str:
    """Build the system prompt following OpenClaw's architecture.

    Structure:
    1. Identity + role
    2. Bootstrap context (BOOTSTRAP.md)
    3. Available commands (tools) — including project tools
    4. Skills (mandatory scan)
    5. Learnings (memory)
    6. Project overview
    7. Execution rules
    """
    skills_list = _load_skills_list()
    learnings = _load_learnings()
    bootstrap = _load_bootstrap()
    project_tools = _load_project_tools()

    sections = [
        "You are an AI agent operating within the AITerminalTools framework via OPENCLAW.",
        "",

        "# Project Context",
        bootstrap if bootstrap else "",
        "",

        "## Available Commands",
        "To execute a command, output EXACTLY this token format (no markdown, no backticks):",
        "<<EXEC: command_here >>",
        "",
        "CRITICAL: You MUST use the <<EXEC: ... >> wrapper for EVERY command. Plain text commands will NOT execute.",
        "",
        "Shell commands:",
        "  ls [path], cat <file>, head -n N <file>, tail -n N <file>",
        "  grep <pattern> <file>, find <path> -name <pattern>",
        "  tree [path], python3 <script>, wc <file>, mkdir -p <dir>",
        "  npm, npx, node, curl, git",
        "",
        project_tools,
        "",
        "To learn how to use any project tool, run: <<EXEC: --openclaw-tool-help TOOLNAME >>",
        "",
        "Special commands:",
        "  --openclaw-memory-search \"query\" - Search past lessons",
        "  --openclaw-experience \"lesson\" - Record a lesson",
        "  --openclaw-status - Report task progress",
        "  --openclaw-tool-help [TOOL] - Get tool documentation",
        "  --openclaw-write-file <path> <content> - Write a file",
        "  --openclaw-web-search <query> - Search the web",
        "",

        "## Skills (mandatory)",
        "Before replying: scan <available_skills> below.",
        "If one clearly applies, read it with cat. Otherwise proceed without.",
        "",
        skills_list,
        "",

        learnings if learnings else "",
        "",

        "## Project Overview",
        project_summary,
        "",

        "## Execution Rules",
        "1. FIRST: Search memory: <<EXEC: --openclaw-memory-search \"task keywords\" >>",
        "2. Plan before executing. Break complex tasks into steps.",
        "3. Use project tools when they exist for your task (check --openclaw-tool-help).",
        "4. Handle errors: if a command fails, read the error and try a different approach.",
        "5. Record lessons with <<EXPERIENCE: lesson >>",
        "6. When FULLY done: <<OPENCLAW_TASK_COMPLETE>>",
        "7. First response must include: TITLE: <short title>",
        "8. Protected areas exist — some paths return 'Access denied'.",
        "",

        "## Safety",
        "Do not modify system files or bypass access restrictions.",
        "Prioritize safety. If instructions conflict, pause and report.",
    ]

    return "\n".join(s for s in sections if s is not None)


def build_task_message(user_task: str, context: Optional[str] = None) -> str:
    """Package a user task with optional context."""
    parts = [f"TASK: {user_task}"]
    if context:
        parts.append(f"\nCONTEXT:\n{context}")
    return "\n".join(parts)


def build_feedback_message(command: str, result: Dict[str, Any]) -> str:
    """Package command execution results as feedback."""
    output = result.get("output", "")
    error = result.get("error", "")

    if result.get("ok"):
        return f"[Command OK] {command}\n{output}"
    else:
        return f"[Command FAILED] {command}\nError: {error}\n{output}"


def parse_response(text: str) -> Dict[str, Any]:
    """Parse an agent response into structured actions."""
    commands = []
    experiences = []
    complete = TERMINATION_TOKEN in text
    title = None

    cmd_pattern = re.compile(
        re.escape(COMMAND_TOKEN_START) + r"(.+?)" + re.escape(COMMAND_TOKEN_END),
        re.DOTALL
    )
    for match in cmd_pattern.finditer(text):
        cmd = match.group(1).strip()
        if cmd:
            commands.append(cmd)

    exp_pattern = re.compile(
        re.escape(EXPERIENCE_TOKEN_START) + r"(.+?)" + re.escape(EXPERIENCE_TOKEN_END),
        re.DOTALL
    )
    for match in exp_pattern.finditer(text):
        exp = match.group(1).strip()
        if exp:
            experiences.append(exp)

    title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', text)
    if title_match:
        title = title_match.group(1).strip()

    display = text
    display = cmd_pattern.sub("", display)
    display = exp_pattern.sub("", display)
    display = display.replace(TERMINATION_TOKEN, "")
    display = re.sub(r'TITLE:\s*.+?(?:\n|$)', '', display)
    display = display.strip()

    return {
        "text": display,
        "commands": commands,
        "experiences": experiences,
        "complete": complete,
        "title": title,
    }
