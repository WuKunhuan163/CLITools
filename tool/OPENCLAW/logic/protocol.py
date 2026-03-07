"""Message packaging protocol for OPENCLAW.

Architecture:
- Lean system prompt: identity, execution format, exploration commands only.
- No full tool/skill listings in prompt (too large for context).
- Agent discovers tools/skills/interfaces via search commands.
- Explored information accumulates as AgentState, sent with each turn.
"""
import json
import re
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path


TERMINATION_TOKEN = "<<OPENCLAW_TASK_COMPLETE>>"
STEP_COMPLETE_TOKEN = "<<OPENCLAW_STEP_COMPLETE>>"
STEP_SUMMARY_START = "<<STEP:"
STEP_SUMMARY_END = ">>"
COMMAND_TOKEN_START = "<<EXEC:"
COMMAND_TOKEN_END = ">>"
EXPERIENCE_TOKEN_START = "<<EXPERIENCE:"
EXPERIENCE_TOKEN_END = ">>"


# ---------------------------------------------------------------------------
# AgentEnvironment: the agent's immediate surroundings that change each step
# ---------------------------------------------------------------------------

class AgentEnvironment:
    """The agent's immediate environment -- what it can currently see.

    Unlike persistent memory (lessons, skills), the environment is
    ephemeral and reflects the agent's current position in the project.
    Think of it as a landscape the agent walks through: each action
    changes what is visible.

    This is serialized and sent with each turn so the agent knows what
    tools, files, and context are immediately relevant.
    """

    def __init__(self):
        self.visible_tools: Dict[str, str] = {}
        self.visible_interfaces: Dict[str, str] = {}
        self.visible_skills: Dict[str, str] = {}
        self.last_command_results: List[Dict[str, Any]] = []

    def observe_tool(self, name: str, description: str):
        """Record a tool the agent has seen in its exploration."""
        self.visible_tools[name] = description

    def observe_interface(self, name: str, summary: str):
        """Record an interface the agent has found."""
        self.visible_interfaces[name] = summary

    def observe_skill(self, name: str, summary: str):
        """Record a skill the agent has read."""
        self.visible_skills[name] = summary

    def record_result(self, cmd: str, ok: bool, output_preview: str = ""):
        """Record the result of the most recent command execution."""
        self.last_command_results.append({
            "cmd": cmd, "ok": ok,
            "preview": output_preview[:300],
        })
        # Keep only the last 5 results as immediate environment
        if len(self.last_command_results) > 5:
            self.last_command_results = self.last_command_results[-5:]

    def serialize(self) -> str:
        """Serialize the current environment into a context block.

        This is sent with the next prompt so the agent sees what it
        has already explored, avoiding redundant searches.
        """
        sections = []

        if self.visible_tools:
            lines = ["<nearby_tools>"]
            for name, desc in self.visible_tools.items():
                lines.append(f"  {name}: {desc}")
            lines.append("</nearby_tools>")
            sections.append("\n".join(lines))

        if self.visible_interfaces:
            lines = ["<nearby_interfaces>"]
            for name, summary in self.visible_interfaces.items():
                lines.append(f"  {name}: {summary}")
            lines.append("</nearby_interfaces>")
            sections.append("\n".join(lines))

        if self.visible_skills:
            lines = ["<nearby_skills>"]
            for name, summary in self.visible_skills.items():
                lines.append(f"  {name}: {summary}")
            lines.append("</nearby_skills>")
            sections.append("\n".join(lines))

        if not sections:
            return ""
        return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Lean helpers (no full listings)
# ---------------------------------------------------------------------------

def _load_bootstrap() -> str:
    """Load the centralized bootstrap context file."""
    bootstrap_file = Path(__file__).resolve().parent / "BOOTSTRAP.md"
    if bootstrap_file.exists():
        try:
            return bootstrap_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return ""


