"""Agent command handler — implements --agent/--ask/--plan subcommands.

Subcommands:
    prompt "..."              Start a new session and send initial prompt
    feed <SID> <CMD>          Send a follow-up command to an existing session
    response <SID> <JSON>     Inject structured LLM response events into session
    history [SID] [--limit N] Show recent N events for a session in CLI format
    config [KEY] [VALUE]      View/set assistant configuration
    status [SID]              Show session status
    sessions                  List all sessions
    setup                     Configure LLM API keys
    export <SID>              Export session + memory to archive
    import <archive> [brain]  Import session from archive
    brain [list|init|show]    Manage brain types

Shorthand (when ALLOW_IMPLICIT_PROMPT is True):
    TOOL --ask "my question"  ≡  TOOL --ask prompt "my question"
    TOOL --ask --prompt "q"   ≡  TOOL --ask prompt "q"

Toggle ALLOW_IMPLICIT_PROMPT to False if symmetric command growth causes
ambiguity between subcommands and prompt text.
"""
import json
import os
import sys
import time
from typing import Optional

from logic.agent.state import (
    AgentSession, save_session, load_session, list_sessions,
)

# ── Shorthand Toggles ────────────────────────────────────────────────
# Flip to False when symmetric command growth causes ambiguity.
#
# ALLOW_IMPLICIT_PROMPT:
#   True  → TOOL --ask "my question" works (omit 'prompt' subcommand)
#   False → TOOL --ask prompt "my question" required
#
# ALLOW_ASSISTANT_SHORTHAND:
#   True  → TOOL --ask ... works (--assistant omitted)
#   False → TOOL --assistant --ask ... required
#
# Both are imported by logic/tool/blueprint/base.py for dispatch.
ALLOW_IMPLICIT_PROMPT = True
ALLOW_ASSISTANT_SHORTHAND = True


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

    gui_mode = "--gui" in args or "--live" in args
    dry_run = "--dry-run" in args
    self_operate = "--self-operate" in args

    self_name = ""
    env_spec = ""
    prompt_flag_texts = []
    workspace_path = ""
    filtered_args = []
    i = 0
    skip_flags = {"--gui", "--live", "--dry-run", "--self-operate"}
    while i < len(args):
        if args[i] == "--self-name" and i + 1 < len(args):
            self_name = args[i + 1]
            i += 2
        elif args[i] == "--env" and i + 1 < len(args):
            env_spec = args[i + 1]
            i += 2
        elif args[i] == "--prompt" and i + 1 < len(args):
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                prompt_flag_texts.append(args[i])
                i += 1
        elif args[i] == "--workspace" and i + 1 < len(args):
            workspace_path = args[i + 1]
            i += 2
        elif args[i] in skip_flags:
            i += 1
        else:
            filtered_args.append(args[i])
            i += 1
    prompt_flag_text = prompt_flag_texts[0] if prompt_flag_texts else ""

    if workspace_path:
        ws_path = os.path.abspath(workspace_path)
        if os.path.isdir(ws_path):
            tool_dir = ws_path

    self_operate_opts = {
        "self_operate": self_operate,
        "self_name": self_name,
        "env": env_spec,
    } if self_operate else {}

    subcmd = filtered_args[0] if filtered_args else ""
    rest = filtered_args[1:]

    if prompt_flag_text:
        prompt_args = [prompt_flag_text] + rest
        if gui_mode or self_operate:
            _handle_prompt_gui(prompt_args, tool_name, project_root, tool_dir,
                               mode=mode, extra_prompts=prompt_flag_texts[1:],
                               **self_operate_opts)
        elif dry_run:
            _handle_prompt(prompt_args, tool_name, project_root, tool_dir,
                           mode=mode, dry_run=True)
        else:
            _handle_prompt(prompt_args, tool_name, project_root, tool_dir,
                           mode=mode, dry_run=False)
        return

    _KNOWN_SUBCMDS_EARLY = {
        "prompt", "feed", "response", "history", "config", "status",
        "sessions", "setup", "export", "import", "brain",
    }

    if (gui_mode or self_operate) and subcmd == "prompt":
        _handle_prompt_gui(rest, tool_name, project_root, tool_dir, mode=mode,
                           **self_operate_opts)
        return
    elif (gui_mode or self_operate) and not subcmd:
        _handle_prompt_gui([], tool_name, project_root, tool_dir, mode=mode,
                           **self_operate_opts)
        return
    elif (gui_mode or self_operate) and ALLOW_IMPLICIT_PROMPT and subcmd not in _KNOWN_SUBCMDS_EARLY:
        _handle_prompt_gui(filtered_args, tool_name, project_root, tool_dir,
                           mode=mode, **self_operate_opts)
        return

    _KNOWN_SUBCMDS = {
        "prompt", "feed", "response", "history", "config", "status",
        "sessions", "setup", "export", "import", "brain",
    }

    if subcmd == "prompt":
        _handle_prompt(rest, tool_name, project_root, tool_dir, mode=mode,
                       dry_run=dry_run)
    elif subcmd == "feed":
        _handle_feed(rest, tool_name, project_root, tool_dir, mode=mode,
                     dry_run=dry_run)
    elif subcmd == "response":
        _handle_response(rest, tool_name, project_root, tool_dir, mode=mode)
    elif subcmd == "history":
        _handle_history(rest, project_root)
    elif subcmd == "config":
        _handle_config(rest, project_root)
    elif subcmd == "status":
        _handle_status(rest, project_root, tool_dir)
    elif subcmd == "sessions":
        _handle_sessions(project_root, tool_dir)
    elif subcmd == "setup":
        _handle_setup(project_root)
    elif subcmd == "export":
        _handle_export(rest, project_root)
    elif subcmd == "import":
        _handle_import(rest, project_root)
    elif subcmd == "brain":
        _handle_brain(rest, project_root)
    elif ALLOW_IMPLICIT_PROMPT and subcmd and subcmd not in _KNOWN_SUBCMDS:
        implicit_args = filtered_args
        if gui_mode or self_operate:
            _handle_prompt_gui(implicit_args, tool_name, project_root, tool_dir,
                               mode=mode, **self_operate_opts)
        elif dry_run:
            _handle_prompt(implicit_args, tool_name, project_root, tool_dir,
                           mode=mode, dry_run=True)
        else:
            _handle_prompt(implicit_args, tool_name, project_root, tool_dir,
                           mode=mode, dry_run=False)
    else:
        print(f"Unknown subcommand: {subcmd}")
        _print_help(tool_name, mode)


MODE_LABELS = {"agent": "Agent", "ask": "Ask", "plan": "Plan"}


