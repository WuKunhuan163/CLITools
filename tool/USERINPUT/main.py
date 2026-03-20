#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""USERINPUT Tool — thin router.

Dispatches to decomposed sub-modules:
  (no args)          → logic/cli.py      (GUI feedback collection)
  --queue            → logic/queue/cli.py (queue management)
  --system-prompt    → logic/prompt/cli.py (system prompt management)
  --config           → logic/config/cli.py (config management)
  --enquiry-mode     → logic/config/cli.py (enquiry mode toggle)
  ---<eco>           → ToolBase eco commands
"""

import os
import sys
import warnings
import argparse
from pathlib import Path

script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

try:
    from interface.tool import ToolBase
except ImportError:
    import subprocess
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.project_root = Path(__file__).resolve().parent.parent.parent
            self.script_dir = Path(__file__).resolve().parent
            self.tool_dir = self.script_dir
        def check_dependencies(self): return True
        def setup_gui(self): pass
        def handle_command_line(self, parser=None):
            if len(sys.argv) > 1 and sys.argv[1] == "setup":
                setup_script = self.script_dir / "setup.py"
                if setup_script.exists():
                    subprocess.run([sys.executable, str(setup_script)] + sys.argv[2:])
                    sys.exit(0)
            return False


class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

    def get_python_exe(self, version=None):
        if not version:
            from interface.config import get_setting
            version = get_setting("default_python_version", "3.11.14")

        v = version
        if v.startswith("python3"): v = v[7:]
        elif v.startswith("python"): v = v[6:]

        try:
            from interface import get_interface
            python_iface = get_interface("PYTHON")
            install_root = python_iface.get_python_install_dir()
        except (ImportError, AttributeError):
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

        from interface.utils import get_system_tag
        system_tag = get_system_tag()

        possible_dirs = [v, f"{v}-{system_tag}", f"python{v}-{system_tag}", f"python3{v}-{system_tag}"]
        for d in possible_dirs:
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)
        return sys.executable


def _build_parser():
    """Build the argument parser for USERINPUT."""
    parser = argparse.ArgumentParser(description="USERINPUT Tool", add_help=False)
    parser.add_argument('-h', '--help', action='store_true', dest='show_help')

    # Core feedback arguments
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    parser.add_argument('--enquiry', action='store_true',
                        help="Bypass queue, request real-time user feedback")
    parser.add_argument('--auto-commit-message', type=str, default=None,
                        help="Append a progress message to the auto-commit")

    # Subcommand modes
    parser.add_argument('--queue', action='store_true',
                        help="Queue mode: manage queued prompts")
    parser.add_argument('--system-prompt', action='store_true', dest='system_prompt_mode',
                        help="System prompt management mode")
    parser.add_argument('--config', action='store_true', dest='config_mode',
                        help="Configuration management mode")
    parser.add_argument('--enquiry-mode', type=str, nargs='?', const='status', metavar='on|off',
                        help="Toggle persistent enquiry mode (on/off/status)")

    # Shared management flags (used by --queue and --system-prompt)
    parser.add_argument('--list', action='store_true', help="List items")
    parser.add_argument('--gui', action='store_true', help="Open GUI manager")
    parser.add_argument('--add', type=str, metavar='TEXT', help="Add item")
    parser.add_argument('--delete', type=int, metavar='ID', default=None, help="Delete item by index")
    parser.add_argument('--move-up', type=int, metavar='ID', default=None)
    parser.add_argument('--move-down', type=int, metavar='ID', default=None)
    parser.add_argument('--move-to-top', type=int, metavar='ID', default=None)
    parser.add_argument('--move-to-bottom', type=int, metavar='ID', default=None)

    # Config values (used by --config)
    parser.add_argument('--focus-interval', type=int, default=None)
    parser.add_argument('--time-increment', type=int, default=None)
    parser.add_argument('--cpu-limit', type=float, default=None)
    parser.add_argument('--cpu-timeout', type=int, default=None)

    return parser


def main():
    tool = UserInputTool()

    # Register tool instance for shared get_msg() translations
    from tool.USERINPUT.logic import set_tool
    set_tool(tool)

    # ── Remote GUI control (early intercept) ──
    _gui_cmd_map = {
        "--gui-submit": "submit", "--gui-cancel": "cancel",
        "--gui-stop": "stop", "--gui-add-time": "add_time",
    }
    _gui_match = next((f for f in _gui_cmd_map if f in sys.argv), None)
    if _gui_match:
        from interface.gui import handle_gui_remote_command
        remaining = [a for a in sys.argv[1:] if a not in _gui_cmd_map and a != "--no-warning"]
        return handle_gui_remote_command(
            "USERINPUT", tool.project_root, _gui_cmd_map[_gui_match],
            remaining, tool.get_translation,
        )

    # ── Eco commands (---prefix) ──
    has_eco = any(a.startswith("---") for a in sys.argv[1:])
    if has_eco:
        if tool.handle_command_line():
            return 0

    # ── Parse arguments ──
    parser = _build_parser()
    args, unknown = parser.parse_known_args()

    if args.show_help:
        parser.print_help()
        return 0

    # Suggest flags for bare words that look like known options
    _known_flags = {
        'list', 'gui', 'add', 'delete', 'queue', 'enquiry',
        'system-prompt', 'config', 'help', 'setup', 'rule', 'test', 'dev',
    }
    for u in unknown:
        if not u.startswith('-') and u.lower() in _known_flags:
            from interface.config import get_color
            BOLD, YELLOW, RESET = get_color("BOLD"), get_color("YELLOW"), get_color("RESET")
            print(f"{BOLD}{YELLOW}Did you mean{RESET} --{u.lower()} ?")
            return 1

    # ── Route to subcommand modules ──

    if args.queue:
        from tool.USERINPUT.logic.queue.cli import run_queue
        return run_queue(tool, args, unknown)

    if getattr(args, 'system_prompt_mode', False):
        from tool.USERINPUT.logic.prompt.cli import run_prompt
        return run_prompt(tool, args, unknown)

    if getattr(args, 'config_mode', False):
        from tool.USERINPUT.logic.config.cli import run_config
        return run_config(tool, args, unknown)

    if args.enquiry_mode is not None:
        from tool.USERINPUT.logic.config.cli import run_enquiry_mode
        return run_enquiry_mode(tool, args)

    # Reject management flags without a mode context
    mgmt_flags = args.list or args.gui or args.add or args.delete is not None
    mgmt_flags = mgmt_flags or any(
        v is not None for v in [args.move_up, args.move_down, args.move_to_top, args.move_to_bottom]
    )
    if mgmt_flags:
        print("Usage: --list, --gui, --add, --delete, --move-* require --queue, --system-prompt, or --config.",
              file=sys.stderr)
        return 1

    # ── Default: GUI feedback collection ──
    from tool.USERINPUT.logic.cli import run_feedback
    return run_feedback(tool, args)


if __name__ == "__main__":
    sys.exit(main())