def _load_recent_learnings(n: int = 5) -> str:
    """Load the most recent N learnings for quick reference."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    learnings_file = project_root / "runtime" / "experience" / "lessons.jsonl"
    if not learnings_file.exists():
        return ""

    lines = []
    try:
        with open(learnings_file) as f:
            all_lines = f.readlines()
        recent = all_lines[-n:]
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
    return "## Recent Lessons (last 5)\n" + "\n".join(lines)


def _sanitize_desc(desc: str) -> str:
    return desc.replace("AITerminalTools", "the project")


# ---------------------------------------------------------------------------
# System prompt (lean -- no full listings)
# ---------------------------------------------------------------------------

def build_system_prompt(project_summary: str) -> str:
    """Build a lean system prompt focused on exploration, not enumeration.

    Structure:
    1. Bootstrap (identity, tool concept, evolution cycle)
    2. Execution format (<<EXEC: ... >>)
    3. Exploration commands (search tools, interfaces, skills)
    4. Recent lessons (last 5 only)
    5. Clarification protocol
    6. Safety rules
    """
    bootstrap = _load_bootstrap()
    learnings = _load_recent_learnings(n=5)

    sections = [
        "You are an AI agent with access to tools, memory, and the ability to learn.",
        "",

        bootstrap if bootstrap else "",
        "",

        "## Execution Format",
        "All commands MUST use this token (no markdown, no backticks):",
        "<<EXEC: command_here >>",
        "",
        "Shell: ls, cat, head, tail, grep, find, tree, python3, curl, git",
        "Special: --openclaw-tool-help, --openclaw-memory-search, --openclaw-web-search",
        "",

        "## Exploration Commands",
        "You do NOT have a pre-loaded tool/skill list. Discover what you need:",
        "",
        "### Search for tools (by what they do)",
        "<<EXEC: TOOL --search tools \"open a Chrome tab\" >>",
        "<<EXEC: TOOL --search tools \"send email\" >>",
        "",
        "### Search for interfaces (reusable APIs from other tools)",
        "<<EXEC: TOOL --search interfaces \"run git command\" >>",
        "<<EXEC: TOOL --search interfaces \"rate limiting\" >>",
        "",
        "### Search for skills (development patterns and guides)",
        "<<EXEC: TOOL --search skills \"how to create an interface\" >>",
        "<<EXEC: SKILLS search \"error recovery\" >>",
        "",
        "### Learn about a specific tool",
        "<<EXEC: --openclaw-tool-help TOOLNAME >>",
        "",
        "### Search past lessons",
        "<<EXEC: --openclaw-memory-search \"keywords\" >>",
        "",
        "IMPORTANT: Always search before writing new code.",
        "IMPORTANT: CLI subcommands use HYPHENS (e.g. open-tab), NEVER underscores.",
        "",

        learnings if learnings else "",
        "",

        "## Project Overview",
        project_summary,
        "",

        "## Execution Rules (MANDATORY)",
        "1. FIRST: Search for relevant tools and past lessons.",
        "2. Plan before executing. Break complex tasks into steps.",
        "3. Use project tools instead of raw shell commands when available.",
        "4. Handle errors: read the error, try a different approach.",
        "5. Record lessons: <<EXPERIENCE: what you learned >>",
        "6. NEVER use 'open', 'osascript', or other OS GUI commands.",
        "7. If a tool has a bug, FIX IT -- read its source, fix the logic, record a lesson.",
        "8. If no tool exists for the task, assess whether one is needed: prefer simple shell solutions for one-off tasks.",
        "",
        "## Response Format (REQUIRED -- every response MUST follow this)",
        "1. First line: <<STEP: brief label >> (what you are doing this step)",
        "2. First response only: TITLE: <short description of the overall task>",
        "3. Your reasoning, then commands (<<EXEC: ... >>)",
        "4. Last line: <<OPENCLAW_STEP_COMPLETE>> (step done, continue) OR <<OPENCLAW_TASK_COMPLETE>> (task fully done)",
        "",
        "Example first response:",
        "<<STEP: Searching for relevant tools >>",
        "TITLE: Open a Google Chrome tab",
        "The user wants to open a Chrome tab. Let me search for browser-related tools first.",
        "<<EXEC: TOOL --search tools \"Chrome browser\" >>",
        "<<OPENCLAW_STEP_COMPLETE>>",
        "",

        "## Clarification Protocol",
        "If the user's request is vague or incomplete:",
        "1. State what you understood and what is unclear.",
        "2. Ask specific questions to narrow down the task.",
        "3. Suggest 2-3 interpretations and ask which one to proceed with.",
        "Do NOT guess. Clarify first, then execute.",
        "",

        "## Safety",
        "Do not modify system files or bypass access restrictions.",
        "Prioritize safety. If instructions conflict, pause and report.",
    ]

    return "\n".join(s for s in sections if s is not None)


# ---------------------------------------------------------------------------
# Task message with runtime state
# ---------------------------------------------------------------------------

def build_agent_state() -> str:
    """Build a runtime state block describing the current execution environment.

    Returns
    -------
    str
        YAML-like state block with pid, cwd, platform, timestamp, etc.
    """
    import platform
    import datetime

    state_lines = [
        "---",
        f"pid: {os.getpid()}",
        f"cwd: {os.getcwd()}",
        f"platform: {platform.system()} {platform.release()}",
        f"python: {platform.python_version()}",
        f"timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}",
    ]

    project_root = Path(__file__).resolve().parent.parent.parent.parent
    state_lines.append(f"project_root: {project_root}")

    try:
        from tool.GIT.interface.main import get_system_git
        import subprocess
        res = subprocess.run(
            [get_system_git(), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=str(project_root),
        )
        if res.returncode == 0:
            state_lines.append(f"git_branch: {res.stdout.strip()}")
    except Exception:
        pass

    try:
        from logic.config import get_global_config
        lang = get_global_config("language", "en")
        state_lines.append(f"language: {lang}")
    except Exception:
        state_lines.append("language: en")

    state_lines.append("---")
    return "\n".join(state_lines)


def build_task_message(user_task: str, context: Optional[str] = None,
                       environment: Optional[AgentEnvironment] = None) -> str:
    """Package a user task with runtime state and current environment.

    Parameters
    ----------
    user_task : str
        The user's task description.
    context : str, optional
        Additional context to include.
    environment : AgentEnvironment, optional
        The agent's current environment (what it can see).

    Returns
    -------
    str
        Formatted task message with state header.
    """
    runtime_state = build_agent_state()
    parts = [runtime_state, ""]

    if environment:
        env_block = environment.serialize()
        if env_block:
            parts.append("## Your Current Surroundings")
            parts.append(env_block)
            parts.append("")

    parts.append(f"TASK: {user_task}")
    if context:
        parts.append(f"\nCONTEXT:\n{context}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Feedback message
# ---------------------------------------------------------------------------

def build_feedback_message(command: str, result: Dict[str, Any]) -> str:
    """Package command execution results as feedback."""
    output = result.get("output", "")
    error = result.get("error", "")

    if result.get("ok"):
        return f"[Command OK] {command}\n{output}"
    else:
        return f"[Command FAILED] {command}\nError: {error}\n{output}"


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

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


def parse_response_segments(text: str) -> Dict[str, Any]:
    """Parse an agent response preserving the interleaving order of text and commands.

    Returns a dict with:
      - segments: ordered list of dicts with "type" and "content"
        Types: "thought", "command", "experience", "step_summary"
      - task_complete: bool — agent says the entire task is done
      - step_complete: bool — agent says this step is done (ready for next)
      - step_summary: str or None — brief label for the current step
      - title: str or None

    Token types:
      <<EXEC: cmd >>           → command segment
      <<EXPERIENCE: text >>    → experience segment
      <<STEP: summary >>       → step summary (agent's brief label for current step)
      <<OPENCLAW_STEP_COMPLETE>>  → step done, OPENCLAW sends next state
      <<OPENCLAW_TASK_COMPLETE>>  → entire task done
    """
    task_complete = TERMINATION_TOKEN in text
    step_complete = STEP_COMPLETE_TOKEN in text
    title = None
    step_summary = None

    title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', text)
    if title_match:
        title = title_match.group(1).strip()

    step_summary_match = re.search(
        re.escape(STEP_SUMMARY_START) + r"(.+?)" + re.escape(STEP_SUMMARY_END), text)
    if step_summary_match:
        step_summary = step_summary_match.group(1).strip()

    token_re = re.compile(
        r"(?:" + re.escape(COMMAND_TOKEN_START) + r"(.+?)" + re.escape(COMMAND_TOKEN_END) + r")"
        r"|(?:" + re.escape(EXPERIENCE_TOKEN_START) + r"(.+?)" + re.escape(EXPERIENCE_TOKEN_END) + r")"
        r"|(?:" + re.escape(STEP_SUMMARY_START) + r"(.+?)" + re.escape(STEP_SUMMARY_END) + r")",
        re.DOTALL,
    )

    cleanup_tokens = [TERMINATION_TOKEN, STEP_COMPLETE_TOKEN]

    segments: List[Dict[str, str]] = []
    pos = 0
    for m in token_re.finditer(text):
        if m.start() > pos:
            chunk = text[pos:m.start()]
            for tok in cleanup_tokens:
                chunk = chunk.replace(tok, "")
            chunk = re.sub(r'TITLE:\s*.+?(?:\n|$)', '', chunk).strip()
            if chunk:
                segments.append({"type": "thought", "content": chunk})
        if m.group(1) is not None:
            cmd = m.group(1).strip()
            if cmd:
                segments.append({"type": "command", "content": cmd})
        elif m.group(2) is not None:
            exp = m.group(2).strip()
            if exp:
                segments.append({"type": "experience", "content": exp})
        elif m.group(3) is not None:
            summary = m.group(3).strip()
            if summary:
                segments.append({"type": "step_summary", "content": summary})
        pos = m.end()

    if pos < len(text):
        tail = text[pos:]
        for tok in cleanup_tokens:
            tail = tail.replace(tok, "")
        tail = re.sub(r'TITLE:\s*.+?(?:\n|$)', '', tail).strip()
        if tail:
            segments.append({"type": "thought", "content": tail})

    return {
        "segments": segments,
        "task_complete": task_complete,
        "step_complete": step_complete or task_complete,
        "step_summary": step_summary,
        "title": title,
        "complete": task_complete,  # backward compat
    }