def _ensure_workspace(tool_dir: str, project_root: str, tool_name: str = "") -> dict:
    """Auto-provision and open a workspace for the given tool directory.

    Returns workspace info dict (with 'id', 'name', 'path', 'brain_path')
    or None if workspace provisioning fails.
    """
    from interface.workspace import get_workspace_manager
    from pathlib import Path

    wm = get_workspace_manager(Path(project_root))
    target = tool_dir or project_root
    if not Path(target).is_dir():
        return None

    try:
        target_name = Path(target).name
        ws_name = target_name if target_name != tool_name else tool_name
        if not ws_name or ws_name in (".", ""):
            ws_name = tool_name or "workspace"
        ws_info = wm.create_workspace(target, name=ws_name)
    except FileExistsError:
        from logic.workspace.manager import _hash_path
        ws_id = _hash_path(str(Path(target).resolve()))
        ws_info = wm.open_workspace(ws_id)
    except Exception:
        return None

    if ws_info and ws_info.get("status") != "open":
        try:
            ws_info = wm.open_workspace(ws_info["id"])
        except Exception:
            pass

    if ws_info:
        brain_path = str(wm.get_brain_path(ws_info["id"]))
        ws_info["brain_path"] = brain_path

    return ws_info


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
    implicit_note = ""
    if ALLOW_IMPLICIT_PROMPT:
        implicit_note = f"\n  {DIM}Shorthand: {tool_name} {flag} \"prompt text\" (omit 'prompt' subcommand){RESET}"
    print(f"""
{BOLD}{label} Mode{RESET} for {tool_name}{readonly_note}

Usage:
  {tool_name} {flag} "Your task description"       Start with implicit prompt
  {tool_name} {flag} prompt "Your task description" Start with explicit prompt
  {tool_name} {flag} --prompt "..." ["..." ...]     One or more prompts (queued)
  {tool_name} {flag} --gui "..."                    Open GUI with initial prompt
  {tool_name} {flag} --gui                          Open GUI (no initial prompt)
  {tool_name} {flag} --dry-run "..."                Show prompt without calling LLM
  {tool_name} {flag} --workspace /path "..."        Mount workspace directory as CWD
  {tool_name} {flag} feed <SESSION_ID> "..."        Follow-up instruction
  {tool_name} {flag} response <SID> <json>          Inject response events
  {tool_name} {flag} history [SESSION_ID] [--limit N]
  {tool_name} {flag} config [KEY [VALUE]]
  {tool_name} {flag} status [SESSION_ID]
  {tool_name} {flag} sessions
  {tool_name} {flag} setup
  {tool_name} {flag} export <SESSION_ID>{implicit_note}
  {tool_name} {flag} import <archive.tar.gz> [brain_type]
  {tool_name} {flag} brain [list|init <name>|show <name>]
""".strip())


def _get_session_config_default(key, fallback):
    """Read a session config value from the LLM config, with fallback."""
    try:
        from tool.LLM.logic.config import get_config_value
        val = get_config_value(key, fallback)
        return int(val) if isinstance(fallback, int) else val
    except Exception:
        return fallback


