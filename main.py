#!/usr/bin/env python3
"""TOOL — AITerminalTools root CLI manager.

Three-tier command structure:
  ---<eco>   Shared eco commands (directory-discovered from logic/_/)
  --<tool>   Hierarchical tool-specific commands
  -<mod>     Decorator flags (-no-warning, -tool-quiet)
"""
import sys
from pathlib import Path

_script_path = Path(__file__).resolve()
if _script_path.parent.name == "bin":
    ROOT_PROJECT_ROOT = _script_path.parent.parent
else:
    ROOT_PROJECT_ROOT = _script_path.parent

if str(ROOT_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT_PROJECT_ROOT))

from interface.config import get_color, get_global_config
from interface.lang import get_translation
from interface.utils import get_logic_dir, set_rtl_mode
from interface.tool import ToolBase

BOLD = get_color("BOLD", "\033[1m")
DIM = get_color("DIM", "\033[2m")
RESET = get_color("RESET", "\033[0m")

SHARED_LOGIC_DIR = get_logic_dir(ROOT_PROJECT_ROOT)

def _(translation_key, default, **kwargs):
    text = get_translation(str(SHARED_LOGIC_DIR), translation_key, default)
    return text.format(**kwargs)

_root_tool = ToolBase("TOOL", is_root=True)


def _print_tool_help():
    """Print help listing discovered eco commands from logic/_/."""
    print(f"{BOLD}AITerminalTools Manager{RESET}")
    print(f"\nUsage: TOOL ---<command> [options]")
    print(f"\n  Prefix convention: ---<eco>  --<tool>  -<modifier>\n")

    shared_dir = ROOT_PROJECT_ROOT / "logic" / "_"
    eco_cmds = []
    if shared_dir.exists():
        for d in sorted(shared_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_"):
                cli_path = d / "cli.py"
                if cli_path.exists():
                    eco_cmds.append(d.name)

    print(f"  {BOLD}Discovered Eco Commands{RESET}")
    for name in eco_cmds:
        print(f"    ---{name:<20s}")

    print(f"\n  {BOLD}Base Commands{RESET}")
    for name in ["setup", "rule", "install", "uninstall",
                  "agent", "ask", "plan", "endpoint", "call-register"]:
        print(f"    ---{name:<20s}")

    print(f"\nUse TOOL ---<command> --help for details.")


def main():
    stripped_argv = [a for a in sys.argv[1:]
                     if a not in ["-no-warning", "-tool-quiet"]]

    current_lang = get_global_config("language", "en")
    set_rtl_mode(current_lang in ["ar"])

    if not stripped_argv or stripped_argv[0] in ["-h", "--help", "help"]:
        _print_tool_help()
        return

    # Collect --- eco tokens and positional args
    eco_tokens = []
    positional_args = []
    for arg in stripped_argv:
        if arg.startswith("---") and len(arg) > 3:
            eco_tokens.append(arg[3:])
        else:
            positional_args.append(arg)

    if eco_tokens:
        from logic._.agent.cli import ALLOW_ASSISTANT_SHORTHAND
        base_handlers = {
            "setup": lambda args: _root_tool.run_setup(),
            "rule": lambda args: _root_tool.print_rule(),
            "install": _root_tool._handle_install_dispatch,
            "uninstall": _root_tool._handle_uninstall_dispatch,
            "call-register": _root_tool._handle_call_register,
            "endpoint": _root_tool._handle_endpoint,
        }
        if ALLOW_ASSISTANT_SHORTHAND:
            base_handlers["agent"] = lambda args: _root_tool._handle_agent(args)
            base_handlers["ask"] = lambda args: _root_tool._handle_agent(args, mode="ask")
            base_handlers["plan"] = lambda args: _root_tool._handle_agent(args, mode="plan")

        resolved = _root_tool._resolve_eco_command(
            eco_tokens, positional_args, parser=None,
            base_handlers=base_handlers,
        )
        if resolved:
            return

        user_cmd = f"---{eco_tokens[0]}"
    else:
        user_cmd = stripped_argv[0]

    from interface.utils import suggest_commands
    shared_dir = ROOT_PROJECT_ROOT / "logic" / "_"
    discovered = []
    if shared_dir.exists():
        for d in sorted(shared_dir.iterdir()):
            if d.is_dir() and (d / "cli.py").exists():
                discovered.append(f"---{d.name}")

    matches = suggest_commands(user_cmd, discovered, n=3, cutoff=0.4)
    print(f"{BOLD}Unknown command:{RESET} {user_cmd}")
    if matches:
        hint = ", ".join(matches)
        print(f"  {DIM}Did you mean: {hint}?{RESET}")
    print(f"  {DIM}Use TOOL --help for available commands.{RESET}")


if __name__ == "__main__":
    main()
