#!/usr/bin/env python3
"""OPENCLAW — Agent autonomy framework with multi-backend LLM integration.

Supports LLM backends:
  - nvidia_glm47: GLM-4.7 via NVIDIA Build API (free tier)
  - zhipu_glm4:   GLM-4-Flash via Zhipu AI (free tier)

Usage:
    OPENCLAW              Show help
    OPENCLAW cli          Interactive terminal agent
    OPENCLAW status       Check LLM provider and connection status
    OPENCLAW sessions     List saved sessions
    OPENCLAW setup-llm    Configure API keys
"""
import sys
import os
import argparse
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color

VALID_BACKENDS = ("nvidia-glm-4-7b", "zhipu-glm-4-flash")

_CONFIG_FILE = Path(__file__).resolve().parent / "data" / "config.json"

def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        import json
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_config(cfg: dict):
    import json
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def cmd_setup_llm(args):
    """Configure the NVIDIA GLM-4.7 API key (one-time setup)."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    get_color("BLUE")
    RESET = get_color("RESET")

    print(f"  {BOLD}OPENCLAW LLM Setup{RESET}")
    print()
    print(f"  This configures GLM-4.7 via NVIDIA Build (free tier).")
    print(f"  Get your API key from: https://build.nvidia.com/z-ai/glm4_7")
    print()

    from tool.LLM.logic.providers.nvidia_glm47 import (
        get_api_key, save_api_key, NvidiaGLM47Provider
    )

    current = get_api_key()
    if current:
        masked = current[:8] + "..." + current[-4:] if len(current) > 12 else "***"
        print(f"  Current key: {masked}")
        print()

    api_key = input("  Enter NVIDIA API key (or press Enter to keep current): ").strip()
    if api_key:
        save_api_key(api_key)
        print(f"  {BOLD}{GREEN}Saved{RESET} API key.")
    elif not current:
        print(f"  No API key configured. Set NVIDIA_API_KEY env var or run setup-llm again.")
        return

    provider = NvidiaGLM47Provider()
    info = provider.get_info()
    avail = f"{GREEN}yes{RESET}" if info["available"] else f"{BOLD}no{RESET}"
    print(f"  {BOLD}Provider{RESET}: {info['model']}")
    print(f"  {BOLD}Available{RESET}: {avail}")
    print(f"  {BOLD}RPM limit{RESET}: {info['rpm_limit']}")
    print(f"  {BOLD}Max context{RESET}: {info['max_context']:,} tokens")


def _make_core(args) -> "OpenClawCore":
    """Create the shared OpenClawCore instance used by all GUI modes."""
    from tool.OPENCLAW.logic.core import OpenClawCore
    from tool.LLM.logic.config import get_config_value
    from tool.LLM.logic.registry import _ALIASES
    data_dir = Path(__file__).resolve().parent / "data"
    cfg = _load_config()
    saved_backend = get_config_value("active_backend")
    if saved_backend and saved_backend in _ALIASES:
        saved_backend = _ALIASES[saved_backend]
    explicit = getattr(args, "backend", None)
    backend = explicit or saved_backend or "nvidia-glm-4-7b"
    core = OpenClawCore(
        data_dir=data_dir,
        backend=backend,
        log_limit=cfg.get("log_limit", 1024),
    )
    return core


def cmd_cli(args):
    """Launch the interactive terminal agent."""
    from tool.OPENCLAW.logic.gui.cli import OpenClawCLI

    core = _make_core(args)
    cli = OpenClawCLI(
        session_mgr=core.session_mgr,
        backend=core.backend,
        cdp_port=args.port,
        core=core,
    )
    cli.run()


def cmd_chat(args):
    """Launch the OPENCLAW chatbot GUI."""
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    backend = getattr(args, "backend", "nvidia-glm-4-7b")
    gui_mode = getattr(args, "gui", "html")

    if gui_mode == "tkinter":
        print(f"  {BOLD}{BLUE}Launching{RESET} OPENCLAW chatbot (tkinter)...")
        from logic.gui.engine import get_safe_python_for_gui
        import tempfile

        python_exe = get_safe_python_for_gui()
        project_root = str(Path(__file__).resolve().parent.parent.parent)
        cdp_port = args.port

        gui_script = f'''
import sys
sys.path.insert(0, {project_root!r})
from interface.resolve import setup_paths
setup_paths({str(Path(__file__).resolve())!r})

from tool.OPENCLAW.logic.session import SessionManager
from tool.OPENCLAW.logic.gui.chat import OpenClawChat
from pathlib import Path

data_dir = Path({str(Path(__file__).resolve().parent)!r}) / "data"
data_dir.mkdir(exist_ok=True)

session_mgr = SessionManager(data_dir)
chat = OpenClawChat(session_mgr, cdp_port={cdp_port})
chat.run()
'''
        with tempfile.NamedTemporaryFile(mode='w', prefix='OPENCLAW_chat_',
                                          suffix='.py', delete=False) as tmp:
            tmp.write(gui_script)
            tmp_path = tmp.name

        try:
            import subprocess
            subprocess.run([python_exe, tmp_path], capture_output=False)
        finally:
            import os
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    else:
        print(f"  {BOLD}{BLUE}Launching{RESET} OPENCLAW chatbot ({backend})...", flush=True)
        from tool.OPENCLAW.logic.session import SessionManager
        from tool.OPENCLAW.logic.gui.chat_html import OpenClawChatHTML

        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(exist_ok=True)

        session_mgr = SessionManager(data_dir)
        chat = OpenClawChatHTML(session_mgr, cdp_port=args.port,
                                backend=backend)
        chat.run()


def cmd_status(args):
    """Check LLM provider and connection status."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.LLM.logic.registry import list_providers
    from tool.LLM.logic.config import get_config_value

    providers = list_providers()
    active = get_config_value("active_backend", "nvidia-glm-4-7b")

    print(f"  {BOLD}LLM Providers{RESET}:")
    for p in providers:
        avail = f"{GREEN}available{RESET}" if p["available"] else f"{RED}not configured{RESET}"
        marker = " *" if p["name"] == active else ""
        print(f"    {BOLD}{p['name']}{RESET}: {avail} "
              f"({p.get('model', '?')}, {p.get('rpm_limit', '?')} RPM){marker}")
    print()
    print(f"  {BOLD}Active backend{RESET}: {active}")


