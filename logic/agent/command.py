"""Agent command handler — implements --agent/--ask/--plan subcommands.

Subcommands:
    prompt "..."              Start a new session and send initial prompt
    feed <SID> <CMD>          Send a follow-up command to an existing session
    status [SID]              Show session status
    sessions                  List all sessions
    setup                     Configure LLM API keys
    export <SID>              Export session + memory to archive
    import <archive> [brain]  Import session from archive
    brain [list|init|show]    Manage brain types
"""
import json
import os
import sys
import time
from typing import Optional

from logic.agent.state import (
    AgentSession, save_session, load_session, list_sessions,
)


def handle_agent_command(args: list, tool_name: str, project_root: str,
                         tool_dir: str = "", mode: str = "agent"):
    """Dispatch --agent/--ask/--plan subcommands.

    Args:
        args: Arguments after the flag.
        tool_name: Name of the invoking tool.
        project_root: Absolute path to project root.
        tool_dir: Absolute path to the tool directory (used as codebase_root).
        mode: "agent" (full), "ask" (read-only), or "plan" (read-only + no scripts).
    """
    if not args:
        _print_help(tool_name, mode)
        return

    subcmd = args[0]
    rest = args[1:]

    if subcmd == "prompt":
        _handle_prompt(rest, tool_name, project_root, tool_dir, mode=mode)
    elif subcmd == "feed":
        _handle_feed(rest, tool_name, project_root, tool_dir, mode=mode)
    elif subcmd == "status":
        _handle_status(rest, project_root)
    elif subcmd == "sessions":
        _handle_sessions(project_root)
    elif subcmd == "setup":
        _handle_setup(project_root)
    elif subcmd == "export":
        _handle_export(rest, project_root)
    elif subcmd == "import":
        _handle_import(rest, project_root)
    elif subcmd == "brain":
        _handle_brain(rest, project_root)
    else:
        print(f"Unknown subcommand: {subcmd}")
        _print_help(tool_name, mode)


MODE_LABELS = {"agent": "Agent", "ask": "Ask", "plan": "Plan"}


def _print_help(tool_name: str, mode: str = "agent"):
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")
    label = MODE_LABELS.get(mode, "Agent")
    flag = f"--{mode}"
    readonly_note = ""
    if mode in ("ask", "plan"):
        readonly_note = f"\n  {DIM}Read-only mode: write_file, edit_file disabled. exec restricted.{RESET}"
    print(f"""
{BOLD}{label} Mode{RESET} for {tool_name}{readonly_note}

Usage:
  {tool_name} {flag} prompt "Your task description"
  {tool_name} {flag} feed <SESSION_ID> "Follow-up instruction"
  {tool_name} {flag} status [SESSION_ID]
  {tool_name} {flag} sessions
  {tool_name} {flag} setup
  {tool_name} {flag} export <SESSION_ID>
  {tool_name} {flag} import <archive.tar.gz> [brain_type]
  {tool_name} {flag} brain [list|init <name>|show <name>]
""".strip())


def _get_provider_name() -> str:
    """Get the best available provider."""
    try:
        from tool.LLM.logic.config import get_config_value
        configured = get_config_value("active_backend")
        if configured:
            return configured
        from tool.LLM.logic.registry import list_providers
        available = [p["name"] for p in list_providers() if p.get("available")]
        if available:
            return available[0]
    except ImportError:
        pass
    return "zhipu-glm-4.7"


