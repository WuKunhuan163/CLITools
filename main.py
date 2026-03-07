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
DIM = get_color("DIM", "\033[2m")
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
    from logic.lifecycle import install_tool as _install
    return _install(tool_name, ROOT_PROJECT_ROOT)

def reinstall_tool(tool_name):
    from logic.lifecycle import reinstall_tool as _reinstall
    return _reinstall(tool_name, ROOT_PROJECT_ROOT)

def uninstall_tool(tool_name, force_yes=False):
    from logic.lifecycle import uninstall_tool as _uninstall
    return _uninstall(tool_name, ROOT_PROJECT_ROOT, force_yes=force_yes, translation_func=_)

def _list_tools(force=False):
    from logic.lifecycle import list_tools
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
    is_auto = False
    if key == "terminal_width":
        if isinstance(value, str) and value.lower() == "auto":
            value = 0
            is_auto = True
        elif value == 0:
            is_auto = True
    if set_global_config(key, value):
        if key == "terminal_width":
            _print_width_check(value, is_auto=is_auto)
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
    from logic.dev.commands import dev_sync
    return dev_sync(ROOT_PROJECT_ROOT, quiet=quiet, translation_func=_)

def _dev_reset():
    from logic.dev.commands import dev_reset
    dev_reset(ROOT_PROJECT_ROOT, SHARED_LOGIC_DIR, translation_func=_)

def _dev_enter(branch, force=False):
    from logic.dev.commands import dev_enter
    dev_enter(branch, ROOT_PROJECT_ROOT, force=force, translation_func=_)

def _dev_create(tool_name):
    from logic.dev.commands import dev_create
    dev_create(tool_name, ROOT_PROJECT_ROOT, translation_func=_)

def _dev_sanity_check(tool_name, fix=False):
    from logic.dev.commands import dev_sanity_check
    return dev_sanity_check(tool_name, ROOT_PROJECT_ROOT, fix=fix, translation_func=_)

def _dev_audit_test(tool_name, fix=False):
    from logic.dev.commands import dev_audit_test
    return dev_audit_test(tool_name, ROOT_PROJECT_ROOT, fix=fix)

def _dev_audit_bin(fix=False):
    from logic.dev.commands import dev_audit_bin
    return dev_audit_bin(ROOT_PROJECT_ROOT, fix=fix)

def _dev_migrate_bin():
    from logic.dev.commands import dev_migrate_bin
    return dev_migrate_bin(ROOT_PROJECT_ROOT)

def _dev_audit_archived():
    from logic.dev.commands import dev_audit_archived
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

def _tool_dev_handler(dev_args):
    """Extended --dev handler for the root TOOL (adds sync, reset, create, etc.)."""
    subcmd = dev_args[0] if dev_args else ""
    rest = dev_args[1:] if len(dev_args) > 1 else []

    if subcmd == "sync":
        _dev_sync()
    elif subcmd == "reset":
        _dev_reset()
    elif subcmd == "enter":
        branch = rest[0] if rest else None
        if branch not in ("main", "test"):
            print("Usage: TOOL --dev enter <main|test> [-f]")
            return
        _dev_enter(branch, "-f" in rest or "--force" in rest)
    elif subcmd == "create":
        name = rest[0] if rest else None
        if not name:
            print("Usage: TOOL --dev create <tool_name>")
            return
        _dev_create(name)
    elif subcmd == "sanity-check":
        name = rest[0] if rest else None
        if not name:
            print("Usage: TOOL --dev sanity-check <tool_name> [--fix]")
            return
        _dev_sanity_check(name, "--fix" in rest)
    elif subcmd == "audit-test":
        name = rest[0] if rest else None
        if not name:
            print("Usage: TOOL --dev audit-test <tool_name> [--fix]")
            return
        _dev_audit_test(name, "--fix" in rest)
    elif subcmd == "audit-bin":
        _dev_audit_bin("--fix" in rest)
    elif subcmd == "audit-archived":
        _dev_audit_archived()
    elif subcmd == "migrate-bin":
        _dev_migrate_bin()
    elif subcmd == "install-hooks":
        from logic.git.hooks import install_hooks
        if install_hooks(ROOT_PROJECT_ROOT):
            print(f"  {BOLD}{GREEN}Installed{RESET} post-checkout hook.")
        else:
            print(f"  {BOLD}{YELLOW}Skipped{RESET}: hook already exists or .git not found.")
    elif subcmd == "uninstall-hooks":
        from logic.git.hooks import uninstall_hooks
        if uninstall_hooks(ROOT_PROJECT_ROOT):
            print(f"  {BOLD}{GREEN}Removed{RESET} post-checkout hook.")
        else:
            print(f"  {BOLD}{YELLOW}Skipped{RESET}: no AITerminalTools hook found.")
    elif subcmd == "locker":
        from logic.git.persistence import get_persistence_manager
        pm = get_persistence_manager(ROOT_PROJECT_ROOT)
        lockers = pm.list_lockers()
        if not lockers:
            print(f"  No lockers.")
        else:
            for l in lockers:
                branch = l.get("branch", "?")
                size = l.get("size_mb", 0)
                print(f"  {BOLD}{l['key']}{RESET}: branch={branch}, size={size}MB")
    else:
        print(f"Usage: TOOL --dev <command>")
        print(f"\n{BOLD}Available commands:{RESET}")
        print(f"  sync                              Sync dev -> tool -> main -> test")
        print(f"  reset                             Reset main/test branches")
        print(f"  enter <main|test> [-f]            Switch to branch")
        print(f"  create <name>                     Create a new tool template")
        print(f"  sanity-check <name> [--fix]       Check tool structure")
        print(f"  audit-test <name> [--fix]         Audit unit test naming")
        print(f"  audit-bin [--fix]                 Audit bin/ shortcuts")
        print(f"  audit-archived                    Check for duplicate tools")
        print(f"  migrate-bin                       Migrate flat bin/ shortcuts")
        print(f"  install-hooks                     Install git post-checkout hook")
        print(f"  uninstall-hooks                   Remove git post-checkout hook")
        print(f"  locker                            List persistence lockers")


