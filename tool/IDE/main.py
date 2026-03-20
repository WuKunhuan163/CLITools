#!/usr/bin/env python3
"""IDE Tool - AI IDE detection, configuration, and hook management.

Manages Cursor/VS Code/Windsurf IDE integration including rules, hooks,
and deployment of IDE-specific configuration templates.
"""
import sys
import json
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists():
        break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic._.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
DIM = get_color("DIM")
RESET = get_color("RESET")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class IDETool(ToolBase):
    def __init__(self):
        super().__init__("IDE")


def main():
    tool = IDETool()

    parser = argparse.ArgumentParser(
        description="AI IDE detection, configuration, and hook management",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs="*", help="Additional arguments")
    parser.add_argument("--force", action="store_true", help="Force overwrite")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    parser.add_argument("--tool", default=None, help="Target tool name for rule command")

    if tool.handle_command_line(parser):
        return

    args, unknown = parser.parse_known_args()
    cmd = args.command

    if cmd == "status" or cmd is None:
        _cmd_status(args)
        return

    if cmd == "detect":
        _cmd_detect(args)
        return

    if cmd == "deploy":
        _cmd_deploy(args)
        return

    if cmd == "rules":
        _cmd_rules(args)
        return

    if cmd == "hooks":
        _cmd_hooks(args)
        return

    if cmd == "rule":
        subcmd = args.args[0] if args.args else None
        if subcmd == "inject":
            _cmd_rule_inject(args)
        elif subcmd == "show":
            _cmd_rule_show(args)
        else:
            _cmd_rule_show(args)
        return

    print(f"  {BOLD}IDE{RESET} - AI IDE integration tool\n")
    print(f"  {BOLD}Commands{RESET}")
    print(f"  {DIM}status    Show detected IDEs and deployment state{RESET}")
    print(f"  {DIM}detect    Detect installed AI IDEs{RESET}")
    print(f"  {DIM}deploy    Deploy IDE config (rules, hooks){RESET}")
    print(f"  {DIM}rules     List deployed rules{RESET}")
    print(f"  {DIM}hooks     List registered hooks{RESET}")
    print(f"  {DIM}rule show [--tool NAME]  Show AI agent rule set{RESET}")
    print(f"  {DIM}rule inject              Inject rule into .cursor/rules/{RESET}")
    print()


def _cmd_status(args):
    from tool.IDE.logic.detect import detect_all
    from tool.IDE.logic.setup.deploy import list_rules, list_hooks

    detected = detect_all(PROJECT_ROOT)

    print(f"\n  {BOLD}IDE{RESET} tool status")
    print(f"  {DIM}Manages AI IDE integration (rules, hooks, deployment){RESET}\n")

    if detected:
        for ide in detected:
            print(f"  {GREEN}{BOLD}{ide}{RESET} detected")
    else:
        print(f"  {YELLOW}No AI IDE detected{RESET}")

    rules = list_rules(PROJECT_ROOT)
    hooks = list_hooks(PROJECT_ROOT)

    print(f"\n  {BOLD}Deployed{RESET}")
    print(f"  Rules: {len(rules)}")
    if rules:
        for r in rules:
            print(f"    {DIM}{r}{RESET}")
    print(f"  Hooks: {len(hooks)}")
    if hooks:
        for h in hooks:
            print(f"    {DIM}{h['event']}: {h['command']}{RESET}")
    print()


def _cmd_detect(args):
    from tool.IDE.logic.detect import detect_all
    detected = detect_all(PROJECT_ROOT)
    if args.as_json:
        print(json.dumps({"ides": detected}))
    elif detected:
        for ide in detected:
            print(f"  {GREEN}{BOLD}{ide}{RESET}")
    else:
        print(f"  {YELLOW}No AI IDE detected.{RESET}")


def _cmd_deploy(args):
    from tool.IDE.logic.detect import detect_all
    from tool.IDE.logic.setup.deploy import deploy_cursor

    detected = detect_all(PROJECT_ROOT)
    if not detected:
        print(f"  {YELLOW}No AI IDE detected.{RESET} Nothing to deploy.")
        return

    total = {"deployed": [], "skipped": []}
    if "cursor" in detected:
        result = deploy_cursor(PROJECT_ROOT, force=args.force)
        total["deployed"].extend(result["deployed"])
        total["skipped"].extend(result["skipped"])

    if args.as_json:
        print(json.dumps(total))
    elif total["deployed"]:
        print(f"  {BOLD}{GREEN}Deployed.{RESET} {DIM}{len(total['deployed'])} files for {', '.join(detected)}{RESET}")
        for f in total["deployed"]:
            print(f"    {DIM}{f}{RESET}")
    else:
        print(f"  {BOLD}Up to date.{RESET} {DIM}All files current for {', '.join(detected)}{RESET}")


def _cmd_rules(args):
    from tool.IDE.logic.setup.deploy import list_rules
    rules = list_rules(PROJECT_ROOT)
    if args.as_json:
        print(json.dumps({"rules": rules}))
    elif rules:
        print(f"  {BOLD}Deployed rules{RESET} ({len(rules)}):")
        for r in rules:
            print(f"    {DIM}{r}{RESET}")
    else:
        print(f"  {DIM}No rules deployed.{RESET}")


def _cmd_hooks(args):
    from tool.IDE.logic.setup.deploy import list_hooks
    hooks = list_hooks(PROJECT_ROOT)
    if args.as_json:
        print(json.dumps({"hooks": hooks}))
    elif hooks:
        print(f"  {BOLD}Registered hooks{RESET} ({len(hooks)}):")
        for h in hooks:
            print(f"    {DIM}{h['event']}: {h['command']}{RESET}")
    else:
        print(f"  {DIM}No hooks registered.{RESET}")


def _cmd_rule_show(args):
    from tool.IDE.logic.rule import generate_ai_rule
    generate_ai_rule(PROJECT_ROOT, target_tool=args.tool)


def _cmd_rule_inject(args):
    from tool.IDE.logic.rule import inject_rule
    inject_rule(PROJECT_ROOT)


if __name__ == "__main__":
    main()
