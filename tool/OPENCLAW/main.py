#!/usr/bin/env python3
"""OPENCLAW — Agent autonomy framework with multi-backend LLM integration.

Supports two LLM backends:
  - nvidia_glm47: GLM-4.7 via NVIDIA Build API (free tier, compliant)
  - yuanbao_web:  Tencent Yuanbao via CDMCP browser automation (legacy)

Usage:
    OPENCLAW              Show help
    OPENCLAW chat         Launch the chatbot GUI (default: GLM-4.7 API)
    OPENCLAW status       Check LLM provider and connection status
    OPENCLAW sessions     List saved sessions
    OPENCLAW setup-llm    Configure the NVIDIA GLM-4.7 API key
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
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.config import get_color

VALID_BACKENDS = ("nvidia_glm47", "yuanbao_web")


def cmd_setup_llm(args):
    """Configure the NVIDIA GLM-4.7 API key (one-time setup)."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    print(f"  {BOLD}OPENCLAW LLM Setup{RESET}")
    print()
    print(f"  This configures GLM-4.7 via NVIDIA Build (free tier).")
    print(f"  Get your API key from: https://build.nvidia.com/z-ai/glm4_7")
    print()

    from logic.llm.nvidia_glm47 import (
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


def cmd_chat(args):
    """Launch the OPENCLAW chatbot GUI."""
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    backend = getattr(args, "backend", "nvidia_glm47")
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
from logic.resolve import setup_paths
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
        label = "GLM-4.7 API" if backend == "nvidia_glm47" else "Yuanbao Web"
        print(f"  {BOLD}{BLUE}Launching{RESET} OPENCLAW chatbot ({label})...", flush=True)
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
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    print(f"  {BOLD}LLM Providers{RESET}:")

    # GLM-4.7 API status
    from logic.llm.nvidia_glm47 import NvidiaGLM47Provider
    provider = NvidiaGLM47Provider()
    info = provider.get_info()
    avail = f"{GREEN}available{RESET}" if info["available"] else f"{RED}not configured{RESET}"
    print(f"    {BOLD}nvidia_glm47{RESET}: {avail} ({info['model']}, {info['rpm_limit']} RPM)")

    # Yuanbao web status
    try:
        from logic.chrome.session import is_chrome_cdp_available
        cdp_ok = is_chrome_cdp_available(args.port)
    except Exception:
        cdp_ok = False

    if cdp_ok:
        try:
            from tool.OPENCLAW.logic.chrome.api import get_auth_state, find_yuanbao_tab
            tab = find_yuanbao_tab(args.port)
            if tab:
                auth = get_auth_state(args.port)
                authed = auth.get("authenticated", False)
                if authed:
                    status = f"{GREEN}available{RESET}"
                else:
                    status = f"{YELLOW}tab found, not logged in{RESET}"
            else:
                status = f"{YELLOW}CDP available, no Yuanbao tab{RESET}"
        except Exception:
            status = f"{YELLOW}CDP available, Yuanbao check failed{RESET}"
    else:
        status = f"{RED}CDP unavailable{RESET}"
    print(f"    {BOLD}yuanbao_web{RESET}:  {status} (port {args.port})")

    print()
    print(f"  {BOLD}Default backend{RESET}: nvidia_glm47")
    print(f"  Use --backend yuanbao_web for browser-based mode.")


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


def main():
    tool = ToolBase("OPENCLAW")

    parser = argparse.ArgumentParser(
        description="OPENCLAW - Agent autonomy framework with multi-backend LLM",
        add_help=False
    )
    parser.add_argument("--port", type=int, default=9222, help="Chrome CDP port")
    parser.add_argument("--backend", choices=VALID_BACKENDS,
                        default="nvidia_glm47",
                        help="LLM backend (default: nvidia_glm47)")

    subparsers = parser.add_subparsers(dest="command")
    p_chat = subparsers.add_parser("chat", help="Launch the chatbot GUI")
    p_chat.add_argument("--gui", choices=["html", "tkinter"], default="html",
                        help="GUI mode: html (default) or tkinter")
    subparsers.add_parser("status", help="Check LLM provider status")
    subparsers.add_parser("sessions", help="List saved sessions")
    subparsers.add_parser("setup-llm", help="Configure NVIDIA GLM-4.7 API key")

    if tool.handle_command_line(parser): return

    args = parser.parse_args()

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    if args.command == "chat":
        cmd_chat(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "sessions":
        cmd_sessions(args)
    elif args.command == "setup-llm":
        cmd_setup_llm(args)
    else:
        print(f"  {BOLD}OPENCLAW{RESET} - Agent autonomy framework.")
        print()
        print(f"  Commands:")
        print(f"    chat        Launch chatbot GUI (default: GLM-4.7 API)")
        print(f"    status      Check LLM provider and connection status")
        print(f"    sessions    List saved sessions")
        print(f"    setup-llm   Configure NVIDIA GLM-4.7 API key")
        print()
        print(f"  Options:")
        print(f"    --port N       Chrome CDP port (default: 9222)")
        print(f"    --backend B    nvidia_glm47 | yuanbao_web")
        print()
        print(f"  First-time setup:")
        print(f"    1. OPENCLAW setup-llm      (enter NVIDIA API key)")
        print(f"    2. OPENCLAW chat           (start with GLM-4.7)")
        print()
        print(f"  Legacy mode (Yuanbao browser):")
        print(f"    OPENCLAW chat --backend yuanbao_web")


if __name__ == "__main__":
    main()