def _tool_test_handler(test_args):
    """Extended --test handler for the root TOOL."""
    import argparse as _ap
    tp = _ap.ArgumentParser(add_help=False)
    tp.add_argument("tool_name", nargs="?", default="root", help="Tool name or 'root'")
    tp.add_argument("--range", nargs=2, type=int, help="Test range (start end)")
    tp.add_argument("--max", type=int, default=3, help="Max concurrent tests")
    tp.add_argument("--timeout", type=int, default=60, help="Test timeout")
    tp.add_argument("--list", action="store_true", help="List tests only")
    tp.add_argument("--no-warning", action="store_true")
    parsed = tp.parse_args(test_args)
    _test_tool_with_args(parsed)


def _tool_config_handler(config_args):
    """Handle ``TOOL --config`` (global configuration management)."""
    import argparse as _ap
    cp = _ap.ArgumentParser(
        prog="TOOL --config",
        description="Manage global AITerminalTools configuration",
    )
    config_sub = cp.add_subparsers(dest="config_command")
    cs = config_sub.add_parser("set", help="Set a configuration value")
    cs.add_argument("key", help="Configuration key")
    cs.add_argument("value", help="Configuration value")
    config_sub.add_parser("show-lang", help="Show current language")
    config_sub.add_parser("show", help="Show all tool configurations")

    parsed = cp.parse_args(config_args)

    current_lang = get_global_config("language", "en")
    set_rtl_mode(current_lang in ["ar"])

    if parsed.config_command == "set":
        val = parsed.value
        if val.isdigit():
            val = int(val)
        update_config(parsed.key, val)
    elif parsed.config_command == "show-lang":
        print(f"Current language: {current_lang}")
    elif parsed.config_command == "show":
        _show_config()
    else:
        cp.print_help()


def _tool_install_handler(install_args):
    """Handle ``TOOL --install <name>``."""
    if not install_args:
        print("Usage: TOOL --install <TOOL_NAME>")
        return
    install_tool(install_args[0])


def _tool_reinstall_handler(reinstall_args):
    """Handle ``TOOL --reinstall <name>``."""
    if not reinstall_args:
        print("Usage: TOOL --reinstall <TOOL_NAME>")
        return
    reinstall_tool(reinstall_args[0])


def _tool_uninstall_handler(uninstall_args):
    """Handle ``TOOL --uninstall <name> [-y]``."""
    if not uninstall_args:
        print("Usage: TOOL --uninstall <TOOL_NAME> [-y]")
        return
    force_yes = "-y" in uninstall_args or "--yes" in uninstall_args
    name = [a for a in uninstall_args if not a.startswith("-")][0]
    uninstall_tool(name, force_yes)


def _tool_list_handler(list_args):
    """Handle ``TOOL --list [--force]``."""
    force = "--force" in list_args
    _list_tools(force)