def _handle_prompt_gui(args: list, tool_name: str, project_root: str,
                       tool_dir: str, mode: str = "agent",
                       self_operate: bool = False, self_name: str = "",
                       env: str = "", extra_prompts: list = None):
    """Start the HTML GUI server and optionally send an initial prompt.

    When self_operate is True, the prompt is displayed in the GUI but NOT
    sent to the LLM provider. Instead, the system waits for an external
    ``--response`` command (typically from the calling AI IDE agent).
    """
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    CYAN = get_color("CYAN", "\033[36m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    import sys as _sys
    prompt = " ".join(args) if args else None
    provider = "auto"
    default_turn_limit = _get_session_config_default("default_turn_limit", 20)

    codebase = tool_dir or project_root
    ws_info = _ensure_workspace(codebase, project_root, tool_name)

    from interface.status import fmt_status, fmt_info, fmt_stage

    if ws_info:
        print(fmt_info(f"Workspace: {ws_info.get('name', '?')} [{ws_info.get('id', '?')[:8]}]"), flush=True)

    print(fmt_stage("Checking for running server...", status="active"), flush=True)
    existing_port = _find_running_gui_port()
    if existing_port:
        base_url = f"http://localhost:{existing_port}"
        print(fmt_status("Reusing GUI.", complement=f"at {base_url}"), flush=True)

        try:
            import urllib.request
            scope_body = json.dumps({
                "scope_name": tool_name,
                "default_codebase": codebase,
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/api/scope",
                data=scope_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception:
            pass

        if prompt and _has_running_session(base_url):
            RED = get_color("RED", "\033[31m")
            print(f"  {RED}{BOLD}Blocked.{RESET} A session is still running.", flush=True)
            print(f"  {DIM}Complete or cancel the current task before starting a new one.{RESET}")
            return

        if prompt and not self_operate:
            try:
                import urllib.request
                data = json.dumps({"text": prompt, "turn_limit": default_turn_limit}).encode()
                req = urllib.request.Request(
                    f"{base_url}/api/session/default/send",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
                print(f"  {BOLD}Sent{RESET} initial prompt.", flush=True)
            except Exception:
                print(f"  Prompt queued — type it in the browser.", flush=True)
            if extra_prompts:
                _queue_extra_prompts(base_url, extra_prompts, default_turn_limit)
        elif prompt and self_operate:
            _inject_self_operate_prompt(base_url, prompt, self_name, env,
                                        default_turn_limit)
        return

    try:
        from logic.assistant.gui.server import start_server
    except ImportError:
        print(f"  {BOLD}LLM tool not available.{RESET} Install it first.", flush=True)
        return

    label = MODE_LABELS.get(mode, "Agent")
    if self_operate:
        label_display = f"{label} (self-operate)"
    else:
        label_display = label
    print(fmt_stage("Starting server...", status="active"), flush=True)
    print(fmt_info(f"{label_display} GUI (provider: {provider})"), flush=True)

    try:
        from tool.LLM.logic.config import get_config_value
        lang = get_config_value("lang", "en")
    except Exception:
        lang = "en"

    agent = start_server(
        selected_model=provider,
        port=0,
        open_browser=True,
        enable_tools=True,
        default_codebase=tool_dir or None,
        lang=lang,
        scope_name=tool_name,
    )

    print(fmt_status("Started GUI.", complement=f"at {agent.url}", style="success"), flush=True)

    if prompt:
        import time as _t
        _t.sleep(0.5)
        if self_operate:
            _inject_self_operate_prompt(agent.url, prompt, self_name, env,
                                        default_turn_limit)
        else:
            try:
                import urllib.request
                data = json.dumps({"text": prompt, "turn_limit": default_turn_limit}).encode()
                req = urllib.request.Request(
                    f"{agent.url}/api/session/default/send",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
                print(f"  {BOLD}Sent{RESET} initial prompt.", flush=True)
            except Exception:
                print(f"  Prompt queued — type it in the browser.", flush=True)
            if extra_prompts:
                _queue_extra_prompts(agent.url, extra_prompts, default_turn_limit)

    if self_operate:
        print(f"  {CYAN}{BOLD}Self-operate mode.{RESET} {DIM}Awaiting --response.{RESET}", flush=True)

    print(fmt_info("Press Ctrl+C to stop."), flush=True)
    _sys.stdout.flush()
    try:
        agent._server.wait()
    except KeyboardInterrupt:
        agent.stop()


def _queue_extra_prompts(base_url: str, prompts: list, turn_limit: int):
    """Queue additional prompts after the initial prompt has been sent."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    import urllib.request
    import time as _t
    _t.sleep(0.3)

    queued = 0
    for p in prompts:
        p = p.strip()
        if not p:
            continue
        try:
            data = json.dumps({"text": p, "turn_limit": turn_limit}).encode()
            req = urllib.request.Request(
                f"{base_url}/api/session/default/send",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
            queued += 1
        except Exception:
            pass
    if queued:
        print(f"  {BOLD}Queued{RESET} {DIM}{queued} additional prompt(s).{RESET}", flush=True)


def _inject_self_operate_prompt(base_url: str, prompt: str, self_name: str,
                                env: str, turn_limit: int):
    """Inject a self-operate prompt into the GUI without calling LLM."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    CYAN = get_color("CYAN", "\033[36m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    import urllib.request

    title = prompt[:50] if prompt else "Self-operate"

    env_label = ""
    if env:
        parts = env.split("/")
        env_label = parts[-1] if parts else env

    display_name = f"{env_label} ({self_name})" if env_label and self_name else self_name or env_label or "Self"

    events = [
        {"type": "user", "prompt": prompt},
        {"type": "session_status", "id": "__SID__", "status": "running"},
        {
            "type": "llm_request",
            "provider": display_name,
            "round": 1,
            "model": self_name or "self",
            "self_operate": True,
            "env": env,
            "self_name": self_name,
        },
    ]

    payload = json.dumps({
        "title": title,
        "events": events,
        "self_operate": True,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/api/sessions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
    sid = resp.get("session_id", "")

    print(f"  {BOLD}Self-operate prompt sent.{RESET} {DIM}Session: {sid}{RESET}")
    print(f"  {CYAN}Awaiting response:{RESET} --agent response {sid[:8]} <json>")
    print(f"  {DIM}Display name: {display_name}{RESET}")


def _has_running_session(base_url: str) -> bool:
    """Check if any session is currently in 'running' state."""
    try:
        import urllib.request
        resp = json.loads(
            urllib.request.urlopen(f"{base_url}/api/sessions", timeout=5).read())
        for s in resp.get("sessions", []):
            if s.get("status") == "running":
                return True
    except Exception:
        pass
    return False


def _get_provider_name() -> str:
    """Get the best available provider. Defaults to 'auto' for intelligent selection."""
    try:
        from tool.LLM.logic.config import get_config_value
        configured = get_config_value("active_backend")
        if configured:
            return configured
    except ImportError:
        pass
    return "auto"


def _get_system_prompt(tool_name: str, mode: str = "agent") -> str:
    """Build a system prompt for the agent/ask/plan mode."""
    if mode == "agent":
        return (
            f"You are an autonomous AI Agent working in the {tool_name} tool directory. "
            f"You can independently plan, execute, and verify tasks.\n\n"
            f"## Available Tools\n\n"
            f"1. **exec(command=...)** — Run shell commands.\n"
            f"2. **write_file(path=..., content=...)** — Create/overwrite files.\n"
            f"3. **edit_file(path=..., old_text=..., new_text=...)** — Modify files.\n"
            f"4. **read_file(path=...)** — Read file contents.\n"
            f"5. **search(pattern=...)** — Search for text/code.\n"
            f"6. **ask_user(question=...)** — Ask the user a question.\n"
            f"7. **todo(action=..., items=...)** — Manage task lists (init/update/delete items).\n"
            f"8. **switch_mode(target_mode=..., explanation=...)** — "
            f"Request to switch to a different operating mode (e.g. 'plan'). "
            f"The user may approve or deny the switch. If denied, write your plan "
            f"to a tmp/ file or use the todo tool to organize tasks.\n\n"
            f"## Key Behaviors\n\n"
            f"- Always use tools. Never just describe changes — ACT.\n"
            f"- **Read ALL relevant files before writing.** If you see 2+ files, read them all.\n"
            f"- write_file content must be the COMPLETE file, not a fragment.\n"
            f"- **Modify existing files in-place** — do NOT create new files at different paths.\n"
            f"  If the user says 'edit /path/file.html', write to that EXACT path.\n"
            f"- Use edit_file for targeted changes instead of rewriting entire files.\n"
            f"- If a command fails, try a different approach.\n"
            f"- Verify your work: read the file after writing to confirm.\n"
            f"- If a task is very complex and you cannot plan it clearly in your head, "
            f"consider using switch_mode to request Plan mode. If denied, use the "
            f"todo tool to break the task down, or write a plan to tmp/plan.md.\n\n"
            f"## Input Recognition\n\n"
            f"If the prompt is empty, garbled, or looks like a command/flag "
            f"(e.g. '--port 8100'), respond briefly and stop. "
            f"Do NOT explore the project or read files speculatively.\n\n"
            f"## Stopping Rules\n\n"
            f"- **STOP immediately** once the task is complete. Output a brief summary.\n"
            f"- If the task is ambiguous, make a reasonable assumption and act — "
            f"do NOT keep asking the user for clarification.\n"
            f"- Do NOT loop endlessly refining. One verification pass is sufficient.\n"
            f"- If you have done 3+ reads/searches without editing, stop exploring and act.\n"
            f"- If you cannot complete the task (missing permissions, broken tools), "
            f"state the blocker and STOP.\n"
        )

    mode_label = MODE_LABELS.get(mode, mode)
    if mode == "ask":
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
                   tool_dir: str, mode: str = "agent",
                   dry_run: bool = False):
    """Start a new session with an initial prompt."""
    if not args:
        flag = f"--{mode}"
        print(f"Usage: {flag} prompt \"Your task description\"")
        return

    prompt = " ".join(args)
    provider = _get_provider_name()
    codebase = tool_dir or os.path.join(project_root, "tool", tool_name)

    from logic.assistant.sandbox import set_tool_sandbox_dir
    set_tool_sandbox_dir(tool_dir or None)

    ws_info = _ensure_workspace(codebase, project_root, tool_name)

    session = AgentSession(
        tool_name=tool_name,
        codebase_root=codebase,
        selected_model=provider,
        tier=2,
        mode=mode,
        initial_prompt=prompt[:500],
    )
    if ws_info:
        session.workspace_id = ws_info.get("id")
        session.workspace_brain_path = ws_info.get("brain_path")

    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RESET = get_color("RESET", "\033[0m")

    label = MODE_LABELS.get(mode, "Agent")

    if dry_run:
        _print_dry_run(
            session, prompt, tool_name, project_root, mode, provider)
        return

    gui_url, gui_base, gui_sid = _ensure_gui_and_create_session(
        session, provider, tool_dir, mode)
    if gui_url:
        print(f"  {BOLD}GUI session opened.{RESET} {DIM}{gui_url}{RESET}")

    print(f"  {BOLD}{label} session started.{RESET} {DIM}{session.id}{RESET}")
    if mode in ("ask", "plan"):
        print(f"  {DIM}Read-only mode: file modifications disabled.{RESET}")
    print(f"  {DIM}Provider: {provider} | CWD: {codebase}{RESET}")

    events = []
    _gui_injector = (
        _GuiEventInjector(f"{gui_base}/api/session/{gui_sid}/inject")
        if gui_base and gui_sid else None
    )

    _GUI_SKIP_TYPES = {"debug"}

    def emit(evt):
        events.append(evt)
        _print_event(evt)
        if _gui_injector and evt.get("type") not in _GUI_SKIP_TYPES:
            _gui_injector.push(evt)

    system_prompt = _get_system_prompt(tool_name, mode=mode)
    from logic.agent.loop import AgentLoop
    loop = AgentLoop(
        session=session,
        selected_model=provider,
        system_prompt=system_prompt,
        project_root=project_root,
        emit=emit,
        tier=session.tier,
        mode=mode,
    )

    result = loop.run_turn(prompt)
    if _gui_injector:
        _gui_injector.flush_and_stop()
    save_session(session, project_root, tool_dir=tool_dir)

    flag = f"--{mode}"
    print(f"\n  {BOLD}Session complete.{RESET} {DIM}ID: {session.id}{RESET}")
    print(f"  {DIM}Use: {tool_name} {flag} feed {session.id} \"follow-up\"{RESET}")


def _handle_feed(args: list, tool_name: str, project_root: str,
                 tool_dir: str, mode: str = "agent",
                 dry_run: bool = False):
    """Send a follow-up to an existing session."""
    if len(args) < 2:
        flag = f"--{mode}"
        print(f"Usage: {flag} feed <SESSION_ID> \"Your instruction\"")
        return

    session_id = args[0]
    text = " ".join(args[1:])

    session = load_session(session_id, project_root, tool_dir=tool_dir)
    if not session:
        print(f"Session {session_id} not found.")
        return

    session_mode = getattr(session, 'mode', mode)
    provider = session.provider_name or _get_provider_name()

    if dry_run:
        return _print_dry_run(
            session, text, tool_name, project_root, session_mode, provider)

    gui_inject_url = _find_gui_inject_url_for_session(session_id)
    _gui_injector = (
        _GuiEventInjector(gui_inject_url) if gui_inject_url else None
    )

    events = []
    _GUI_SKIP_TYPES_FEED = {"debug"}

    def emit(evt):
        events.append(evt)
        _print_event(evt)
        if _gui_injector and evt.get("type") not in _GUI_SKIP_TYPES_FEED:
            _gui_injector.push(evt)

    system_prompt = _get_system_prompt(tool_name, mode=session_mode)
    from logic.agent.loop import AgentLoop
    loop = AgentLoop(
        session=session,
        selected_model=provider,
        system_prompt=system_prompt,
        project_root=project_root,
        emit=emit,
        tier=session.tier,
        mode=session_mode,
    )

    result = loop.run_turn(text)
    if _gui_injector:
        _gui_injector.flush_and_stop()
    save_session(session, project_root, tool_dir=tool_dir)

    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")
    print(f"\n  {BOLD}Turn complete.{RESET} {DIM}ID: {session.id} | Messages: {session.message_count}{RESET}")


def _handle_response(args: list, tool_name: str, project_root: str,
                     tool_dir: str, mode: str = "agent"):
    """Inject structured LLM response events into a session.

    Accepts a sequence of JSON events (llm_response_start, text,
    llm_response_end, tool_result, etc.) and feeds them into
    the active ConversationManager session. After processing any
    tool calls, prints the next LLM request payload.
    """
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    CYAN = get_color("CYAN", "\033[36m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RESET = get_color("RESET", "\033[0m")

    if not args:
        flag = f"--{mode}"
        print(f"Usage: {flag} response <SESSION_ID> <json_file_or_string>")
        print(f"  Provide either a path to a .json file or inline JSON.")
        print(f"  The JSON should be an array of event objects or a single event.")
        return

    session_id = args[0]
    json_input = " ".join(args[1:]) if len(args) > 1 else ""

    if not json_input:
        flag = f"--{mode}"
        print(f"Usage: {flag} response {session_id} <json_file_or_string>")
        return

    if os.path.isfile(json_input):
        with open(json_input, encoding="utf-8") as f:
            json_input = f.read()

    try:
        data = json.loads(json_input)
    except json.JSONDecodeError as e:
        print(f"  {BOLD}Invalid JSON.{RESET} {DIM}{e}{RESET}")
        return

    events = data if isinstance(data, list) else [data]

    import urllib.request
    port = _find_running_gui_port()
    if not port:
        print(f"  {BOLD}No running GUI server found.{RESET} Start one with --gui first.")
        return

    base_url = f"http://localhost:{port}"

    sessions_resp = json.loads(
        urllib.request.urlopen(f"{base_url}/api/sessions", timeout=5).read())
    found = None
    for s in sessions_resp.get("sessions", []):
        if s.get("id", "").startswith(session_id):
            found = s["id"]
            break
    if not found:
        print(f"  {BOLD}Session not found.{RESET} {DIM}{session_id}{RESET}")
        return

    def _inject(evt):
        """Push a single event to the GUI SSE stream."""
        req = urllib.request.Request(
            f"{base_url}/api/session/{found}/inject",
            data=json.dumps({"event": evt}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)

    full_text = ""
    tool_calls = []
    tool_results_provided = 0
    has_tool_calls = False

    for evt in events:
        etype = evt.get("type", "")

        if etype == "llm_request":
            _inject(evt)
            provider = evt.get("provider", "LLM")
            round_num = evt.get("round", 1)
            print(f"  {CYAN}[R{round_num}]{RESET} {DIM}{provider}{RESET}")

        elif etype == "llm_response_start":
            _inject(evt)
            round_num = evt.get("round", "?")
            print(f"  {CYAN}[R{round_num}]{RESET} Response start")

        elif etype == "text":
            tokens = evt.get("tokens", "")
            full_text += tokens
            _inject(evt)
            sys.stdout.write(tokens)
            sys.stdout.flush()

        elif etype == "tool_call" or etype == "tool":
            tool_calls.append(evt)
            has_tool_calls = True
            name = evt.get("name", evt.get("function", {}).get("name", "?"))
            _inject(evt)
            print(f"\n  {BOLD}> {name}{RESET}")

        elif etype == "tool_result":
            tool_results_provided += 1
            _inject(evt)
            _print_event(evt)

        elif etype == "thinking":
            _inject(evt)

        elif etype == "llm_response_end":
            has_tool_calls = evt.get("has_tool_calls", has_tool_calls)
            latency = evt.get("latency_s", 0)
            provider = evt.get("provider", "?")
            usage = evt.get("usage", {})
            if not usage.get("completion_tokens") and full_text:
                est_out = max(1, len(full_text) // 4)
                est_in = est_out * 2
                evt.setdefault("usage", {})
                evt["usage"]["completion_tokens"] = est_out
                evt["usage"]["prompt_tokens"] = est_in
                evt["usage"]["total_tokens"] = est_in + est_out
            if full_text:
                evt["_full_text"] = full_text
            _inject(evt)
            print(f"\n  {DIM}[{latency}s via {provider}]{RESET}")

            unresolved = [tc for tc in tool_calls[tool_results_provided:]]
            if unresolved:
                print(f"\n  {YELLOW}{BOLD}Executing tool calls...{RESET}")
                for tc in unresolved:
                    name = tc.get("name", tc.get("function", {}).get("name", "?"))
                    tc_args = tc.get("arguments", tc.get("function", {}).get("arguments", {}))
                    if isinstance(tc_args, str):
                        try:
                            tc_args = json.loads(tc_args)
                        except json.JSONDecodeError:
                            pass
                    result = _execute_tool_via_api(base_url, found, name, tc_args)
                    _inject(result)
                    _print_event(result)

            if full_text:
                print(f"\n  {CYAN}{BOLD}═══ Context updated ═══{RESET}")
                print(f"  {DIM}Full text ({len(full_text)} chars) injected to session.{RESET}")

        elif etype == "complete":
            _inject(evt)
            print(f"\n  {BOLD}Complete.{RESET}")

        elif etype == "user":
            _inject(evt)

        else:
            _inject(evt)

    state_resp = json.loads(
        urllib.request.urlopen(f"{base_url}/api/state", timeout=5).read())
    state = state_resp.get("state", {})
    active_sid = state.get("active_session")
    status = state.get("status", "?")
    print(f"\n  {BOLD}Session state.{RESET} {DIM}ID: {found} | Status: {status}{RESET}")

    if has_tool_calls and tool_calls:
        _auto_feed(base_url, found, tool_calls, BOLD, DIM, CYAN, YELLOW, RESET)

    _check_self_operate_queue(base_url, found, BOLD, DIM, CYAN, RESET)


def _check_self_operate_queue(base_url: str, session_id: str,
                              BOLD: str, DIM: str, CYAN: str, RESET: str):
    """After --response completes, check if queued tasks exist and report."""
    import urllib.request
    try:
        resp = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(
                    f"{base_url}/api/session/{session_id}/queue",
                    data=json.dumps({"action": "list"}).encode(),
                    headers={"Content-Type": "application/json"},
                ), timeout=5).read())
        queue = resp.get("queue", [])
        if queue:
            next_task = queue[0]
            print(f"\n  {CYAN}{BOLD}Queue has {len(queue)} pending task(s).{RESET}")
            print(f"  {DIM}Next: {next_task.get('text', '?')[:80]}{RESET}")
            print(f"  {DIM}The queued task will start when a new --response is sent,")
            print(f"  or use --prompt to start it as a provider task.{RESET}")
    except Exception:
        pass


def _auto_feed(base_url: str, session_id: str, tool_calls: list,
               BOLD: str, DIM: str, CYAN: str, YELLOW: str, RESET: str):
    """After --response with tool calls, emit tool results and next llm_request.

    This simulates the automatic feed that occurs after tool execution,
    preparing the session for the next --response from the self-operate agent.
    """
    import urllib.request

    history = json.loads(
        urllib.request.urlopen(
            f"{base_url}/api/history/{session_id}", timeout=5).read())
    events = history.get("events", [])

    current_round = 1
    for evt in events:
        if evt.get("type") == "llm_request":
            r = evt.get("round", 1)
            if r > current_round:
                current_round = r
    next_round = current_round + 1

    self_operate = False
    self_name = ""
    env_spec = ""
    provider_display = ""
    for evt in events:
        if evt.get("type") == "llm_request":
            if evt.get("self_operate"):
                self_operate = True
                self_name = evt.get("self_name", "")
                env_spec = evt.get("env", "")
                provider_display = evt.get("provider", "")

    if self_operate:
        next_req = {
            "type": "llm_request",
            "provider": provider_display,
            "round": next_round,
            "model": self_name or "self",
            "self_operate": True,
            "env": env_spec,
            "self_name": self_name,
        }
        req = urllib.request.Request(
            f"{base_url}/api/session/{session_id}/inject",
            data=json.dumps({"event": next_req}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)

        print(f"\n  {CYAN}{BOLD}═══ Feed (Round {next_round}) ═══{RESET}")
        print(f"  {DIM}Awaiting next --response for round {next_round}.{RESET}")
        print(f"  {DIM}Session: {session_id[:8]}{RESET}")


def _find_running_gui_port() -> int:
    """Find the port of a running LLM Agent GUI server."""
    import socket
    import urllib.request

    def _port_open(port: int) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.05)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            return False

    for port_range in [range(8100, 8200), range(9780, 9800)]:
        for port in port_range:
            if not _port_open(port):
                continue
            try:
                resp = urllib.request.urlopen(
                    f"http://localhost:{port}/api/state", timeout=0.5)
                if resp.status == 200:
                    return port
            except Exception:
                continue
    return 0


def _ensure_gui_and_create_session(session, provider_name: str,
                                    tool_dir: str, mode: str) -> tuple:
    """Ensure the GUI server is running and create a session tab.

    Returns (gui_url, gui_base_url, gui_session_id) tuple.
    All empty strings on failure.
    """
    import urllib.request

    port = _find_running_gui_port()
    if not port:
        try:
            from logic.assistant.gui.server import start_server
            from tool.LLM.logic.config import get_config_value
            lang = get_config_value("lang", "en")
            agent = start_server(
                selected_model=provider_name,
                port=0,
                open_browser=True,
                enable_tools=True,
                default_codebase=tool_dir or None,
                lang=lang,
            )
            port = agent.port
        except Exception:
            return ("", "", "")

    base_url = f"http://localhost:{port}"
    try:
        data = json.dumps({
            "title": getattr(session, 'initial_prompt', 'New Task')[:60],
            "mode": mode,
            "self_operate": True,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/api/sessions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        if resp.get("ok"):
            sid = resp["session_id"]
            return (f"{base_url}/#session={sid}", base_url, sid)
    except Exception:
        pass
    return (base_url, "", "")


class _GuiEventInjector:
    """Asynchronous event injector — batches events and POSTs in background."""

    def __init__(self, inject_url: str):
        import threading
        import queue as _q
        self._url = inject_url
        self._batch_url = inject_url.replace("/inject", "/inject-batch")
        self._queue: _q.Queue = _q.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def push(self, evt: dict):
        self._queue.put(evt)

    def flush_and_stop(self):
        self._stop.set()
        self._thread.join(timeout=5)
        self._drain()

    def _worker(self):
        import time
        while not self._stop.is_set():
            time.sleep(0.15)
            self._drain()

    def _drain(self):
        import urllib.request
        batch = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except Exception:
                break
        if not batch:
            return
        try:
            payload = json.dumps(
                {"events": batch}, ensure_ascii=False).encode()
            req = urllib.request.Request(
                self._batch_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass


def _gui_inject_event(inject_url: str, evt: dict):
    """POST a single event to the GUI server for live SSE broadcasting."""
    import urllib.request
    try:
        payload = json.dumps({"event": evt}, ensure_ascii=False).encode()
        req = urllib.request.Request(
            inject_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def _find_gui_inject_url_for_session(session_id: str) -> str:
    """Find the GUI inject URL for a session that may already exist on the server."""
    import urllib.request
    port = _find_running_gui_port()
    if not port:
        return ""
    base = f"http://localhost:{port}"
    try:
        resp = json.loads(
            urllib.request.urlopen(f"{base}/api/sessions", timeout=3).read())
        for s in resp.get("sessions", []):
            if s.get("id", "").startswith(session_id) or session_id.startswith(s.get("id", "")):
                return f"{base}/api/session/{s['id']}/inject"
    except Exception:
        pass
    return ""


def _execute_tool_via_api(base_url: str, session_id: str,
                          tool_name: str, tool_args: dict) -> dict:
    """Execute a tool call via the GUI server's API (placeholder).

    Currently, tool calls are handled by ConversationManager internally.
    This sends the tool result back as a structured event.
    """
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET", "\033[0m")

    from logic.assistant.std.registry import ToolContext, STANDARD_TOOLS
    import logic.assistant.std.tools  # noqa: F401 — ensure tools are registered
    handler = STANDARD_TOOLS.get(tool_name)
    if not handler:
        return {"type": "tool_result", "ok": False,
                "output": f"Unknown tool: {tool_name}"}

    results = []
    def emit(evt):
        results.append(evt)
        _print_event(evt)

    cwd = os.getcwd()
    ctx = ToolContext(
        emit=emit,
        cwd=cwd,
        project_root=os.environ.get("PROJECT_ROOT", cwd),
    )
    result = handler(tool_args, ctx)
    return {"type": "tool_result", "ok": result.get("ok", False),
            "output": result.get("output", "")}


def _handle_history(args: list, project_root: str):
    """Show recent N events for a session in CLI format."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    CYAN = get_color("CYAN", "\033[36m")
    RESET = get_color("RESET", "\033[0m")

    limit = 20
    session_id = None
    i = 0
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            try:
                limit = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        else:
            if not session_id:
                session_id = args[i]
            i += 1

    import urllib.request
    port = _find_running_gui_port()
    if not port:
        if not session_id:
            print(f"  {BOLD}No running GUI server.{RESET} Provide a session ID to load from disk.")
            return
        events = _load_events_from_disk(session_id, project_root)
        if events is None:
            print(f"  {BOLD}Session not found.{RESET} {DIM}{session_id}{RESET}")
            return
    else:
        base_url = f"http://localhost:{port}"
        if not session_id:
            try:
                state = json.loads(
                    urllib.request.urlopen(f"{base_url}/api/state", timeout=3).read())
                session_id = state.get("state", {}).get("active_session")
                if not session_id:
                    sessions = json.loads(
                        urllib.request.urlopen(f"{base_url}/api/sessions", timeout=3).read())
                    slist = sessions.get("sessions", [])
                    if slist:
                        session_id = slist[-1]["id"]
            except Exception:
                pass
        if not session_id:
            print(f"  {BOLD}No active session.{RESET}")
            return

        try:
            full_sid = session_id
            resp = json.loads(
                urllib.request.urlopen(
                    f"{base_url}/api/history/{session_id}", timeout=5).read())
            events = resp.get("events", [])
        except Exception:
            events = _load_events_from_disk(session_id, project_root) or []

    total = len(events)
    recent = events[-limit:] if len(events) > limit else events
    print(f"  {BOLD}History{RESET} for {DIM}{session_id}{RESET} "
          f"({len(recent)}/{total} events)")
    print()

    text_buf = ""
    for evt in recent:
        etype = evt.get("type", "")
        if etype == "text":
            text_buf += evt.get("tokens", "")
            continue
        if text_buf:
            for line in text_buf.strip().split("\n")[:30]:
                print(f"  {line}")
            text_buf = ""
        _print_event(evt)
    if text_buf:
        for line in text_buf.strip().split("\n")[:30]:
            print(f"  {line}")


def _load_events_from_disk(session_id: str, project_root: str):
    """Load events from a persisted session file.

    Supports both new layout (``<id>/history.json``) and legacy (``<id>.json``).
    """
    sessions_dir = os.path.join(project_root, "runtime", "sessions")
    if not os.path.isdir(sessions_dir):
        return None
    import glob
    for path in glob.glob(os.path.join(sessions_dir, "*/history.json")):
        dir_name = os.path.basename(os.path.dirname(path))
        if dir_name.startswith(session_id):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("events", [])
    for path in glob.glob(os.path.join(sessions_dir, "*.json")):
        basename = os.path.basename(path).replace(".json", "")
        if basename.startswith(session_id):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("events", [])
    return None


def _handle_config(args: list, project_root: str):
    """View/set assistant configuration values."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")

    try:
        from tool.LLM.logic.config import load_config, save_config
    except ImportError:
        print(f"  {BOLD}LLM tool not available.{RESET}")
        return

    cfg = load_config()

    ASSISTANT_KEYS = {
        "active_backend": "Active model/provider (e.g. zhipu-glm-4.7-flash, auto)",
        "default_turn_limit": "Default max rounds per task (int, default: 20)",
        "max_input_tokens": "Max input tokens per API call (int, default: 65536)",
        "max_output_tokens": "Max output tokens per API call (int, default: 16384)",
        "max_context_tokens": "Max context window tokens before trimming (int, default: 1048576)",
        "max_read_chars": "Max chars returned by read_file (int, default: 12000)",
        "max_exec_chars": "Max chars returned by exec (int, default: 6000)",
        "language": "System prompt language (zh/en, default: zh)",
        "history_limit": "Default events shown by --history (int, default: 20)",
    }

    if not args:
        print(f"  {BOLD}Assistant Configuration{RESET}")
        print()
        for key, desc in ASSISTANT_KEYS.items():
            val = cfg.get(key, "")
            if val:
                print(f"  {BOLD}{key}{RESET} = {GREEN}{val}{RESET}")
            else:
                print(f"  {BOLD}{key}{RESET} = {DIM}(not set){RESET}")
            print(f"    {DIM}{desc}{RESET}")
        return

    key = args[0]
    if len(args) == 1:
        val = cfg.get(key)
        if val is not None:
            print(f"  {BOLD}{key}{RESET} = {GREEN}{val}{RESET}")
        else:
            print(f"  {BOLD}{key}{RESET} = {DIM}(not set){RESET}")
        if key in ASSISTANT_KEYS:
            print(f"  {DIM}{ASSISTANT_KEYS[key]}{RESET}")
        return

    value = " ".join(args[1:])
    int_keys = {"default_turn_limit", "max_input_tokens", "max_output_tokens",
                "max_context_tokens", "max_read_chars", "max_exec_chars",
                "history_limit"}
    if key in int_keys:
        try:
            value = int(value)
        except ValueError:
            print(f"  {BOLD}Invalid value.{RESET} {DIM}{key} requires an integer.{RESET}")
            return

    cfg[key] = value
    save_config(cfg)
    print(f"  {BOLD}Saved.{RESET} {DIM}{key} = {value}{RESET}")


def _handle_status(args: list, project_root: str, tool_dir: str = ""):
    """Show session status."""
    if args:
        session = load_session(args[0], project_root, tool_dir=tool_dir)
        if session:
            print(json.dumps(session.to_dict(), indent=2))
        else:
            print(f"Session {args[0]} not found.")
    else:
        sessions = list_sessions(project_root, tool_dir=tool_dir)
        if not sessions:
            print("No agent sessions found.")
            return
        latest = sessions[0]
        print(json.dumps(latest, indent=2))


def _handle_sessions(project_root: str, tool_dir: str = ""):
    """List all agent sessions."""
    sessions = list_sessions(project_root, tool_dir=tool_dir)
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


def _print_dry_run(session: AgentSession, user_text: str,
                   tool_name: str, project_root: str,
                   mode: str, provider_name: str):
    """Display the full prompt that would be sent to the LLM, without executing."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    YELLOW = get_color("YELLOW", "\033[33m")
    CYAN = get_color("CYAN", "\033[36m")
    RESET = get_color("RESET", "\033[0m")

    system_prompt = _get_system_prompt(tool_name, mode=mode)
    from logic.agent.context import build_context
    packaged = build_context(
        session, user_text, tier=session.tier or 2,
        project_root=project_root)

    label = MODE_LABELS.get(mode, "Agent")
    is_new = session.message_count <= 0

    print(f"\n  {YELLOW}{BOLD}[DRY RUN]{RESET} {label} mode | Provider: {provider_name}")
    print(f"  {DIM}Session: {session.id} | "
          f"{'New session' if is_new else f'Existing ({session.message_count} msgs)'} | "
          f"CWD: {session.codebase_root}{RESET}")
    print()

    print(f"  {CYAN}{BOLD}═══ SYSTEM PROMPT ({len(system_prompt)} chars) ═══{RESET}")
    for line in system_prompt.split("\n"):
        print(f"  {DIM}{line}{RESET}")
    print()

    print(f"  {CYAN}{BOLD}═══ USER MESSAGE ({len(packaged)} chars) ═══{RESET}")
    for line in packaged.split("\n"):
        print(f"  {line}")
    print()

    from logic.agent.tools import get_tool_defs_for_mode
    tools = get_tool_defs_for_mode(mode)
    tool_names = [t["function"]["name"] for t in tools if "function" in t]
    print(f"  {CYAN}{BOLD}═══ TOOLS ({len(tool_names)}) ═══{RESET}")
    for name in tool_names:
        print(f"  {DIM}- {name}{RESET}")

    total_chars = len(system_prompt) + len(packaged)
    est_tokens = total_chars // 4
    print(f"\n  {DIM}Estimated input: ~{est_tokens} tokens ({total_chars} chars){RESET}")
    print(f"  {YELLOW}{BOLD}No LLM call was made.{RESET}")


def _print_event(evt: dict):
    """Print an agent event to the console."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    YELLOW = get_color("YELLOW", "\033[33m")
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
    elif t == "llm_response_start":
        r = evt.get("round", "?")
        print(f"  {DIM}[Round {r} start]{RESET}")
    elif t == "llm_response_end":
        latency = evt.get("latency_s", 0)
        has_tc = evt.get("has_tool_calls", False)
        provider = evt.get("provider", "")
        tc_label = " (tool calls)" if has_tc else ""
        prov_label = f" via {provider}" if provider else ""
        print(f"  {DIM}[{latency}s{tc_label}{prov_label}]{RESET}")
    elif t == "user":
        prompt = evt.get("prompt", "")
        if prompt:
            print(f"\n  {BOLD}User:{RESET} {prompt[:120]}")
    elif t == "complete":
        reason = evt.get("reason", "done")
        if reason == "error":
            print(f"  {RED}{BOLD}Task failed.{RESET}")
        elif reason == "cancelled":
            print(f"  {YELLOW}{BOLD}Task cancelled.{RESET}")
        elif reason == "round_limit":
            print(f"  {YELLOW}{BOLD}Round limit reached.{RESET}")
        else:
            print(f"  {GREEN}{BOLD}Task completed.{RESET}")
    elif t == "file_summary":
        files = evt.get("files", [])
        count = len(files)
        print(f"  {DIM}[{count} file{'s' if count != 1 else ''} modified]{RESET}")
    elif t == "system_notice":
        text = evt.get("text", "")
        level = evt.get("level", "info")
        if level == "error":
            YELLOW = get_color("YELLOW", "\033[33m")
            print(f"  {YELLOW}{BOLD}{text}{RESET}")
        else:
            print(f"  {DIM}{text}{RESET}")
    elif t == "debug":
        text = evt.get("text", "")
        print(f"  {DIM}[debug] {text}{RESET}")
    elif t == "experience":
        lesson = evt.get("lesson", "")
        print(f"  {DIM}[experience] {lesson[:100]}{RESET}")


# ─── --assistant CLI: wraps GUI HTTP API for programmatic control ──────────

def _assistant_api(port: int, method: str, path: str, body: dict = None) -> dict:
    """Call the GUI API and return parsed JSON response."""
    import urllib.request
    url = f"http://localhost:{port}{path}"
    data = json.dumps(body or {}).encode() if method != "GET" else None
    req = urllib.request.Request(url, data=data, method=method,
                                headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_assistant_command(args: list, tool_name: str = "TOOL"):
    """Handle --assistant subcommands that control the GUI via HTTP API.

    Subcommands:
        list                         List sessions
        state [SID]                  Show session state
        history <SID> [--limit N]    Show event history
        send <SID> "prompt"          Send a message
        model <model_id>             Switch model
        accept <SID> <hunk_index>    Accept an edit hunk
        revert <SID> <hunk_index>    Revert an edit hunk
        accept-all <SID>             Accept all undecided hunks
        revert-all <SID>             Revert all undecided hunks
        edits <SID>                  List edit blocks
        new [title]                  Create new session
        delete <SID>                 Delete session
        clear                        Delete all sessions + create fresh one
        cancel                       Cancel running task
    """
    port = _find_running_gui_port()
    if not port:
        print("No GUI server found. Start with: TOOL --agent --gui")
        return

    if not args:
        _assistant_help(tool_name)
        return

    subcmd = args[0]
    rest = args[1:]

    if subcmd == "list":
        r = _assistant_api(port, "GET", "/api/sessions")
        if r.get("ok"):
            for s in r.get("sessions", []):
                status = s.get("status", "?")
                print(f"  {s['id']}  {status:<8}  {s.get('title', '')}")
        else:
            print(f"Error: {r.get('error')}")

    elif subcmd == "state":
        sid = rest[0] if rest else ""
        r = _assistant_api(port, "GET", "/api/state")
        if r.get("ok"):
            state = r["state"]
            sessions = state.get("sessions", {})
            if sid and sid in sessions:
                s = sessions[sid]
                print(json.dumps(s, indent=2, ensure_ascii=False))
            elif sid:
                print(f"Session {sid} not found")
            else:
                print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print(f"Error: {r.get('error')}")

    elif subcmd == "history":
        if not rest:
            print("Usage: --assistant history <SID> [--limit N]")
            return
        sid = rest[0]
        limit = 50
        if "--limit" in rest:
            idx = rest.index("--limit")
            if idx + 1 < len(rest):
                limit = int(rest[idx + 1])
        r = _assistant_api(port, "GET", f"/api/session/{sid}/history")  # RESTful
        if r.get("ok"):
            events = r.get("events", [])
            for evt in events[-limit:]:
                t = evt.get("type", "")
                if t == "user":
                    print(f"  USER: {evt.get('prompt', '')[:120]}")
                elif t == "text":
                    pass
                elif t == "tool":
                    print(f"  TOOL: {evt.get('name', '')} | {evt.get('desc', '')[:80]}")
                elif t == "tool_result":
                    ok = evt.get("ok")
                    name = evt.get("name", "")
                    out = (evt.get("output", "") or "")[:100]
                    print(f"  RESULT: ok={ok} name={name} | {out}")
                elif t in ("llm_request", "llm_response_end", "model_info"):
                    model = evt.get("model", "")
                    tokens = evt.get("tokens", "")
                    if t == "model_info":
                        print(f"  MODEL: {model} {tokens}tok")
                    elif t == "llm_response_end":
                        print(f"  LLM_END: {model}")
                elif t in ("task_completed", "task_cancelled"):
                    print(f"  {t.upper()}")
                elif t == "file_summary":
                    files = evt.get("files", [])
                    print(f"  FILE_SUMMARY: {len(files)} files")
        else:
            print(f"Error: {r.get('error')}")

    elif subcmd == "send":
        if len(rest) < 2:
            print("Usage: --assistant send <SID> \"prompt text\"")
            return
        sid = rest[0]
        text = " ".join(rest[1:])
        r = _assistant_api(port, "POST", f"/api/session/{sid}/send",
                         {"text": text})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "model":
        if not rest:
            print("Usage: --assistant model <model_id>")
            return
        model = rest[0]
        r = _assistant_api(port, "POST", "/api/model/switch", {"model": model})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "edits":
        if not rest:
            print("Usage: --assistant edits <SID>")
            return
        sid = rest[0]
        r = _assistant_api(port, "GET", f"/api/session/{sid}/edit")
        if r.get("ok"):
            blocks = r.get("blocks", [])
            print(f"Edit blocks: {len(blocks)}")
            for b in blocks:
                status = b.get("decision") or "undecided"
                path = b.get("path", "")
                print(f"  [{b['index']}] {status:<10} {b['tool']:<10} {path}")
                if b.get("old_text_preview"):
                    print(f"       old: {b['old_text_preview']}")
                if b.get("new_text_preview"):
                    print(f"       new: {b['new_text_preview']}")
        else:
            print(f"Error: {r.get('error')}")

    elif subcmd == "accept":
        if len(rest) < 2:
            print("Usage: --assistant accept <SID> <hunk_index>")
            return
        sid = rest[0]
        idx = int(rest[1])
        r = _assistant_api(port, "POST", f"/api/session/{sid}/edit/{idx}",
                         {"action": "accept"})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "revert":
        if len(rest) < 2:
            print("Usage: --assistant revert <SID> <hunk_index>")
            return
        sid = rest[0]
        idx = int(rest[1])
        r = _assistant_api(port, "POST", f"/api/session/{sid}/edit/{idx}",
                         {"action": "revert"})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "accept-all":
        if not rest:
            print("Usage: --assistant accept-all <SID>")
            return
        sid = rest[0]
        edits = _assistant_api(port, "GET", f"/api/session/{sid}/edit")
        if not edits.get("ok"):
            print(f"Error: {edits.get('error')}")
            return
        accepted = 0
        for b in edits.get("blocks", []):
            if not b["decided"]:
                r = _assistant_api(port, "POST",
                                 f"/api/session/{sid}/edit/{b['index']}",
                                 {"action": "accept"})
                if r.get("ok"):
                    accepted += 1
        print(f"Accepted {accepted} hunks")

    elif subcmd == "revert-all":
        if not rest:
            print("Usage: --assistant revert-all <SID>")
            return
        sid = rest[0]
        edits = _assistant_api(port, "GET", f"/api/session/{sid}/edit")
        if not edits.get("ok"):
            print(f"Error: {edits.get('error')}")
            return
        reverted = 0
        for b in reversed(edits.get("blocks", [])):
            if not b["decided"]:
                r = _assistant_api(port, "POST",
                                 f"/api/session/{sid}/edit/{b['index']}",
                                 {"action": "revert"})
                if r.get("ok"):
                    reverted += 1
        print(f"Reverted {reverted} hunks")

    elif subcmd == "new":
        title = " ".join(rest) if rest else "New Task"
        r = _assistant_api(port, "POST", "/api/sessions", {"title": title})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "delete":
        if not rest:
            print("Usage: --assistant delete <SID>")
            return
        r = _assistant_api(port, "DELETE", f"/api/session/{rest[0]}", {})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "clear":
        r = _assistant_api(port, "DELETE", "/api/sessions", {})
        print(json.dumps(r, ensure_ascii=False))

    elif subcmd == "cancel":
        r = _assistant_api(port, "POST", "/api/session/default/cancel", {})
        print(json.dumps(r, ensure_ascii=False))

    else:
        print(f"Unknown --assistant subcommand: {subcmd}")
        _assistant_help(tool_name)


def _assistant_help(tool_name: str = "TOOL"):
    print(f"""
Assistant Control (wraps GUI HTTP API)

Sessions:
  {tool_name} --assistant list                         List sessions
  {tool_name} --assistant new [title]                  Create new session
  {tool_name} --assistant delete <SID>                 Delete session
  {tool_name} --assistant clear                        Delete all + create fresh

Communication:
  {tool_name} --assistant send <SID> "prompt"          Send a message
  {tool_name} --assistant state [SID]                  Show session state
  {tool_name} --assistant history <SID> [--limit N]    Show event history
  {tool_name} --assistant cancel                       Cancel running task

Edit control:
  {tool_name} --assistant edits <SID>                  List edit blocks
  {tool_name} --assistant accept <SID> <index>         Accept a hunk
  {tool_name} --assistant revert <SID> <index>         Revert a hunk
  {tool_name} --assistant accept-all <SID>             Accept all undecided
  {tool_name} --assistant revert-all <SID>             Revert all undecided

Model:
  {tool_name} --assistant model <model_id>             Switch model

Endpoint (structured JSON, mirrors API paths):
  {tool_name} --assistant --endpoint --sessions
  {tool_name} --assistant --endpoint --session <SID> --state
  {tool_name} --assistant --endpoint --model --list
  {tool_name} --assistant --endpoint --key --validate <key>

API paths:
  GET    /api/sessions                   POST /api/sessions
  GET    /api/session/<sid>/state        DELETE /api/session/<sid>
  POST   /api/session/<sid>/send         GET  /api/session/<sid>/history
  GET    /api/session/<sid>/edit         POST /api/session/<sid>/edit/<idx>
  POST   /api/model/switch              GET  /api/model/list
  POST   /api/key/{{validate,save,delete,states,reverify}}
""")


# ── --assistant --endpoint ────────────────────────────────────────────

_PATH_PARAM_KEYS = {"session", "edit"}

_POST_SUFFIXES = {
    "send", "cancel", "rename", "activate", "switch", "validate",
    "save", "delete", "states", "reverify", "check", "resolve",
    "inject", "inject-batch", "input", "audit",
}

_BODY_PARAM_MAP = {
    "send": "text",
    "switch": "model",
    "validate": "key",
    "delete": "provider",
    "reverify": "provider",
    "rename": "title",
}


def handle_assistant_endpoint(args: list, tool_name: str = "TOOL"):
    """Route ``--assistant --endpoint`` commands to the GUI HTTP API.

    Builds an API path from ``--flag`` args and dispatches the request.
    Non-flag args are treated as path parameters (for ``--session``,
    ``--edit``) or request body values.

    Examples::

        --sessions                         → GET  /api/sessions
        --session <SID> --state            → GET  /api/session/<SID>/state
        --session <SID> --send "hello"     → POST /api/session/<SID>/send
        --model --switch gpt-4             → POST /api/model/switch
        --model --list                     → GET  /api/model/list
        --key --validate sk-xxx            → POST /api/key/validate
        --key --states                     → POST /api/key/states
        --state                            → GET  /api/state
        --usage                            → GET  /api/usage
        --health                           → GET  /api/health
        --brain --blueprints               → GET  /api/brain/blueprints
        --sandbox --state                  → GET  /api/sandbox/state
    """
    if not args:
        _endpoint_help(tool_name)
        return

    port = _find_running_gui_port()
    if not port:
        print(json.dumps({"ok": False, "error": "No GUI server found. Start with: TOOL --agent --gui"}))
        return

    segments = []
    data_args = []
    method_override = None

    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if key == "delete-method":
                method_override = "DELETE"
                i += 1
                continue
            segments.append(key)
            if key in _PATH_PARAM_KEYS and i + 1 < len(args) and not args[i + 1].startswith("--"):
                segments.append(args[i + 1])
                i += 2
                continue
        else:
            data_args.append(a)
        i += 1

    if not segments:
        _endpoint_help(tool_name)
        return

    api_path = "/api/" + "/".join(segments)
    last_seg = segments[-1] if segments else ""

    is_edit_action = ("edit" in segments and data_args
                      and data_args[0] in ("accept", "revert"))

    if method_override:
        method = method_override
    elif last_seg in _POST_SUFFIXES or is_edit_action:
        method = "POST"
    else:
        method = "GET"

    body = None
    if is_edit_action:
        body = {"action": data_args[0]}
    elif method == "POST" and data_args:
        try:
            body = json.loads(data_args[0])
        except (json.JSONDecodeError, IndexError):
            param_key = _BODY_PARAM_MAP.get(last_seg, "value")
            body = {param_key: " ".join(data_args)}
    elif method == "POST":
        body = {}

    r = _assistant_api(port, method, api_path, body)
    print(json.dumps(r, indent=2, ensure_ascii=False))


def _endpoint_help(tool_name: str = "TOOL"):
    print(f"""
Assistant Endpoint (structured JSON, mirrors API paths)

Usage: {tool_name} --assistant --endpoint --<path> [--<sub>] [args]

System:
  --state                              Full system state
  --health                             Health check
  --usage                              Usage data

Sessions:
  --sessions                           List sessions (GET)
  --session <SID> --state              Session state
  --session <SID> --history            Event history
  --session <SID> --send "prompt"      Send message (POST)
  --session <SID> --cancel             Cancel running task (POST)
  --session <SID> --rename "title"     Rename session (POST)
  --session <SID> --activate           Set as active (POST)
  --session <SID> --edit               List edit blocks
  --session <SID> --edit <IDX> accept  Accept/revert hunk (POST)

Model:
  --model --list                       Configured models
  --model --switch <model_id>          Switch model (POST)

Keys:
  --key --validate <key>               Validate API key (POST)
  --key --save '{{"provider":...}}'      Save API key (POST)
  --key --delete <provider>            Delete API key (POST)
  --key --states                       Get key states (POST)
  --key --reverify <provider>          Reverify key (POST)

Brain:
  --brain --blueprints                 List brain blueprints
  --brain --instances                  List brain instances
  --brain --active                     Active brain info

Sandbox:
  --sandbox --state                    Sandbox state
  --sandbox --check '{{}}'               Check command (POST)
  --sandbox --resolve '{{}}'             Resolve pending (POST)

Deletion:
  --session <SID> --delete-method      Delete session (DELETE)
  --sessions --delete-method           Clear all sessions (DELETE)

Path mapping: --key --validate → POST /api/key/validate
""")