def _get_system_prompt(tool_name: str, lang: str = "en",
                       mode: str = "agent") -> str:
    """Build a system prompt for the agent/ask/plan mode."""
    if mode == "agent":
        if lang == "zh":
            return (
                f"你是一个自主AI Agent，工作在 {tool_name} 工具目录中。\n"
                f"你可以独立规划、执行和验证任务。\n\n"
                f"## 可用工具\n\n"
                f"1. **exec(command=...)** — 执行shell命令。\n"
                f"2. **write_file(path=..., content=...)** — 创建/覆盖文件。\n"
                f"3. **edit_file(path=..., old_text=..., new_text=...)** — 修改文件。\n"
                f"4. **read_file(path=...)** — 读取文件内容。\n"
                f"5. **search(pattern=...)** — 搜索文本/代码。\n"
                f"6. **ask_user(question=...)** — 向用户提问。\n\n"
                f"## 关键行为\n\n"
                f"- 必须使用工具，不要只描述变更。\n"
                f"- write_file的content必须是完整文件。\n"
                f"- 修改文件前先read_file。\n"
                f"- 命令失败时尝试不同方法。\n"
            )
        return (
            f"You are an autonomous AI Agent working in the {tool_name} tool directory. "
            f"You can independently plan, execute, and verify tasks.\n\n"
            f"## Available Tools\n\n"
            f"1. **exec(command=...)** — Run shell commands.\n"
            f"2. **write_file(path=..., content=...)** — Create/overwrite files.\n"
            f"3. **edit_file(path=..., old_text=..., new_text=...)** — Modify files.\n"
            f"4. **read_file(path=...)** — Read file contents.\n"
            f"5. **search(pattern=...)** — Search for text/code.\n"
            f"6. **ask_user(question=...)** — Ask the user a question.\n\n"
            f"## Key Behaviors\n\n"
            f"- Always use tools. Never just describe changes.\n"
            f"- write_file content must be the COMPLETE file.\n"
            f"- Read files before modifying them.\n"
            f"- If a command fails, try a different approach.\n"
        )

    mode_label = MODE_LABELS.get(mode, mode)
    if mode == "ask":
        if lang == "zh":
            return (
                f"你是一个AI助手，工作在 {tool_name} 工具目录中，处于 **Ask模式**（只读）。\n"
                f"你可以探索代码库并回答问题，但**不能修改任何文件**。\n\n"
                f"## 可用工具\n\n"
                f"1. **exec(command=...)** — 执行只读shell命令（ls, cat, grep, find, git log等）。\n"
                f"   禁止: rm, mv, cp, mkdir, touch, chmod, tee, 重定向(>), pip/npm install。\n"
                f"2. **read_file(path=...)** — 读取文件内容。\n"
                f"3. **search(pattern=...)** — 搜索文本/代码。\n"
                f"4. **ask_user(question=...)** — 向用户提问。\n\n"
                f"## 关键行为\n\n"
                f"- 使用工具探索代码，回答问题。\n"
                f"- 不能创建、修改或删除任何文件。\n"
                f"- 如果用户要求修改，解释你处于只读模式。\n"
            )
        return (
            f"You are an AI assistant in {mode_label} Mode (read-only) for {tool_name}.\n"
            f"You can explore the codebase and answer questions but **cannot modify any files**.\n\n"
            f"## Available Tools\n\n"
            f"1. **exec(command=...)** — Run READ-ONLY shell commands (ls, cat, grep, find, git log, etc.).\n"
            f"   FORBIDDEN: rm, mv, cp, mkdir, touch, chmod, tee, redirect (>), pip/npm install.\n"
            f"2. **read_file(path=...)** — Read file contents.\n"
            f"3. **search(pattern=...)** — Search for text/code.\n"
            f"4. **ask_user(question=...)** — Ask the user a question.\n\n"
            f"## Key Behaviors\n\n"
            f"- Use tools to explore code and answer questions.\n"
            f"- You CANNOT create, modify, or delete any files.\n"
            f"- If the user asks for modifications, explain you are in read-only mode.\n"
        )

    if lang == "zh":
        return (
            f"你是一个AI助手，工作在 {tool_name} 工具目录中，处于 **Plan模式**（只读规划）。\n"
            f"你可以分析代码库并设计实施方案，但**不能修改任何文件或执行脚本**。\n\n"
            f"## 可用工具\n\n"
            f"1. **exec(command=...)** — 执行只读shell命令（ls, cat, grep, find, git log等）。\n"
            f"   禁止: 所有写入操作、脚本执行（python3 xxx.py等）。\n"
            f"2. **read_file(path=...)** — 读取文件内容。\n"
            f"3. **search(pattern=...)** — 搜索文本/代码。\n"
            f"4. **ask_user(question=...)** — 向用户提问。\n\n"
            f"## 关键行为\n\n"
            f"- 分析代码结构，设计方案，给出具体的实施步骤。\n"
            f"- 不能创建、修改或删除任何文件。\n"
            f"- 不能执行任何脚本。\n"
            f"- 输出清晰的计划和建议。\n"
        )
    return (
        f"You are an AI assistant in {mode_label} Mode (read-only planning) for {tool_name}.\n"
        f"You can analyze the codebase and design implementation plans but **cannot modify "
        f"any files or execute scripts**.\n\n"
        f"## Available Tools\n\n"
        f"1. **exec(command=...)** — Run READ-ONLY shell commands (ls, cat, grep, find, git log, etc.).\n"
        f"   FORBIDDEN: All write operations and script execution (python3 script.py, etc.).\n"
        f"2. **read_file(path=...)** — Read file contents.\n"
        f"3. **search(pattern=...)** — Search for text/code.\n"
        f"4. **ask_user(question=...)** — Ask the user a question.\n\n"
        f"## Key Behaviors\n\n"
        f"- Analyze code structure, design plans, give concrete implementation steps.\n"
        f"- You CANNOT create, modify, or delete any files.\n"
        f"- You CANNOT execute scripts.\n"
        f"- Output clear plans and recommendations.\n"
    )