def _tool_audit_handler(audit_args):
    """Handle ``TOOL --audit {imports,quality} [options]``."""
    import argparse as _ap
    ap = _ap.ArgumentParser(prog="TOOL --audit", description="Code quality audits")
    audit_sub = ap.add_subparsers(dest="audit_command")
    ip = audit_sub.add_parser("imports", help="Audit cross-tool import quality")
    ip.add_argument("--tool", help="Audit specific tool only")
    ip.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    ip.add_argument("--exclude", help="Comma-separated tool names to skip")
    qp = audit_sub.add_parser("quality", help="Audit hooks, interfaces, and skills")
    qp.add_argument("--tool", help="Audit specific tool only")
    qp.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    qp.add_argument("--exclude", help="Comma-separated tool names to skip")
    qp.add_argument("--no-skills", action="store_true", help="Skip skills audit")

    parsed = ap.parse_args(audit_args)
    root = Path(__file__).resolve().parent

    if parsed.audit_command == "imports":
        from logic.lang.audit_imports import audit_all_tools, audit_tool, format_report, to_json
        exclude = [x.strip() for x in (parsed.exclude or "").split(",") if x.strip()]
        if parsed.tool:
            tool_dir = root / "tool" / parsed.tool
            if not tool_dir.exists():
                print(f"Tool not found: {parsed.tool}")
            else:
                issues = audit_tool(tool_dir, root)
                results = {parsed.tool: issues} if issues else {}
                print(to_json(results) if parsed.as_json else format_report(results))
        else:
            results = audit_all_tools(root, exclude=exclude or ["GOOGLE.CDMCP"])
            print(to_json(results) if parsed.as_json else format_report(results))
    elif parsed.audit_command == "quality":
        from logic.audit.hooks import (
            audit_all_quality, audit_tool_quality, audit_skills,
            format_quality_report, quality_to_json,
        )
        exclude = [x.strip() for x in (parsed.exclude or "").split(",") if x.strip()]
        skills_issues = None if parsed.no_skills else audit_skills(root)
        if parsed.tool:
            tool_dir = root / "tool" / parsed.tool
            if not tool_dir.exists():
                print(f"Tool not found: {parsed.tool}")
            else:
                tool_res = audit_tool_quality(tool_dir, root)
                results = {parsed.tool: tool_res} if tool_res else {}
                print(quality_to_json(results, skills_issues) if parsed.as_json
                      else format_quality_report(results, skills_issues))
        else:
            results = audit_all_quality(root, exclude=exclude)
            print(quality_to_json(results, skills_issues) if parsed.as_json
                  else format_quality_report(results, skills_issues))
    else:
        ap.print_help()


def _tool_lang_handler(lang_args):
    """Handle ``TOOL --lang {audit,list}``."""
    import argparse as _ap
    lp = _ap.ArgumentParser(prog="TOOL --lang", description="Language management")
    lang_sub = lp.add_subparsers(dest="lang_command")
    la = lang_sub.add_parser("audit", help="Audit translation coverage")
    la.add_argument("code", help="Language code")
    la.add_argument("--force", action="store_true", help="Clear audit cache")
    la.add_argument("--turing", action="store_true", help="Scan Turing states")
    lang_sub.add_parser("list", help="List supported languages")

    parsed = lp.parse_args(lang_args)
    if parsed.lang_command == "audit":
        _audit_lang(parsed.code, parsed.force, parsed.turing)
    elif parsed.lang_command == "list":
        _list_languages()
    else:
        lp.print_help()


def _tool_rule_handler(rule_args):
    """Handle ``TOOL --rule {create,inject}``."""
    import argparse as _ap
    rp = _ap.ArgumentParser(prog="TOOL --rule", description="AI rule management")
    rule_sub = rp.add_subparsers(dest="rule_command")
    rc = rule_sub.add_parser("create", help="Create a Cursor rule (.mdc)")
    rc.add_argument("name", help="Rule name")
    rc.add_argument("--description", required=True, help="Rule description")
    rc.add_argument("--globs", help="File patterns (comma separated)")
    rc.add_argument("--always-apply", action="store_true", help="Always apply this rule")
    rule_sub.add_parser("inject", help="Inject TOOL rule into .cursor/rules/ (auto-apply)")

    parsed = rp.parse_args(rule_args)
    if parsed.rule_command == "create":
        _generate_ai_rule(parsed.name, parsed.description, parsed.globs, parsed.always_apply)
    elif parsed.rule_command == "inject":
        _inject_rule()
    elif not parsed.rule_command:
        _show_rule()
    else:
        rp.print_help()