def cmd_sessions(args):
    """List saved sessions."""
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    from tool.OPENCLAW.logic.session import SessionManager

    data_dir = Path(__file__).resolve().parent / "data"
    session_mgr = SessionManager(data_dir)
    sessions = session_mgr.list_sessions()

    if not sessions:
        print(f"  No sessions found.")
        return

    print(f"  {BOLD}Sessions{RESET} ({len(sessions)}):")
    for s in sessions[:20]:
        title = s.get_display_title()
        msg_count = len(s.messages)
        status = s.status
        import time as _t
        ts = _t.strftime("%m-%d %H:%M", _t.localtime(s.updated_at))
        print(f"    [{s.id}] {title} ({msg_count} msgs, {status}, {ts})")


_RUN_DIR = Path(__file__).resolve().parent / "data" / "run"


def cmd_cli_status(args):
    """Query a running CLI instance's state by PID."""
    import json as _json
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    DIM = get_color("DIM")
    RESET = get_color("RESET")

    pid = args.pid
    state_file = _RUN_DIR / f"cli_{pid}.json"
    if not state_file.exists():
        print(f"  {RED}No running CLI found for PID {pid}.{RESET}")
        available = sorted(_RUN_DIR.glob("cli_*.json"))
        if available:
            print(f"  {DIM}Active CLIs:{RESET}")
            for f in available:
                try:
                    d = _json.loads(f.read_text())
                    print(f"    PID {d['pid']}: {d['status']} ({d.get('ts', '?')})")
                except Exception:
                    pass
        return

    state = _json.loads(state_file.read_text())
    status_color = GREEN if state["status"] == "idle" else BOLD
    print(f"  {BOLD}CLI Status{RESET} (PID {pid})")
    print(f"    Status:   {status_color}{state['status']}{RESET}")
    if state.get("detail"):
        print(f"    Detail:   {state['detail']}")
    print(f"    Backend:  {state.get('backend', '?')}")
    print(f"    Session:  {state.get('session_id') or 'none'}")
    print(f"    Updated:  {state.get('ts', '?')}")


def cmd_cli_inject(args):
    """Inject a command into a running CLI instance."""
    RED = get_color("RED")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    pid = args.pid
    state_file = _RUN_DIR / f"cli_{pid}.json"
    ctrl_file = _RUN_DIR / f"cli_{pid}.cmd"

    if not state_file.exists():
        print(f"  {RED}No running CLI found for PID {pid}.{RESET}")
        return

    command = " ".join(args.inject_args)
    if not command:
        print(f"  {RED}No command provided.{RESET}")
        return

    _RUN_DIR.mkdir(parents=True, exist_ok=True)
    ctrl_file.write_text(command)
    print(f"  {GREEN}Injected{RESET} into PID {pid}: {command}")