def _handle_prompt(args: list, tool_name: str, project_root: str,
                   tool_dir: str, mode: str = "agent"):
    """Start a new session with an initial prompt."""
    if not args:
        flag = f"--{mode}"
        print(f"Usage: {flag} prompt \"Your task description\"")
        return

    prompt = " ".join(args)
    provider = _get_provider_name()
    codebase = tool_dir or os.path.join(project_root, "tool", tool_name)

    session = AgentSession(
        tool_name=tool_name,
        codebase_root=codebase,
        provider_name=provider,
        tier=2,
        mode=mode,
    )

    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    label = MODE_LABELS.get(mode, "Agent")
    print(f"  {BOLD}{label} session started.{RESET} {DIM}{session.id}{RESET}")
    if mode in ("ask", "plan"):
        print(f"  {DIM}Read-only mode: file modifications disabled.{RESET}")
    print(f"  {DIM}Provider: {provider} | CWD: {codebase}{RESET}")

    events = []
    def emit(evt):
        events.append(evt)
        _print_event(evt)

    system_prompt = _get_system_prompt(tool_name, mode=mode)
    from logic.agent.loop import AgentLoop
    loop = AgentLoop(
        session=session,
        provider_name=provider,
        system_prompt=system_prompt,
        project_root=project_root,
        emit=emit,
        tier=session.tier,
        mode=mode,
    )

    result = loop.run_turn(prompt)
    save_session(session, project_root)

    flag = f"--{mode}"
    print(f"\n  {BOLD}Session complete.{RESET} {DIM}ID: {session.id}{RESET}")
    print(f"  {DIM}Use: {tool_name} {flag} feed {session.id} \"follow-up\"{RESET}")


def _handle_feed(args: list, tool_name: str, project_root: str,
                 tool_dir: str, mode: str = "agent"):
    """Send a follow-up to an existing session."""
    if len(args) < 2:
        flag = f"--{mode}"
        print(f"Usage: {flag} feed <SESSION_ID> \"Your instruction\"")
        return

    session_id = args[0]
    text = " ".join(args[1:])

    session = load_session(session_id, project_root)
    if not session:
        print(f"Session {session_id} not found.")
        return

    session_mode = getattr(session, 'mode', mode)
    provider = session.provider_name or _get_provider_name()

    events = []
    def emit(evt):
        events.append(evt)
        _print_event(evt)

    system_prompt = _get_system_prompt(tool_name, mode=session_mode)
    from logic.agent.loop import AgentLoop
    loop = AgentLoop(
        session=session,
        provider_name=provider,
        system_prompt=system_prompt,
        project_root=project_root,
        emit=emit,
        tier=session.tier,
        mode=session_mode,
    )

    result = loop.run_turn(text)
    save_session(session, project_root)

    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")
    print(f"\n  {BOLD}Turn complete.{RESET} {DIM}ID: {session.id} | Messages: {session.message_count}{RESET}")


def _handle_status(args: list, project_root: str):
    """Show session status."""
    if args:
        session = load_session(args[0], project_root)
        if session:
            print(json.dumps(session.to_dict(), indent=2))
        else:
            print(f"Session {args[0]} not found.")
    else:
        sessions = list_sessions(project_root)
        if not sessions:
            print("No agent sessions found.")
            return
        latest = sessions[0]
        print(json.dumps(latest, indent=2))


def _handle_sessions(project_root: str):
    """List all agent sessions."""
    sessions = list_sessions(project_root)
    if not sessions:
        print("No agent sessions found.")
        return
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    for s in sessions[:10]:
        status = s.get("status", "?")
        sid = s.get("id", "?")
        tool = s.get("tool_name", "?")
        msgs = s.get("message_count", 0)
        print(f"  {BOLD}{sid}{RESET} {tool} ({status}, {msgs} msgs) {DIM}{s.get('codebase_root', '')}{RESET}")