def _tool_search_handler(search_args):
    """Handle ``TOOL --search {tools,interfaces,skills} <query>``."""
    import argparse as _ap
    sp = _ap.ArgumentParser(prog="TOOL --search", description="Semantic search across project")
    sub = sp.add_subparsers(dest="search_target")

    tp = sub.add_parser("tools", help="Search tools by natural language")
    tp.add_argument("query", nargs="+", help="Search query")
    tp.add_argument("-n", "--top", type=int, default=5, help="Max results")

    ip = sub.add_parser("interfaces", help="Search tool interfaces")
    ip.add_argument("query", nargs="+", help="Search query")
    ip.add_argument("-n", "--top", type=int, default=5, help="Max results")

    skp = sub.add_parser("skills", help="Search skills")
    skp.add_argument("query", nargs="+", help="Search query")
    skp.add_argument("-n", "--top", type=int, default=5, help="Max results")
    skp.add_argument("--tool", dest="skill_tool", default=None, help="Scope to a specific tool")

    parsed = sp.parse_args(search_args)
    if not parsed.search_target:
        sp.print_help()
        return

    from logic.search.tools import search_tools, search_interfaces, search_skills

    query = " ".join(parsed.query)
    top_k = parsed.top

    if parsed.search_target == "tools":
        results = search_tools(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "interfaces":
        results = search_interfaces(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "skills":
        tool_name = getattr(parsed, "skill_tool", None)
        results = search_skills(ROOT_PROJECT_ROOT, query, top_k=top_k, tool_name=tool_name)
    else:
        sp.print_help()
        return

    if not results:
        print(f"  No results for: {query}")
        return

    for i, r in enumerate(results, 1):
        meta = r.get("meta", {})
        score_pct = int(r["score"] * 100)
        rtype = meta.get("type", "unknown")

        if rtype == "tool":
            desc = meta.get("description") or meta.get("purpose") or ""
            flags = []
            if meta.get("has_readme"):
                flags.append("README")
            if meta.get("has_for_agent"):
                flags.append("for_agent")
            tag = f" [{', '.join(flags)}]" if flags else ""
            print(f"  {BOLD}{i}. {r['id']}{RESET} ({score_pct}%){tag}")
            if desc:
                print(f"     {desc}")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype == "interface":
            print(f"  {BOLD}{i}. {r['id']}{RESET} interface ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype == "skill":
            tool_tag = f" (tool: {meta['tool']})" if meta.get("tool") else ""
            print(f"  {BOLD}{i}. {r['id']}{RESET}{tool_tag} ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")


# Maps --flag to handler function
_TOOL_FLAG_HANDLERS = {
    "--dev": lambda args: _tool_dev_handler(args),
    "--test": lambda args: _tool_test_handler(args),
    "--config": lambda args: _tool_config_handler(args),
    "--install": lambda args: _tool_install_handler(args),
    "--reinstall": lambda args: _tool_reinstall_handler(args),
    "--uninstall": lambda args: _tool_uninstall_handler(args),
    "--list": lambda args: _tool_list_handler(args),
    "--status": lambda args: _show_status(),
    "--audit": lambda args: _tool_audit_handler(args),
    "--lang": lambda args: _tool_lang_handler(args),
    "--rule": lambda args: _tool_rule_handler(args),
    "--search": lambda args: _tool_search_handler(args),
}


def _print_tool_help():
    """Print unified help for all TOOL commands."""
    print(f"{BOLD}AITerminalTools Manager{RESET}")
    print(f"\nUsage: TOOL --<command> [options]\n")
    print(f"Commands:")
    print(f"  --install <name>         Install a tool")
    print(f"  --reinstall <name>       Reinstall a tool")
    print(f"  --uninstall <name> [-y]  Uninstall a tool")
    print(f"  --list [--force]         List all available tools")
    print(f"  --status                 Show installed tools and their status")
    print(f"  --config <sub>           Manage global configuration (set, show, show-lang)")
    print(f"  --lang <sub>             Language management (audit, list)")
    print(f"  --audit <sub>            Code quality audits (imports, quality)")
    print(f"  --rule <sub>             AI rule management (create, inject)")
    print(f"  --search <sub> <query>  Semantic search (tools, interfaces, skills)")
    print(f"  --dev <sub>              Developer commands")
    print(f"  --test <sub>             Run tests")
    print(f"\nUse TOOL --<command> --help for details on each command.")


def main():
    stripped_argv = [a for a in sys.argv[1:] if a not in ["--no-warning", "--tool-quiet"]]

    current_lang = get_global_config("language", "en")
    set_rtl_mode(current_lang in ["ar"])

    if not stripped_argv or stripped_argv[0] in ["-h", "--help", "help"]:
        _print_tool_help()
        return

    for flag, handler in _TOOL_FLAG_HANDLERS.items():
        if flag in stripped_argv:
            idx = stripped_argv.index(flag)
            handler(stripped_argv[idx + 1:])
            return

    print(f"Unknown command: {stripped_argv[0]}")
    print(f"Use TOOL --help for available commands.")

if __name__ == "__main__":
    main()