def cmd_cli_list(_args):
    """List all running CLI instances."""
    import json as _json
    BOLD = get_color("BOLD")
    DIM = get_color("DIM")
    RESET = get_color("RESET")

    available = sorted(_RUN_DIR.glob("cli_*.json")) if _RUN_DIR.exists() else []
    if not available:
        print(f"  {DIM}No active CLI instances.{RESET}")
        return

    print(f"  {BOLD}Active CLI instances:{RESET}")
    for f in available:
        try:
            d = _json.loads(f.read_text())
            print(f"    PID {d['pid']}: {d['status']}"
                  f" | backend={d.get('backend', '?')}"
                  f" | {d.get('ts', '?')}")
        except Exception:
            pass


_CONFIG_KEYS = {
    "log_limit": ("int", 1024, "Max operation logs per session (deletes half when exceeded)."),
}

def cmd_config(args):
    """View or set OPENCLAW configuration."""
    BOLD = get_color("BOLD")
    DIM = get_color("DIM")
    CYAN = get_color("CYAN")
    get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    cfg = _load_config()

    if not args.key:
        print(f"  {BOLD}OPENCLAW Config{RESET}")
        for key, (typ, default, desc) in _CONFIG_KEYS.items():
            val = cfg.get(key, default)
            print(f"    {CYAN}{key}{RESET} = {BOLD}{val}{RESET}  {DIM}({desc}){RESET}")
        print(f"\n  {DIM}Set: OPENCLAW config <key> <value>{RESET}")
        return

    key = args.key
    if key not in _CONFIG_KEYS:
        print(f"  {RED}{BOLD}Unknown key:{RESET} {key}")
        print(f"  {DIM}Available: {', '.join(_CONFIG_KEYS.keys())}{RESET}")
        return

    if not args.value:
        typ, default, desc = _CONFIG_KEYS[key]
        val = cfg.get(key, default)
        print(f"  {CYAN}{key}{RESET} = {BOLD}{val}{RESET}  {DIM}({desc}){RESET}")
        return

    typ, default, desc = _CONFIG_KEYS[key]
    try:
        if typ == "int":
            val = int(args.value)
        elif typ == "bool":
            val = args.value.lower() in ("true", "1", "yes")
        else:
            val = args.value
    except ValueError:
        print(f"  {RED}{BOLD}Invalid value:{RESET} expected {typ}.")
        return

    cfg[key] = val
    _save_config(cfg)
    print(f"  {BOLD}Set{RESET} {CYAN}{key}{RESET} = {BOLD}{val}{RESET}.")


def cmd_sandbox(args):
    """View or set sandbox command policies."""
    BOLD = get_color("BOLD")
    DIM = get_color("DIM", "\033[2m")
    CYAN = get_color("CYAN", "\033[36m")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.OPENCLAW.logic.sandbox import (
        list_policies, set_command_policy, remove_command_policy,
        ALLOWED_COMMANDS, BLOCKED_COMMANDS,
    )

    if args.sandbox_cmd and args.sandbox_policy:
        cmd_name = args.sandbox_cmd
        policy = args.sandbox_policy
        if policy == "remove":
            removed = remove_command_policy(cmd_name)
            if removed:
                print(f"  {BOLD}Removed{RESET} policy for {CYAN}{cmd_name}{RESET}.")
            else:
                print(f"  {DIM}No policy set for {cmd_name}.{RESET}")
        else:
            set_command_policy(cmd_name, policy)
            print(f"  {BOLD}Set{RESET} {CYAN}{cmd_name}{RESET} = {BOLD}{policy}{RESET}.")
        return

    policies = list_policies()
    if policies:
        print(f"  {BOLD}User Policies{RESET}")
        for cmd_name, pol in sorted(policies.items()):
            pol_color = GREEN if pol == "allow" else RED
            print(f"    {CYAN}{cmd_name:<20}{RESET} {pol_color}{BOLD}{pol}{RESET}")
    else:
        print(f"  {DIM}No user-configured policies.{RESET}")

    print(f"\n  {DIM}Built-in: {len(ALLOWED_COMMANDS)} allowed, {len(BLOCKED_COMMANDS)} blocked.{RESET}")
    print(f"  {DIM}Set: OPENCLAW sandbox <command> allow|deny|remove{RESET}")


