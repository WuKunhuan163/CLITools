#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import argparse
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

# Add project root to sys.path
_script_path = Path(__file__).resolve()
if _script_path.parent.name == "bin":
    ROOT_PROJECT_ROOT = _script_path.parent.parent
else:
    ROOT_PROJECT_ROOT = _script_path.parent

if str(ROOT_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT_PROJECT_ROOT))

# Import colors and shared utils from logic
from logic.config import get_color, get_setting, get_global_config
from logic.lang.utils import get_translation
from logic.utils import get_logic_dir, set_rtl_mode

RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", "\033[32m")
BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
YELLOW = get_color("YELLOW", "\033[33m")
RED = get_color("RED", "\033[31m")
WHITE = get_color("WHITE", "\033[37m")

SHARED_LOGIC_DIR = get_logic_dir(ROOT_PROJECT_ROOT)

def _(translation_key, default, **kwargs):
    text = get_translation(str(SHARED_LOGIC_DIR), translation_key, default)
    return text.format(**kwargs)

# --- Lifecycle Commands ---
def install_tool(tool_name):
    from logic.tool.lifecycle import install_tool as _install
    return _install(tool_name, ROOT_PROJECT_ROOT)

def reinstall_tool(tool_name):
    from logic.tool.lifecycle import reinstall_tool as _reinstall
    return _reinstall(tool_name, ROOT_PROJECT_ROOT)

def uninstall_tool(tool_name, force_yes=False):
    from logic.tool.lifecycle import uninstall_tool as _uninstall
    return _uninstall(tool_name, ROOT_PROJECT_ROOT, force_yes=force_yes, translation_func=_)

def _list_tools(force=False):
    from logic.tool.lifecycle import list_tools
    list_tools(ROOT_PROJECT_ROOT, force=force, translation_func=_)

# --- Config Commands ---
def _print_width_check(width, is_auto=False, actual_detected=True):
    from logic.config.manager import print_width_check
    print_width_check(width, is_auto=is_auto, actual_detected=actual_detected, project_root=ROOT_PROJECT_ROOT, translation_func=_)

def update_config(key, value):
    from logic.config.main import set_global_config
    if key == "language":
        lang = value.lower()
        if lang != "en":
            trans_path = ROOT_PROJECT_ROOT / "logic" / "translation" / f"{lang}.json"
            if not trans_path.exists():
                print(f"{BOLD}{RED}" + _("label_error", "Error") + f"{RESET}: " + _("lang_error_not_found_simple", "Language '{lang}' not found.", lang=lang))
                return False
    if set_global_config(key, value):
        if key == "terminal_width":
            val = get_global_config("terminal_width")
            _print_width_check(val, is_auto=(value in [0, "auto"]))
        else:
            print(_("config_updated", "Global configuration updated: {key} = {value}", key=key, value=value))
        return True
    return False

# --- Config Show Command ---
def _show_config():
    """Display global and per-tool configurations."""
    global_config_path = ROOT_PROJECT_ROOT / "data" / "config.json"

    print(f"\n{BOLD}Global Configuration{RESET}")
    if global_config_path.exists():
        try:
            with open(global_config_path) as f:
                global_config = json.load(f)
            for k, v in sorted(global_config.items()):
                print(f"  {k}: {v}")
        except Exception:
            print(f"  {RED}Error reading config{RESET}")
    else:
        print("  (no global config)")

    tool_dir = ROOT_PROJECT_ROOT / "tool"
    tool_configs = []
    if tool_dir.exists():
        for td in sorted(tool_dir.iterdir()):
            config_path = td / "data" / "config.json"
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        cfg = json.load(f)
                    tool_configs.append((td.name, cfg))
                except Exception:
                    tool_configs.append((td.name, {"_error": "unreadable"}))

    if tool_configs:
        print(f"\n{BOLD}Tool Configurations{RESET}")
        for name, cfg in tool_configs:
            items = ", ".join(f"{k}={v}" for k, v in cfg.items() if not k.startswith("_"))
            if items:
                print(f"  {name}: {items}")
            elif "_error" in cfg:
                print(f"  {name}: {RED}error{RESET}")
    print()


# --- Status Command ---
def _show_status():
    """Display installed tools, configuration completeness, and health."""
    registry_path = ROOT_PROJECT_ROOT / "tool.json"
    if not registry_path.exists():
        print(f"{BOLD}{RED}Registry not found{RESET}.")
        return

    with open(registry_path) as f:
        registry = json.load(f)

    all_tools = registry.get("tools", [])
    bin_dir = ROOT_PROJECT_ROOT / "bin"
    tool_dir = ROOT_PROJECT_ROOT / "tool"

    print(f"\n{BOLD}AITerminalTools Status{RESET}")
    print(f"{'Tool':<20} {'Installed':<12} {'Config':<12} {'Tests':<10}")
    print("-" * 54)

    def _is_tool_installed(n):
        sn = n.split(".")[-1] if "." in n else n
        return (bin_dir / sn / sn).exists() or (bin_dir / sn).is_file()

    for name in sorted(all_tools):
        installed = _is_tool_installed(name)
        has_main = (tool_dir / name / "main.py").exists()

        installed_str = f"{GREEN}yes{RESET}" if (installed and has_main) else f"{RED}no{RESET}"

        config_status = "-"
        config_path = tool_dir / name / "data" / "config.json"
        if config_path.exists():
            config_status = f"{GREEN}ok{RESET}"
        elif has_main:
            config_status = f"{YELLOW}none{RESET}"

        test_dir = tool_dir / name / "test"
        if test_dir.exists() and any(test_dir.glob("test_*.py")):
            test_count = len(list(test_dir.glob("test_*.py")))
            test_status = f"{test_count} test(s)"
        else:
            test_status = "-"

        # Pad ANSI-colored strings properly
        print(f"  {name:<18} {installed_str:<21} {config_status:<21} {test_status}")

    installed_count = sum(1 for n in all_tools
                         if _is_tool_installed(n) and (tool_dir / n / "main.py").exists())
    print(f"\n{BOLD}{installed_count}/{len(all_tools)}{RESET} tools installed.\n")


# --- Dev Commands ---
def _dev_sync(quiet=False):
    from logic.tool.dev.commands import dev_sync
    return dev_sync(ROOT_PROJECT_ROOT, quiet=quiet, translation_func=_)

def _dev_reset():
    from logic.tool.dev.commands import dev_reset
    dev_reset(ROOT_PROJECT_ROOT, SHARED_LOGIC_DIR, translation_func=_)

def _dev_enter(branch, force=False):
    from logic.tool.dev.commands import dev_enter
    dev_enter(branch, ROOT_PROJECT_ROOT, force=force, translation_func=_)

def _dev_create(tool_name):
    from logic.tool.dev.commands import dev_create
    dev_create(tool_name, ROOT_PROJECT_ROOT, translation_func=_)

def _dev_sanity_check(tool_name, fix=False):
    from logic.tool.dev.commands import dev_sanity_check
    return dev_sanity_check(tool_name, ROOT_PROJECT_ROOT, fix=fix, translation_func=_)

def _dev_audit_test(tool_name, fix=False):
    from logic.tool.dev.commands import dev_audit_test
    return dev_audit_test(tool_name, ROOT_PROJECT_ROOT, fix=fix)

def _dev_audit_bin(fix=False):
    from logic.tool.dev.commands import dev_audit_bin
    return dev_audit_bin(ROOT_PROJECT_ROOT, fix=fix)

def _dev_migrate_bin():
    from logic.tool.dev.commands import dev_migrate_bin
    return dev_migrate_bin(ROOT_PROJECT_ROOT)

def _dev_audit_archived():
    from logic.tool.dev.commands import dev_audit_archived
    return dev_audit_archived(ROOT_PROJECT_ROOT)

# --- Test Commands ---
def _test_tool_with_args(args):
    from logic.test.manager import test_tool_with_args
    test_tool_with_args(args, ROOT_PROJECT_ROOT, translation_func=_)

# --- Lang Commands ---
def _audit_lang(lang_code, force=False, turing=False):
    from logic.lang.commands import audit_lang
    audit_lang(lang_code, ROOT_PROJECT_ROOT, force=force, turing=turing, translation_func=_)

def _list_languages():
    from logic.lang.commands import list_languages
    list_languages(ROOT_PROJECT_ROOT, translation_func=_)

# --- Rule Commands ---
def _show_rule():
    from logic.config.rule.manager import generate_ai_rule
    generate_ai_rule(ROOT_PROJECT_ROOT)

def _inject_rule():
    from logic.config.rule.manager import inject_rule
    inject_rule(ROOT_PROJECT_ROOT)

def _generate_ai_rule(name, description, globs, always_apply):
    from logic.config.rule.manager import generate_ai_rule
    generate_ai_rule(name, description, globs, always_apply, ROOT_PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description="AITerminalTools Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # TOOL install <name>
    install_p = subparsers.add_parser("install", help="Install a tool")
    install_p.add_argument("name", help="Name of the tool to install")

    # TOOL reinstall <name>
    reinstall_p = subparsers.add_parser("reinstall", help="Reinstall a tool")
    reinstall_p.add_argument("name", help="Name of the tool to reinstall")

    # TOOL uninstall <name>
    uninstall_p = subparsers.add_parser("uninstall", help="Uninstall a tool")
    uninstall_p.add_argument("name", help="Name of the tool to uninstall")
    uninstall_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # TOOL list
    list_p = subparsers.add_parser("list", help="List all available tools")
    list_p.add_argument("--force", action="store_true", help="Force refresh cache")

    # TOOL config
    config_p = subparsers.add_parser("config", help="Manage global configuration")
    config_sub = config_p.add_subparsers(dest="config_command")
    config_set = config_sub.add_parser("set", help="Set a configuration value")
    config_set.add_argument("key", help="Configuration key")
    config_set.add_argument("value", help="Configuration value")
    config_sub.add_parser("show-lang", help="Show current language")
    config_sub.add_parser("show", help="Show all tool configurations")

    # TOOL status
    subparsers.add_parser("status", help="Show installed tools and their status")

    # TOOL dev
    dev_p = subparsers.add_parser("dev", help="Developer commands")
    dev_sub = dev_p.add_subparsers(dest="dev_command")
    dev_sub.add_parser("sync", help="Sync dev -> tool -> main -> test")
    dev_sub.add_parser("reset", help="Reset main/test branches")
    dev_enter_p = dev_sub.add_parser("enter", help="Enter main or test branch")
    dev_enter_p.add_argument("branch", choices=["main", "test"], help="Branch to enter")
    dev_enter_p.add_argument("-f", "--force", action="store_true", help="Force switch")
    dev_create_p = dev_sub.add_parser("create", help="Create a new tool template")
    dev_create_p.add_argument("name", help="Name of the new tool")
    dev_sanity = dev_sub.add_parser("sanity-check", help="Check tool structure")
    dev_sanity.add_argument("name", help="Tool name")
    dev_sanity.add_argument("--fix", action="store_true", help="Try to fix issues")
    dev_audit_t = dev_sub.add_parser("audit-test", help="Audit unit tests")
    dev_audit_t.add_argument("name", help="Tool name")
    dev_audit_t.add_argument("--fix", action="store_true", help="Fix naming")
    dev_audit_b = dev_sub.add_parser("audit-bin", help="Audit bin directory")
    dev_audit_b.add_argument("--fix", action="store_true", help="Fix shortcuts")
    dev_sub.add_parser("audit-archived", help="Check for duplicate tools in tool/ and resource/archived/")
    dev_sub.add_parser("migrate-bin", help="Migrate flat bin/ shortcuts to bin/<tool>/ structure")

    # TOOL test <name>
    test_p = subparsers.add_parser("test", help="Run unit tests")
    test_p.add_argument("tool_name", help="Tool name or 'root'")
    test_p.add_argument("--range", nargs=2, type=int, help="Test range (start end)")
    test_p.add_argument("--max", type=int, default=3, help="Max concurrent tests")
    test_p.add_argument("--timeout", type=int, default=60, help="Test timeout in seconds")
    test_p.add_argument("--list", action="store_true", help="List tests only")
    test_p.add_argument("--no-warning", action="store_true", help="Suppress non-critical warnings")

    # TOOL lang
    lang_p = subparsers.add_parser("lang", help="Language management")
    lang_sub = lang_p.add_subparsers(dest="lang_command")
    lang_audit_p = lang_sub.add_parser("audit", help="Audit translation coverage")
    lang_audit_p.add_argument("code", help="Language code")
    lang_audit_p.add_argument("--force", action="store_true", help="Clear audit cache")
    lang_audit_p.add_argument("--turing", action="store_true", help="Scan Turing states")
    lang_sub.add_parser("list", help="List supported languages")

    # TOOL rule
    rule_p = subparsers.add_parser("rule", help="AI rule management")
    rule_sub = rule_p.add_subparsers(dest="rule_command")
    rule_create_p = rule_sub.add_parser("create", help="Create a Cursor rule (.mdc)")
    rule_create_p.add_argument("name", help="Rule name")
    rule_create_p.add_argument("--description", required=True, help="Rule description")
    rule_create_p.add_argument("--globs", help="File patterns (comma separated)")
    rule_create_p.add_argument("--always-apply", action="store_true", help="Always apply this rule")
    rule_sub.add_parser("inject", help="Inject TOOL rule into .cursor/rules/ (auto-apply)")

    args = parser.parse_args()

    # Apply global settings
    current_lang = get_global_config("language", "en")
    set_rtl_mode(current_lang in ["ar"])

    if args.command == "install": install_tool(args.name)
    elif args.command == "reinstall": reinstall_tool(args.name)
    elif args.command == "uninstall": uninstall_tool(args.name, args.yes)
    elif args.command == "list": _list_tools(args.force)
    elif args.command == "status": _show_status()
    elif args.command == "config":
        if args.config_command == "set":
            val = args.value
            if val.isdigit(): val = int(val)
            update_config(args.key, val)
        elif args.config_command == "show-lang":
            print(f"Current language: {current_lang}")
        elif args.config_command == "show":
            _show_config()
    elif args.command == "dev":
        if args.dev_command == "sync": _dev_sync()
        elif args.dev_command == "reset": _dev_reset()
        elif args.dev_command == "enter": _dev_enter(args.branch, args.force)
        elif args.dev_command == "create": _dev_create(args.name)
        elif args.dev_command == "sanity-check": _dev_sanity_check(args.name, args.fix)
        elif args.dev_command == "audit-test": _dev_audit_test(args.name, args.fix)
        elif args.dev_command == "audit-bin": _dev_audit_bin(args.fix)
        elif args.dev_command == "migrate-bin": _dev_migrate_bin()
        elif args.dev_command == "audit-archived": _dev_audit_archived()
    elif args.command == "test": _test_tool_with_args(args)
    elif args.command == "lang":
        if args.lang_command == "audit": _audit_lang(args.code, args.force, args.turing)
        elif args.lang_command == "list": _list_languages()
    elif args.command == "rule":
        if args.rule_command == "create": _generate_ai_rule(args.name, args.description, args.globs, args.always_apply)
        elif args.rule_command == "inject": _inject_rule()
        elif not args.rule_command: _show_rule()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