def _handle_setup(project_root: str):
    """Configure LLM API key."""
    try:
        from tool.LLM.logic.config import get_config_value, set_config_value
        print("Configure LLM API key for agent mode.")
        print("Currently supported: zhipu (GLM-4.7), nvidia (GLM-4.7)")

        provider = input("Provider [zhipu/nvidia]: ").strip() or "zhipu"
        key = input(f"API key for {provider}: ").strip()
        if key:
            if provider == "zhipu":
                set_config_value("zhipu_api_key", key)
            elif provider == "nvidia":
                set_config_value("nvidia_api_key", key)
            print("Saved.")
        else:
            print("No key provided.")
    except Exception as e:
        print(f"Setup failed: {e}")


def _handle_export(args: list, project_root: str):
    """Export a session + memory to a portable archive."""
    if not args:
        print("Usage: --agent export <SESSION_ID> [output_path]")
        return
    session_id = args[0]
    output_path = args[1] if len(args) > 1 else None
    try:
        from logic.agent.export import export_session
        path = export_session(session_id, project_root, output_path=output_path)
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        print(f"  {BOLD}Exported.{RESET} {path}")
    except Exception as e:
        print(f"Export failed: {e}")


def _handle_import(args: list, project_root: str):
    """Import a session + memory from an archive."""
    if not args:
        print("Usage: --agent import <archive_path> [brain_type]")
        return
    archive_path = args[0]
    brain_type = args[1] if len(args) > 1 else "default"
    try:
        from logic.agent.export import import_session
        sid = import_session(archive_path, project_root, brain_type=brain_type)
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        RESET = get_color("RESET", "\033[0m")
        print(f"  {BOLD}Imported.{RESET} Session ID: {sid}")
    except Exception as e:
        print(f"Import failed: {e}")


def _handle_brain(args: list, project_root: str):
    """Manage brain types."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    if not args or args[0] == "list":
        from logic.agent.brain import list_brain_types
        brains = list_brain_types(project_root)
        if not brains:
            print(f"  {DIM}No brain types found. Use 'brain init <name>' to create one.{RESET}")
            return
        for b in brains:
            print(f"  {BOLD}{b}{RESET}")
    elif args[0] == "init":
        name = args[1] if len(args) > 1 else "default"
        from logic.agent.brain import ensure_experience_dir
        d = ensure_experience_dir(project_root, name)
        print(f"  {BOLD}Brain initialized.{RESET} {DIM}{d}{RESET}")
    elif args[0] == "show":
        name = args[1] if len(args) > 1 else "default"
        from logic.agent.brain import get_experience_dir
        d = get_experience_dir(project_root, name)
        if not d.exists():
            print(f"  Brain '{name}' not found.")
            return
        for f in sorted(d.iterdir()):
            if f.is_file():
                size = f.stat().st_size
                print(f"  {f.name} {DIM}({size} bytes){RESET}")
            elif f.is_dir():
                count = len(list(f.glob("*")))
                print(f"  {f.name}/ {DIM}({count} files){RESET}")
    else:
        print(f"Unknown brain subcommand: {args[0]}")
        print("Usage: --agent brain [list|init <name>|show <name>]")


def _print_event(evt: dict):
    """Print an agent event to the console."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    BLUE = get_color("BLUE", "\033[34m")
    RESET = get_color("RESET", "\033[0m")

    t = evt.get("type", "")
    if t == "tool":
        name = evt.get("name", "")
        desc = evt.get("desc", "")[:80]
        print(f"  {BLUE}>{RESET} {BOLD}{name}{RESET} {desc}")
    elif t == "tool_result":
        ok = evt.get("ok", False)
        output = evt.get("output", "")[:200]
        marker = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"    [{marker}] {DIM}{output}{RESET}")
    elif t == "text":
        tokens = evt.get("tokens", "")
        if tokens and not tokens.startswith("["):
            for line in tokens.split("\n")[:20]:
                print(f"  {line}")
    elif t == "ask_user":
        q = evt.get("question", "")
        print(f"\n  {BOLD}Agent asks:{RESET} {q}")
    elif t == "llm_response_end":
        latency = evt.get("latency_s", 0)
        has_tc = evt.get("has_tool_calls", False)
        tc_label = " (tool calls)" if has_tc else ""
        print(f"  {DIM}[{latency}s{tc_label}]{RESET}")