def main():
    tool = ToolBase("OPENCLAW")

    parser = argparse.ArgumentParser(
        description="OPENCLAW - Agent autonomy framework with multi-backend LLM",
        add_help=False
    )
    parser.add_argument("--port", type=int, default=9222, help="Chrome CDP port")
    parser.add_argument("--backend", choices=VALID_BACKENDS,
                        default="nvidia-glm-4-7b",
                        help="LLM backend (default: nvidia-glm-4-7b)")

    subparsers = parser.add_subparsers(dest="command")
    p_chat = subparsers.add_parser("chat", help="Launch the chatbot GUI")
    p_chat.add_argument("--gui", choices=["html", "tkinter"], default="html",
                        help="GUI mode: html (default) or tkinter")
    subparsers.add_parser("cli", help="Interactive terminal agent (Claude Code-style)")
    subparsers.add_parser("status", help="Check LLM provider status")
    subparsers.add_parser("sessions", help="List saved sessions")
    subparsers.add_parser("setup-llm", help="Configure NVIDIA GLM-4.7 API key")

    p_cli_status = subparsers.add_parser("cli-status",
                                          help="Query a running CLI by PID")
    p_cli_status.add_argument("pid", type=int, help="PID of the CLI instance")

    p_cli_inject = subparsers.add_parser("cli-inject",
                                          help="Inject a command into a running CLI")
    p_cli_inject.add_argument("pid", type=int, help="PID of the CLI instance")
    p_cli_inject.add_argument("inject_args", nargs="+", help="Command to inject")

    subparsers.add_parser("cli-list", help="List active CLI instances")

    p_config = subparsers.add_parser("config", help="View or set OPENCLAW config")
    p_config.add_argument("key", nargs="?", help="Config key to set")
    p_config.add_argument("value", nargs="?", help="Value to set")

    p_sandbox = subparsers.add_parser("sandbox", help="Manage sandbox command policies")
    p_sandbox.add_argument("sandbox_cmd", nargs="?", help="Command name")
    p_sandbox.add_argument("sandbox_policy", nargs="?",
                           choices=["allow", "deny", "remove"],
                           help="Policy: allow, deny, or remove")

    if tool.handle_command_line(parser): return

    args = parser.parse_args()

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    if args.command == "chat":
        cmd_chat(args)
    elif args.command == "cli":
        cmd_cli(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "sessions":
        cmd_sessions(args)
    elif args.command == "setup-llm":
        cmd_setup_llm(args)
    elif args.command == "cli-status":
        cmd_cli_status(args)
    elif args.command == "cli-inject":
        cmd_cli_inject(args)
    elif args.command == "cli-list":
        cmd_cli_list(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "sandbox":
        cmd_sandbox(args)
    else:
        # Default: launch HTML GUI (or show help if --help)
        if len(sys.argv) == 1:
            cmd_chat(args)
        else:
            print(f"  {BOLD}OPENCLAW{RESET} - Agent autonomy framework.")
            print()
            print(f"  GUI modes (default: launches HTML GUI):")
            print(f"    OPENCLAW             Launch HTML GUI (default)")
            print(f"    OPENCLAW cli         Interactive terminal agent (Claude Code-style)")
            print(f"    OPENCLAW chat        Launch chatbot GUI (browser-based)")
            print()
            print(f"  Management:")
            print(f"    status           Check LLM provider and connection status")
            print(f"    sessions         List saved sessions")
            print(f"    setup-llm        Configure NVIDIA GLM-4.7 API key")
            print()
            print(f"  External control:")
            print(f"    cli-list         List active CLI instances")
            print(f"    cli-status PID   Query a running CLI's state")
            print(f"    cli-inject PID CMD  Inject a command into a running CLI")
            print()
            print(f"  Config & Sandbox:")
            print(f"    config           View all settings")
            print(f"    config KEY VAL   Set a config value")
            print(f"    sandbox          View sandbox policies")
            print(f"    sandbox CMD POL  Set policy (allow/deny/remove)")
            print()
            print(f"  Options:")
            print(f"    --port N       Chrome CDP port (default: 9222)")
            print(f"    --backend B    nvidia_glm47 | zhipu_glm4")


if __name__ == "__main__":
    main()
