"""Message packaging protocol for OPENCLAW.

Architecture:
- Structured tool calls via OpenAI-compatible function calling.
- Text content for user-facing explanations (may contain TITLE).
- No text-based tool tokens — all tool invocations are structured JSON.
- Explored information accumulates as AgentState, sent with each turn.
"""
import json
import re
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


TERMINATION_TOKEN = "<<OPENCLAW_TASK_COMPLETE>>"


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
    2. Structured tool call format (OpenAI function calling)
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

        "## Exploration Commands",
        "You do NOT have a pre-loaded tool/skill list. Discover via structured tool calls:",
        "",
        "Search for tools: exec(command='TOOL --search tools \"what you need\"')",
        "Search for interfaces: exec(command='TOOL --search interfaces \"what you need\"')",
        "Search for skills: exec(command='TOOL --search skills \"pattern\"')",
        "Learn a tool: exec(command='--openclaw-tool-help TOOLNAME')",
        "Search lessons: exec(command='--openclaw-memory-search \"keywords\"')",
        "",
        "IMPORTANT: Always search before writing new code.",
        "IMPORTANT: CLI subcommands use HYPHENS (e.g. open-tab), NEVER underscores.",
        "",

        "## Task Management",
        "Use the TODO tool (via structured todo() calls or exec):",
        "todo(action='add', content='description')",
        "todo(action='list')",
        "todo(action='complete', id='ITEM_ID')",
        "",

        learnings if learnings else "",
        "",

        "## Project Overview",
        project_summary,
        "",

        "## Continuous Improvement",
        "Periodically audit skills for infrastructure conversion potential:",
        "- If a skill describes a reusable pattern (retry, preflight, cleanup), check if logic/utils/ already has it.",
        "- If a skill's code examples are frequently copied, extract them into a utility function.",
        "- Run TOOL audit code periodically to check for dead code and unused imports.",
        "- Use TOOL --search skills \"keyword\" to find relevant patterns before writing new code.",
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
        "## Response Format (REQUIRED)",
        "",
        "Tools are invoked via structured function calls (OpenAI format).",
        "Text and tool calls occupy separate API response fields.",
        "",
        "Available tools:",
        "  exec(command)                 -- run a shell/tool command",
        "  read(path, start_line?, end_line?) -- read a file",
        "  grep(pattern, path?, include?) -- search for a pattern",
        "  search(query, scope?)         -- semantic search",
        "  todo(action, id?, content?)   -- manage task list",
        "  experience(lesson, severity?, tool?) -- record a lesson",
        "",
        "Text content is user-facing explanation. Include TITLE: on first response.",
        "<<OPENCLAW_TASK_COMPLETE>> in text when the task is done.",
        "",
        "CRITICAL RULE: After any blocking tool (exec, read, grep, search, todo),",
        "STOP immediately. Do not output more text. Wait for the result.",
        "",
        "Example:",
        "Text: 'Searching for Chrome-related tools.'",
        "Tool: exec(command='TOOL --search tools Chrome')",
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
        from interface.config import get_global_config
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
# Response parser (structured tool calls only)
# ---------------------------------------------------------------------------


def parse_structured_tool_calls(text: str,
                                tool_calls: List[Dict[str, Any]]
                                ) -> Dict[str, Any]:
    """Parse an LLM response with structured tool calls into segments.

    The LLM returns structured JSON tool calls via the ``tools`` parameter.
    This function converts them into a unified segment format for the pipeline.

    Args:
        text: Any accompanying text content from the response.
        tool_calls: List of OpenAI-format tool call dicts, each with
            ``{"id": str, "type": "function",
              "function": {"name": str, "arguments": str}}``.

    Returns:
        Same dict format as ``parse_response_segments``.
    """
    from tool.OPENCLAW.logic.tool_schemas import (
        BLOCKING_TOOL_NAMES, NON_BLOCKING_TOOL_NAMES)

    segments: List[Dict[str, Any]] = []

    if text and text.strip():
        segments.append({"type": "thought", "content": text.strip()})

    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "").lower()
        try:
            args = json.loads(func.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            args = {}

        tc_id = tc.get("id", "")

        if name in BLOCKING_TOOL_NAMES:
            if name == "exec":
                cmd = args.get("command", "")
            elif name == "read":
                cmd = args.get("path", "")
                if args.get("start_line"):
                    cmd += f" (lines {args['start_line']}"
                    cmd += f"-{args.get('end_line', 'EOF')})"
            elif name == "grep":
                cmd = f"{args.get('pattern', '')} {args.get('path', '.')}"
                if args.get("include"):
                    cmd += f" --include={args['include']}"
            elif name == "search":
                cmd = args.get("query", "")
                if args.get("scope"):
                    cmd += f" (in {args['scope']})"
            elif name == "todo":
                action = args.get("action", "list")
                cmd = f"todo {action}"
                if args.get("id"):
                    cmd += f" #{args['id']}"
                if args.get("content"):
                    cmd += f": {args['content']}"
            else:
                cmd = json.dumps(args)

            segments.append({
                "type": "command",
                "content": cmd,
                "tool_name": name,
                "tool_args": args,
                "tool_call_id": tc_id,
            })
        elif name in NON_BLOCKING_TOOL_NAMES:
            if name == "experience":
                lesson = args.get("lesson", "")
                segments.append({
                    "type": "experience",
                    "content": lesson,
                    "tool_name": name,
                    "tool_args": args,
                    "tool_call_id": tc_id,
                })
        else:
            segments.append({
                "type": "command",
                "content": json.dumps(args),
                "tool_name": name,
                "tool_args": args,
                "tool_call_id": tc_id,
            })

    task_complete = False
    title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', text or "")
    title = title_match.group(1).strip() if title_match else None

    return {
        "segments": segments,
        "task_complete": task_complete,
        "step_complete": False,
        "step_summary": None,
        "title": title,
        "complete": task_complete,
        "structured": True,
    }
