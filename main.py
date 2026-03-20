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

# Import colors and shared utils via interface
from interface.config import get_color, get_setting, get_global_config
from interface.lang import get_translation
from interface.utils import get_logic_dir, set_rtl_mode

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
    from interface.lifecycle import install_tool as _install
    return _install(tool_name, ROOT_PROJECT_ROOT)

def reinstall_tool(tool_name):
    from interface.lifecycle import reinstall_tool as _reinstall
    return _reinstall(tool_name, ROOT_PROJECT_ROOT)

def uninstall_tool(tool_name, force_yes=False):
    from interface.lifecycle import uninstall_tool as _uninstall
    return _uninstall(tool_name, ROOT_PROJECT_ROOT, force_yes=force_yes, translation_func=_)

def _list_tools(force=False):
    from interface.lifecycle import list_tools
    list_tools(ROOT_PROJECT_ROOT, force=force, translation_func=_)

# --- Config Commands ---
def _print_width_check(width, is_auto=False, actual_detected=True):
    from interface.config import print_width_check
    print_width_check(width, is_auto=is_auto, actual_detected=actual_detected, project_root=ROOT_PROJECT_ROOT, translation_func=_)

def update_config(key, value):
    from interface.config import set_global_config
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
    from interface.dev import dev_sync
    return dev_sync(ROOT_PROJECT_ROOT, quiet=quiet, translation_func=_)

def _dev_reset():
    from interface.dev import dev_reset
    dev_reset(ROOT_PROJECT_ROOT, SHARED_LOGIC_DIR, translation_func=_)

def _dev_enter(branch, force=False):
    from interface.dev import dev_enter
    dev_enter(branch, ROOT_PROJECT_ROOT, force=force, translation_func=_)

def _dev_create(tool_name):
    from interface.dev import dev_create
    dev_create(tool_name, ROOT_PROJECT_ROOT, translation_func=_)

def _dev_sanity_check(tool_name, fix=False):
    from interface.dev import dev_sanity_check
    return dev_sanity_check(tool_name, ROOT_PROJECT_ROOT, fix=fix, translation_func=_)

def _dev_audit_test(tool_name, fix=False):
    from interface.dev import dev_audit_test
    return dev_audit_test(tool_name, ROOT_PROJECT_ROOT, fix=fix)

def _dev_audit_bin(fix=False):
    from interface.dev import dev_audit_bin
    return dev_audit_bin(ROOT_PROJECT_ROOT, fix=fix)

def _dev_migrate_bin():
    from interface.dev import dev_migrate_bin
    return dev_migrate_bin(ROOT_PROJECT_ROOT)

def _dev_audit_archived():
    from interface.dev import dev_audit_archived
    return dev_audit_archived(ROOT_PROJECT_ROOT)

# --- Test Commands ---
def _test_tool_with_args(args):
    from interface.test import test_tool_with_args
    test_tool_with_args(args, ROOT_PROJECT_ROOT, translation_func=_)

# --- Lang Commands ---
def _audit_lang(lang_code, force=False, turing=False):
    from interface.lang import audit_lang
    audit_lang(lang_code, ROOT_PROJECT_ROOT, force=force, turing=turing, translation_func=_)

def _list_languages():
    from interface.lang import list_languages
    list_languages(ROOT_PROJECT_ROOT, translation_func=_)

# --- Rule Commands ---
def _show_rule():
    from interface.config import generate_ai_rule
    generate_ai_rule(ROOT_PROJECT_ROOT)

def _inject_rule():
    from interface.config import inject_rule
    inject_rule(ROOT_PROJECT_ROOT)

def _generate_ai_rule(name, description, globs, always_apply):
    from interface.config import generate_ai_rule
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
        from interface.git import install_hooks
        if install_hooks(ROOT_PROJECT_ROOT):
            print(f"  {BOLD}{GREEN}Installed{RESET} post-checkout hook.")
        else:
            print(f"  {BOLD}{YELLOW}Skipped{RESET}: hook already exists or .git not found.")
    elif subcmd == "uninstall-hooks":
        from interface.git import uninstall_hooks
        if uninstall_hooks(ROOT_PROJECT_ROOT):
            print(f"  {BOLD}{GREEN}Removed{RESET} post-checkout hook.")
        else:
            print(f"  {BOLD}{YELLOW}Skipped{RESET}: no AITerminalTools hook found.")
    elif subcmd == "locker":
        from interface.git import get_persistence_manager
        pm = get_persistence_manager(ROOT_PROJECT_ROOT)
        lockers = pm.list_lockers()
        if not lockers:
            print(f"  No lockers.")
        else:
            for l in lockers:
                branch = l.get("branch", "?")
                size = l.get("size_mb", 0)
                print(f"  {BOLD}{l['key']}{RESET}: branch={branch}, size={size}MB")
    elif subcmd == "docs":
        from interface.dev import list_docs
        scope = rest[0] if rest else "root"
        docs = list_docs(scope)
        print(f"  {BOLD}Docs at{RESET} {DIM}{docs['path']}{RESET}")
        print(f"  README:    {docs['readme'] or DIM + 'none' + RESET}")
        print(f"  for_agent: {docs['for_agent'] or DIM + 'none' + RESET}")
        reports = docs['reports']
        if reports:
            print(f"  Reports ({len(reports)}):")
            for r in reports[:15]:
                print(f"    {DIM}{r['name']}{RESET}")
        else:
            print(f"  Reports:   {DIM}none{RESET}")
    elif subcmd == "report":
        if not rest:
            print(f"Usage: TOOL --dev report <scope> <topic>")
            print(f"  scope: root, tool/LLM, provider/zhipu, etc.")
            print(f"  topic: short description (becomes filename)")
            return
        scope = rest[0]
        topic = " ".join(rest[1:]) if len(rest) > 1 else "untitled"
        from interface.dev import create_report
        path = create_report(scope, topic, f"# {topic}\n\n## Summary\n\n(Fill in)\n\n## Changes Made\n\n## Issues Found & Fixed\n\n## Next Steps\n")
        print(f"  {BOLD}{GREEN}Created{RESET} {DIM}{path}{RESET}")
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
        print(f"  docs [scope]                      List README/for_agent/reports at scope")
        print(f"  report <scope> <topic>            Create a new report")


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
    ip.add_argument("--docs", action="store_true", help="Also audit documentation files")
    qp = audit_sub.add_parser("quality", help="Audit hooks, interfaces, and skills")
    qp.add_argument("--tool", help="Audit specific tool only")
    qp.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    qp.add_argument("--exclude", help="Comma-separated tool names to skip")
    qp.add_argument("--no-skills", action="store_true", help="Skip skills audit")
    cp = audit_sub.add_parser("code", help="Dead code, unused imports/variables, syntax errors")
    cp.add_argument("--fix", action="store_true", help="Auto-fix safe issues")
    cp.add_argument("--targets", nargs="*", help="Directories to scan (default: logic/ tool/ interface/)")

    parsed = ap.parse_args(audit_args)
    root = Path(__file__).resolve().parent

    if parsed.audit_command == "imports":
        from interface.audit import (
            audit_imports_all, audit_imports_tool, audit_imports_docs,
            format_imports_report, imports_to_json,
        )
        exclude = [x.strip() for x in (parsed.exclude or "").split(",") if x.strip()]
        if parsed.tool:
            tool_dir = root / "tool" / parsed.tool
            if not tool_dir.exists():
                print(f"Tool not found: {parsed.tool}")
            else:
                issues = audit_imports_tool(tool_dir, root)
                results = {parsed.tool: issues} if issues else {}
                print(imports_to_json(results) if parsed.as_json else format_imports_report(results))
        else:
            results = audit_imports_all(root, exclude=exclude or ["GOOGLE.CDMCP"])
            if getattr(parsed, "docs", False):
                doc_issues = audit_imports_docs(root)
                if doc_issues:
                    results["__docs__"] = doc_issues
            print(imports_to_json(results) if parsed.as_json else format_imports_report(results))
    elif parsed.audit_command == "quality":
        from interface.audit import (
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
    elif parsed.audit_command == "code":
        from interface.audit import run_full_audit, print_report
        targets = parsed.targets or None
        report = run_full_audit(targets=targets, auto_fix=parsed.fix)
        print_report(report)
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

    dp = sub.add_parser("tools-deep", help="Search tools at section/command level")
    dp.add_argument("query", nargs="+", help="Search query")
    dp.add_argument("-n", "--top", type=int, default=10, help="Max results")

    ip = sub.add_parser("interfaces", help="Search tool interfaces")
    ip.add_argument("query", nargs="+", help="Search query")
    ip.add_argument("-n", "--top", type=int, default=5, help="Max results")

    skp = sub.add_parser("skills", help="Search skills")
    skp.add_argument("query", nargs="+", help="Search query")
    skp.add_argument("-n", "--top", type=int, default=5, help="Max results")
    skp.add_argument("--tool", dest="skill_tool", default=None, help="Scope to a specific tool")

    lp = sub.add_parser("lessons", help="Search lessons by semantic similarity")
    lp.add_argument("query", nargs="+", help="Search query")
    lp.add_argument("-n", "--top", type=int, default=5, help="Max results")
    lp.add_argument("--tool", dest="lesson_tool", default=None, help="Scope to a specific tool")

    dip = sub.add_parser("discoveries", help="Search discoveries")
    dip.add_argument("query", nargs="+", help="Search query")
    dip.add_argument("-n", "--top", type=int, default=5, help="Max results")
    dip.add_argument("--tool", dest="discovery_tool", default=None, help="Scope to a specific tool")

    docp = sub.add_parser("docs", help="Search project documentation (root, logic, interface)")
    docp.add_argument("query", nargs="+", help="Search query")
    docp.add_argument("-n", "--top", type=int, default=10, help="Max results")

    allp = sub.add_parser("all", help="Search across all knowledge (tools, skills, lessons, discoveries, docs)")
    allp.add_argument("query", nargs="+", help="Search query")
    allp.add_argument("-n", "--top", type=int, default=10, help="Max results")
    allp.add_argument("--tool", dest="all_tool", default=None, help="Scope to a specific tool")

    parsed = sp.parse_args(search_args)
    if not parsed.search_target:
        sp.print_help()
        return

    from interface.search import search_tools, search_interfaces, search_skills, search_tools_deep, search_lessons, search_discoveries, search_docs, search_all

    query = " ".join(parsed.query)
    top_k = parsed.top

    if parsed.search_target == "tools":
        results = search_tools(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "tools-deep":
        results = search_tools_deep(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "interfaces":
        results = search_interfaces(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "skills":
        tool_name = getattr(parsed, "skill_tool", None)
        results = search_skills(ROOT_PROJECT_ROOT, query, top_k=top_k, tool_name=tool_name)
    elif parsed.search_target == "lessons":
        tool_name = getattr(parsed, "lesson_tool", None)
        results = search_lessons(ROOT_PROJECT_ROOT, query, top_k=top_k, tool=tool_name)
    elif parsed.search_target == "discoveries":
        tool_name = getattr(parsed, "discovery_tool", None)
        results = search_discoveries(ROOT_PROJECT_ROOT, query, top_k=top_k, tool=tool_name)
    elif parsed.search_target == "docs":
        results = search_docs(ROOT_PROJECT_ROOT, query, top_k=top_k)
    elif parsed.search_target == "all":
        tool_name = getattr(parsed, "all_tool", None)
        results = search_all(ROOT_PROJECT_ROOT, query, top_k=top_k, tool=tool_name)
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
        elif rtype == "section":
            tool_name = meta.get("tool", "?")
            heading = meta.get("heading", "")
            preview = meta.get("preview", "")[:100]
            src = meta.get("source", "")
            file_path = meta.get("path", "")
            print(f"  {BOLD}{i}. {tool_name}{RESET} > {heading} ({score_pct}%) [{src}]")
            if preview:
                print(f"     {DIM}{preview}{RESET}")
            if file_path:
                print(f"     {DIM}-> {file_path}{RESET}")
        elif rtype == "command":
            tool_name = meta.get("tool", "?")
            cmd = meta.get("command", "")
            file_path = meta.get("path", "")
            print(f"  {BOLD}{i}. {tool_name}{RESET} ({score_pct}%)")
            print(f"     {DIM}$ {cmd}{RESET}")
            if file_path:
                print(f"     {DIM}-> {file_path}{RESET}")
        elif rtype == "interface":
            print(f"  {BOLD}{i}. {r['id']}{RESET} interface ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype == "skill":
            tool_tag = f" (tool: {meta['tool']})" if meta.get("tool") else ""
            print(f"  {BOLD}{i}. {r['id']}{RESET}{tool_tag} ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype == "lesson":
            sev = meta.get("severity", "info")
            tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
            lesson_text = meta.get("lesson", "")[:120]
            ts = meta.get("timestamp", "")[:10]
            print(f"  {BOLD}{i}. Lesson{RESET}{tool_tag} ({score_pct}%) [{sev}] {ts}")
            print(f"     {lesson_text}")
        elif rtype == "discovery":
            tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
            content = meta.get("content", "")[:120]
            ts = meta.get("timestamp", "")[:10]
            print(f"  {BOLD}{i}. Discovery{RESET}{tool_tag} ({score_pct}%) {ts}")
            print(f"     {content}")
        elif rtype in ("doc", "doc_section"):
            source = meta.get("source", "")
            heading = meta.get("heading", "")
            level = meta.get("level", "")
            module = meta.get("module", "")
            preview = meta.get("preview", "")[:100]
            label = module or source or r["id"]
            if heading:
                label = f"{label} > {heading}"
            level_tag = f" [{level}]" if level else ""
            print(f"  {BOLD}{i}. {label}{RESET} ({score_pct}%){level_tag}")
            if preview:
                print(f"     {DIM}{preview}{RESET}")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")


# Root ToolBase instance for hooks, call-register, agent, skills infrastructure
from interface.tool import ToolBase as _ToolBase
_root_tool = _ToolBase("TOOL", is_root=True)


def _workspace_handler(action: str, args: list):
    """Handle TOOL --create-workspace, --open-workspace, --close-workspace, --delete-workspace, --list-workspaces, --workspace."""
    from interface.workspace import get_workspace_manager
    from interface.status import fmt_status, fmt_detail, fmt_info

    wm = get_workspace_manager(ROOT_PROJECT_ROOT)

    if action == "create":
        target_path = args[0] if args else None
        bp_type = None
        name = None
        i = 1
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                bp_type = args[i + 1]
                i += 2
            elif args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            else:
                i += 1

        if not target_path:
            try:
                from tool.FILEDIALOG.interface.main import select_directory
                target_path = select_directory(title="Select workspace directory")
                if not target_path:
                    print(fmt_status("Cancelled.", style="error"))
                    return
            except ImportError:
                print(fmt_status("No path provided.", style="error"))
                print(fmt_detail("Usage: TOOL --create-workspace <path> [--type <blueprint>] [--name <name>]"))
                return

        try:
            info = wm.create_workspace(target_path, name=name, blueprint_type=bp_type)
            print(fmt_status("Workspace created."))
            print(fmt_detail(f"ID: {info['id']}"))
            print(fmt_detail(f"Path: {info['path']}"))
            print(fmt_detail(f"Blueprint: {info['blueprint_type']}"))
            print(fmt_info(f"Open: TOOL --open-workspace {info['id']}"))
        except FileExistsError as e:
            print(fmt_status("Already exists.", style="error"))
            print(fmt_detail(str(e)))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    elif action == "open":
        ws_id = args[0] if args else None
        if not ws_id:
            print(fmt_status("No workspace ID.", style="error"))
            print(fmt_detail("Usage: TOOL --open-workspace <workspace_id>"))
            return
        try:
            info = wm.open_workspace(ws_id)
            print(fmt_status("Workspace opened."))
            print(fmt_detail(f"Name: {info['name']}"))
            print(fmt_detail(f"Path: {info['path']}"))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    elif action == "close":
        info = wm.close_workspace()
        if info:
            print(fmt_status("Workspace closed."))
            print(fmt_detail(f"Name: {info['name']}"))
        else:
            print(fmt_status("No active workspace."))

    elif action == "delete":
        ws_id = args[0] if args else None
        if not ws_id:
            print(fmt_status("No workspace ID.", style="error"))
            print(fmt_detail("Usage: TOOL --delete-workspace <workspace_id>"))
            return
        try:
            wm.delete_workspace(ws_id)
            print(fmt_status("Workspace deleted."))
            print(fmt_detail(f"ID: {ws_id}"))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    elif action == "list":
        workspaces = wm.list_workspaces()
        if not workspaces:
            print(fmt_status("No workspaces."))
            print(fmt_detail("Create one: TOOL --create-workspace <path>"))
            return
        print(f"{BOLD}Workspaces ({len(workspaces)}){RESET}\n")
        for ws in workspaces:
            marker = f" {GREEN}(active){RESET}" if ws.get("active") else ""
            status = ws.get("status", "closed")
            print(f"  {BOLD}{ws['name']}{RESET}{marker}  {DIM}[{status}]{RESET}")
            print(f"    {DIM}ID: {ws['id']}  Path: {ws['path']}{RESET}")
            print(f"    {DIM}Blueprint: {ws.get('blueprint_type', 'default')}{RESET}")
        print()

    elif action == "status":
        info = wm.active_workspace_info()
        if info:
            print(f"{BOLD}Active Workspace{RESET}")
            print(fmt_detail(f"Name: {info['name']}"))
            print(fmt_detail(f"ID: {info['id']}"))
            print(fmt_detail(f"Path: {info['path']}"))
            print(fmt_detail(f"Blueprint: {info.get('blueprint_type', 'default')}"))
            print(fmt_detail(f"Status: {info.get('status', 'unknown')}"))
        else:
            print(fmt_status("No active workspace."))
            print(fmt_detail("Using default scope (AITerminalTools root)."))


def _tool_eco_handler(eco_args):
    """Handle ``TOOL eco`` — unified ecosystem navigation."""
    from interface.eco import (
        eco_dashboard, eco_search, eco_tool, eco_skill,
        eco_map, eco_here, eco_guide,
        eco_blueprint_commands, eco_run_command,
    )

    subcmd = eco_args[0] if eco_args else ""
    rest = eco_args[1:] if len(eco_args) > 1 else []

    if subcmd in ("-h", "--help", "help"):
        _print_eco_help()
        return

    if not subcmd:
        _print_eco_dashboard()
        return

    if subcmd == "search":
        if not rest:
            print(f"Usage: TOOL eco search <query> [-n top] [--scope all|tools|skills|lessons|docs]")
            return
        query_parts = []
        top_k = 10
        scope = "all"
        tool_filter = None
        i = 0
        while i < len(rest):
            if rest[i] in ("-n", "--top") and i + 1 < len(rest):
                top_k = int(rest[i + 1]); i += 2
            elif rest[i] == "--scope" and i + 1 < len(rest):
                scope = rest[i + 1]; i += 2
            elif rest[i] == "--tool" and i + 1 < len(rest):
                tool_filter = rest[i + 1]; i += 2
            else:
                query_parts.append(rest[i]); i += 1
        query = " ".join(query_parts)
        results = eco_search(ROOT_PROJECT_ROOT, query, scope=scope, top_k=top_k, tool=tool_filter)
        if not results:
            print(f"  No results for: {query}")
            return
        _print_search_results(results)
        return

    if subcmd == "tool":
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: TOOL eco tool <TOOL_NAME>")
            return
        info = eco_tool(ROOT_PROJECT_ROOT, name)
        if not info:
            print(f"  {BOLD}{RED}Not found:{RESET} {name}")
            return
        _print_tool_detail(info)
        return

    if subcmd == "skill":
        name = rest[0] if rest else None
        if not name:
            print(f"Usage: TOOL eco skill <skill_name>")
            return
        content = eco_skill(ROOT_PROJECT_ROOT, name)
        if not content:
            print(f"  {BOLD}{RED}Not found:{RESET} {name}")
            return
        print(content)
        return

    if subcmd == "map":
        emap = eco_map(ROOT_PROJECT_ROOT)
        _print_map(emap)
        return

    if subcmd == "here":
        cwd = rest[0] if rest else None
        ctx = eco_here(ROOT_PROJECT_ROOT, cwd)
        _print_here(ctx)
        return

    if subcmd == "guide":
        guide = eco_guide(ROOT_PROJECT_ROOT)
        print(guide)
        return

    if subcmd == "recall":
        query = " ".join(rest) if rest else ""
        if not query:
            print(f"Usage: TOOL eco recall <query>")
            return
        import subprocess
        subprocess.run(["python3", str(ROOT_PROJECT_ROOT / "bin" / "BRAIN"), "recall", query])
        return

    if subcmd == "cmds":
        cmds = eco_blueprint_commands(ROOT_PROJECT_ROOT)
        if not cmds:
            print(f"  No blueprint commands defined.")
            print(f"  {DIM}Add 'commands' to your brain blueprint JSON.{RESET}")
            return
        print(f"\n  {BOLD}Blueprint Commands{RESET}\n")
        for name, defn in cmds.items():
            if isinstance(defn, str):
                print(f"  {BOLD}{name}{RESET}")
                print(f"    {DIM}$ {defn}{RESET}")
            else:
                desc = defn.get("description", "")
                run_cmd = defn.get("run", "")
                print(f"  {BOLD}{name}{RESET}  {desc}")
                print(f"    {DIM}$ {run_cmd}{RESET}")
        print(f"\n  {DIM}Run: TOOL eco cmd <name>{RESET}")
        return

    if subcmd == "cmd":
        cmd_name = rest[0] if rest else None
        if not cmd_name:
            print(f"Usage: TOOL eco cmd <command_name>")
            return
        cmd_str = eco_run_command(ROOT_PROJECT_ROOT, cmd_name)
        if not cmd_str:
            print(f"  {BOLD}{RED}Not found:{RESET} {cmd_name}")
            print(f"  {DIM}Run TOOL eco cmds to see available commands.{RESET}")
            return
        print(f"  {BOLD}Running:{RESET} {DIM}{cmd_str}{RESET}")
        import subprocess
        subprocess.run(cmd_str, shell=True, cwd=str(ROOT_PROJECT_ROOT))
        return

    # Default: try as dashboard
    if subcmd:
        from interface.utils import suggest_commands
        known = ["search", "tool", "skill", "map", "here", "guide", "recall", "cmds", "cmd"]
        matches = suggest_commands(subcmd, known, n=2, cutoff=0.4)
        if matches:
            print(f"  {BOLD}Unknown:{RESET} {subcmd}. Did you mean: {', '.join(matches)}?")
        else:
            print(f"  {BOLD}Unknown:{RESET} {subcmd}")
        print(f"  {DIM}TOOL eco --help for available commands.{RESET}")
        return


def _print_eco_help():
    """Print eco subcommand help."""
    print(f"\n{BOLD}TOOL --eco{RESET} — Ecosystem Navigation\n")
    print(f"  {BOLD}Explore{RESET}")
    print(f"    --eco                      Dashboard — tools, skills, brain overview")
    print(f"    --eco search <query>       Semantic search across all knowledge")
    print(f"    --eco tool <name>          Deep-dive into a specific tool")
    print(f"    --eco skill <name>         Read a development skill/pattern")
    print(f"    --eco map                  Ecosystem directory structure")
    print(f"    --eco here [cwd]           Context-aware help for current directory")
    print(f"\n  {BOLD}Remember{RESET}")
    print(f"    --eco recall <query>       Search brain memory (lessons, activity)")
    print(f"    --eco guide                Onboarding guide for new agents")
    print(f"\n  {BOLD}Shortcuts{RESET}")
    print(f"    --eco cmds                 List blueprint-defined shortcut commands")
    print(f"    --eco cmd <name>           Run a blueprint shortcut command")
    print(f"\n  {BOLD}Options{RESET}")
    print(f"    --eco search <q> --scope tools|skills|lessons|docs  Scoped search")
    print(f"    --eco search <q> -n 5      Limit results")
    print(f"    --eco search <q> --tool LLM  Scope to a tool")
    print(f"\n  {BOLD}Per-tool:{RESET} TOOL_NAME --eco (e.g., LLM --eco, GIT --eco)")
    print()


def _print_search_results(results):
    """Format and print search results (shared with --search)."""
    for i, r in enumerate(results, 1):
        meta = r.get("meta", {})
        score_pct = int(r["score"] * 100)
        rtype = meta.get("type", "unknown")

        if rtype == "tool":
            desc = meta.get("description") or meta.get("purpose") or ""
            print(f"  {BOLD}{i}. {r['id']}{RESET} ({score_pct}%)")
            if desc:
                print(f"     {desc}")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype in ("section", "command"):
            tool_name = meta.get("tool", "?")
            heading = meta.get("heading", "") or meta.get("command", "")
            preview = meta.get("preview", "")[:100]
            print(f"  {BOLD}{i}. {tool_name}{RESET} > {heading} ({score_pct}%)")
            if preview:
                print(f"     {DIM}{preview}{RESET}")
        elif rtype == "skill":
            tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
            print(f"  {BOLD}{i}. {r['id']}{RESET}{tool_tag} ({score_pct}%)")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")
        elif rtype == "lesson":
            sev = meta.get("severity", "info")
            tool_tag = f" [{meta['tool']}]" if meta.get("tool") else ""
            lesson_text = meta.get("lesson", "")[:120]
            print(f"  {BOLD}{i}. Lesson{RESET}{tool_tag} ({score_pct}%) [{sev}]")
            print(f"     {lesson_text}")
        elif rtype in ("doc", "doc_section"):
            label = meta.get("module") or meta.get("source") or r["id"]
            heading = meta.get("heading", "")
            if heading:
                label = f"{label} > {heading}"
            preview = meta.get("preview", "")[:100]
            print(f"  {BOLD}{i}. {label}{RESET} ({score_pct}%)")
            if preview:
                print(f"     {DIM}{preview}{RESET}")
        else:
            print(f"  {BOLD}{i}. {r['id']}{RESET} ({score_pct}%) [{rtype}]")
            print(f"     {DIM}{meta.get('path', '')}{RESET}")


def _print_tool_detail(info):
    """Print detailed tool overview."""
    print(f"\n  {BOLD}{info['name']}{RESET}")
    if info.get("description"):
        print(f"  {info['description']}")
    print()

    checks = [
        ("README.md", info.get("has_readme")),
        ("for_agent.md", info.get("has_for_agent")),
        ("interface/main.py", info.get("has_interface")),
        ("hooks/", info.get("has_hooks")),
        ("test/", info.get("has_tests")),
    ]
    for label, ok in checks:
        marker = f"{GREEN}✓{RESET}" if ok else f"{DIM}·{RESET}"
        print(f"  {marker} {label}")

    if info.get("test_count"):
        print(f"    {DIM}{info['test_count']} test file(s){RESET}")

    if info.get("dependencies"):
        print(f"\n  {BOLD}Dependencies:{RESET} {', '.join(info['dependencies'])}")

    if info.get("interface_functions"):
        print(f"\n  {BOLD}Interface:{RESET}")
        for fn in info["interface_functions"][:10]:
            print(f"    {fn}()")

    print(f"\n  {BOLD}Actions:{RESET}")
    print(f"    TOOL eco search \"{info['name']}\"  — search related knowledge")
    if info.get("has_for_agent"):
        print(f"    Read: tool/{info['name']}/for_agent.md")
    if info.get("has_readme"):
        print(f"    Read: tool/{info['name']}/README.md")
    print()


def _print_map(emap):
    """Print ecosystem structure map."""
    print(f"\n  {BOLD}Ecosystem Map{RESET}  {DIM}{emap['root']}{RESET}\n")
    for dirname, info in emap["directories"].items():
        if not info["exists"]:
            continue
        children_str = ""
        if info["children"]:
            children_str = f"  {DIM}[{', '.join(info['children'][:8])}" + \
                (f", +{len(info['children']) - 8}" if len(info["children"]) > 8 else "") + \
                f"]{RESET}"
        print(f"  {BOLD}{dirname}{RESET}  {info['purpose']}")
        if children_str:
            print(f"  {children_str}")
    print()


def _print_here(ctx):
    """Print context-aware navigation."""
    print(f"\n  {BOLD}CWD:{RESET} {ctx['cwd']}")

    if not ctx.get("in_project"):
        print(f"  {DIM}Outside project.{RESET}")
        if ctx.get("suggestion"):
            print(f"  {ctx['suggestion']}")
        return

    print(f"  {BOLD}Level:{RESET} {ctx['level']}")
    if ctx.get("tool"):
        print(f"  {BOLD}Tool:{RESET} {ctx['tool']}")
    if ctx.get("module"):
        print(f"  {BOLD}Module:{RESET} {ctx['module']}")

    if ctx.get("docs"):
        print(f"\n  {BOLD}Docs here:{RESET}")
        for d in ctx["docs"]:
            print(f"    {DIM}{d}{RESET}")

    if ctx.get("actions"):
        print(f"\n  {BOLD}Suggested:{RESET}")
        for a in ctx["actions"]:
            print(f"    {a}")
    print()


def _print_eco_dashboard():
    """Print ecosystem overview dashboard."""
    from interface.eco import eco_dashboard
    data = eco_dashboard(ROOT_PROJECT_ROOT)
    tools = data["tools"]
    skills = data["skills"]
    brain = data["brain"]
    ws = data.get("workspace")
    bp_cmds = data.get("blueprint_cmds", [])

    print(f"\n  {BOLD}Ecosystem Dashboard{RESET}")
    print(f"  {'─' * 44}")
    print(f"  {BOLD}Tools{RESET}:    {tools['installed']}/{tools['total']} installed")
    print(f"  {BOLD}Skills{RESET}:   {skills['core']} core, {skills['library']} library")
    print(f"  {BOLD}Brain{RESET}:    {brain['tasks_active']} active tasks, {brain['tasks_done']} done, {brain['lessons']} lessons")
    if brain.get("context_age_min", -1) >= 0:
        age = brain["context_age_min"]
        age_str = f"{age}m ago" if age < 60 else f"{age // 60}h{age % 60}m ago"
        print(f"  {BOLD}Context{RESET}:  updated {age_str}")
    else:
        print(f"  {BOLD}Context{RESET}:  {RED}not initialized{RESET}")
    if ws:
        print(f"  {BOLD}Workspace{RESET}: {ws['name']} ({DIM}{ws['path']}{RESET})")
    if bp_cmds:
        print(f"  {BOLD}Shortcuts{RESET}: {', '.join(bp_cmds)}")
    print(f"  {'─' * 44}")
    print(f"\n  {DIM}TOOL --eco --help for all commands.{RESET}")
    print(f"  {DIM}TOOL --eco guide for onboarding.{RESET}\n")


def _tool_migrate_handler(args):
    """Handle TOOL --migrate --<level> <domain> [options]."""
    from logic.command.migrate import (
        list_domains, execute_migration, MIGRATION_LEVELS,
        get_domain_info, check_pending, scan_domain,
    )

    if not args or args[0] in ["-h", "--help", "help"]:
        print(f"{BOLD}TOOL --migrate{RESET} — Migration framework\n")
        print(f"  Usage: TOOL --migrate --<level> <domain> [options]\n")
        print(f"  {BOLD}Levels{RESET}")
        for lv in MIGRATION_LEVELS:
            print(f"    --{lv}")
        print(f"\n  {BOLD}Sub-commands{RESET}")
        print(f"    --list                    List all migration domains")
        print(f"    --scan <domain>           Discover available items in a domain")
        print(f"    --namespace <N>           Scope to a specific sub-source")
        print(f"\n  {BOLD}Domains{RESET}")
        for d in list_domains():
            name = d.get("domain", "?")
            desc = d.get("description", "")[:60]
            levels = ", ".join(d.get("levels", []))
            print(f"    {name:20s} [{levels}]")
            if desc:
                print(f"    {DIM}{desc}{RESET}")
        print(f"\n  {BOLD}Examples{RESET}")
        print(f"    TOOL --migrate --list")
        print(f"    TOOL --migrate --scan CLIANYTHING")
        print(f"    TOOL --migrate --scan CLIANYTHING --namespace blender")
        print(f"    TOOL --migrate --draft-tool CLIANYTHING blender")
        print(f"    TOOL --migrate --infrastructure astral-sh --version 3.12 --platform macos-arm64")
        print(f"    TOOL --migrate --draft-tool CLIANYTHING --all")
        return

    if args[0] == "--list":
        domains = list_domains()
        if not domains:
            print(f"  {BOLD}No migration domains found.{RESET}")
            return
        print(f"  {BOLD}Migration domains{RESET} ({len(domains)})\n")
        for d in domains:
            name = d.get("domain", "?")
            desc = d.get("description", "")[:70]
            levels = ", ".join(d.get("levels", []))
            status = check_pending(name)
            migrated = status.get("migrated", 0)
            total = status.get("total", "?")
            print(f"    {BOLD}{name}{RESET}")
            if desc:
                print(f"    {DIM}{desc}{RESET}")
            print(f"    Levels: {levels}")
            print(f"    Status: {migrated}/{total} migrated")
            print()
        return

    if args[0] == "--scan":
        domain = args[1] if len(args) > 1 else None
        if not domain:
            print(f"  {BOLD}{RED}Missing domain.{RESET} Usage: TOOL --migrate --scan <domain> [--namespace <N>]")
            return
        ns = None
        if "--namespace" in args:
            ns_idx = args.index("--namespace")
            if ns_idx + 1 < len(args):
                ns = args[ns_idx + 1]
        result = scan_domain(domain, namespace=ns)
        if "error" in result:
            print(f"  {BOLD}{RED}Scan failed.{RESET} {result['error']}")
            return
        available = result.get("available", [])
        migrated = result.get("migrated", [])
        pending = result.get("pending", [])
        print(f"  {BOLD}Scan: {domain}{RESET} — {len(available)} items found\n")
        if migrated:
            print(f"  {BOLD}Migrated{RESET} ({len(migrated)})")
            for item in migrated:
                print(f"    {GREEN}{item['name']:20s}{RESET} -> {item.get('tool', '?'):14s} [{item.get('status', 'draft')}]")
        if pending:
            print(f"  {BOLD}Available{RESET} ({len(pending)})")
            for item in pending:
                print(f"    {item['name']:20s} -> {item.get('tool', '?')}")
        if not migrated and not pending:
            print(f"  {DIM}No items found.{RESET}")
        return

    level = None
    domain = None
    namespace = None
    remaining = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--") and arg[2:] in MIGRATION_LEVELS:
            level = arg[2:]
        elif arg == "--namespace" and i + 1 < len(args):
            namespace = args[i + 1]
            i += 1
        elif domain is None and not arg.startswith("-"):
            domain = arg
        else:
            remaining.append(arg)
        i += 1

    if namespace:
        remaining.extend(["--namespace", namespace])

    if not level:
        print(f"  {BOLD}{RED}Missing level.{RESET} Use --<level> (e.g. --draft-tool, --infrastructure)")
        return

    if not domain:
        print(f"  {BOLD}{RED}Missing domain.{RESET} Specify a domain name (e.g. CLI-Anything, astral-sh)")
        return

    info = get_domain_info(domain)
    if not info:
        print(f"  {BOLD}{RED}Unknown domain.{RESET} {DIM}{domain}{RESET}")
        print(f"  Available: {', '.join(d['domain'] for d in list_domains())}")
        return

    code = execute_migration(domain, level, remaining)
    sys.exit(code)


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
    "--eco": lambda args: _tool_eco_handler(args),
    "--hooks": lambda args: _root_tool._handle_hooks_command(args),
    "--call-register": lambda args: _root_tool._handle_call_register(args),
    "--assistant": lambda args: _root_tool._handle_assistant(args),
    "--setup": lambda args: _root_tool.run_setup(),
    "--skills": lambda args: _root_tool._handle_skills_command(args),
    "--migrate": lambda args: _tool_migrate_handler(args),
    "--create-workspace": lambda args: _workspace_handler("create", args),
    "--delete-workspace": lambda args: _workspace_handler("delete", args),
    "--open-workspace": lambda args: _workspace_handler("open", args),
    "--close-workspace": lambda args: _workspace_handler("close", args),
    "--list-workspaces": lambda args: _workspace_handler("list", args),
    "--workspace": lambda args: _workspace_handler("status", args),
}

# Shorthand: --agent/--ask/--plan as top-level commands (omit --assistant).
# Controlled by ALLOW_ASSISTANT_SHORTHAND in logic.agent.command.
try:
    from logic._.agent.command import ALLOW_ASSISTANT_SHORTHAND
    if ALLOW_ASSISTANT_SHORTHAND:
        _TOOL_FLAG_HANDLERS["--agent"] = lambda args: _root_tool._handle_agent(args)
        _TOOL_FLAG_HANDLERS["--ask"] = lambda args: _root_tool._handle_agent(args, mode="ask")
        _TOOL_FLAG_HANDLERS["--plan"] = lambda args: _root_tool._handle_agent(args, mode="plan")
except ImportError:
    pass


def _print_tool_help():
    """Print unified help for all TOOL commands."""
    print(f"{BOLD}AITerminalTools Manager{RESET}")
    print(f"\nUsage: TOOL <command> [options]\n")
    print(f"  {BOLD}Ecosystem Navigation (start here){RESET}")
    print(f"    --eco                      Dashboard — tools, skills, brain overview")
    print(f"    --eco search <query>       Find anything across the ecosystem")
    print(f"    --eco tool <name>          Deep-dive into a specific tool")
    print(f"    --eco skill <name>         Read a development skill/pattern")
    print(f"    --eco guide                Onboarding guide for new agents")
    print(f"    --eco map | here | recall  Structure, context, memory search")
    print(f"    --eco cmds | cmd <name>    Blueprint shortcut commands")
    print(f"\n  {BOLD}Tool Lifecycle{RESET}")
    print(f"    --install <name>           Install a tool")
    print(f"    --reinstall <name>         Reinstall a tool")
    print(f"    --uninstall <name> [-y]    Uninstall a tool")
    print(f"    --list [--force]           List all available tools")
    print(f"    --status                   Show installed tools and their status")
    print(f"\n  {BOLD}Quality & Search{RESET}")
    print(f"    --audit <sub>              Code quality audits (imports, quality, code)")
    print(f"    --search <sub> <query>     Semantic search (tools, skills, lessons, docs, all)")
    print(f"    --lang <sub>               Language management (audit, list)")
    print(f"\n  {BOLD}Development{RESET}")
    print(f"    --dev <sub>                Developer commands (create, sync, sanity-check)")
    print(f"    --test <sub>               Run tests")
    print(f"    --config <sub>             Manage global configuration")
    print(f"    --rule <sub>               AI rule management")
    print(f"    --migrate --<level> <domain>  Migration framework (tool, infrastructure, skills)")
    print(f"\n  {BOLD}Assistant{RESET}")
    print(f"    --agent <prompt>           Agent mode")
    print(f"    --ask <prompt>             Ask mode (read-only)")
    print(f"    --plan <prompt>            Plan mode")
    print(f"    --assistant <sub>          Manage sessions")
    print(f"\n  {BOLD}Workspace{RESET}")
    print(f"    --create-workspace <path>  Create a new workspace")
    print(f"    --list-workspaces          List all workspaces")
    print(f"    --workspace                Show active workspace")
    print(f"\nUse TOOL <command> --help for details on each command.")


def main():
    stripped_argv = [a for a in sys.argv[1:] if a not in ["--no-warning", "--tool-quiet"]]

    current_lang = get_global_config("language", "en")
    set_rtl_mode(current_lang in ["ar"])

    if not stripped_argv or stripped_argv[0] in ["-h", "--help", "help"]:
        _print_tool_help()
        return

    primary = stripped_argv[0]
    _b = get_color("BOLD", "\033[1m")
    _d = get_color("DIM", "\033[2m")
    _r = get_color("RESET", "\033[0m")

    # Enforce --eco prefix to avoid tool name collision
    if primary == "eco":
        print(f"{_b}Use --eco{_r} (with prefix).")
        print(f"  {_d}TOOL --eco                   Dashboard{_r}")
        print(f"  {_d}TOOL --eco search \"query\"     Search ecosystem{_r}")
        print(f"  {_d}TOOL --eco --help             All eco commands{_r}")
        return

    canon = primary if primary.startswith("--") else f"--{primary.lstrip('-')}"

    if canon in _TOOL_FLAG_HANDLERS:
        _TOOL_FLAG_HANDLERS[canon](stripped_argv[1:])
        return

    user_cmd = primary
    from interface.utils import suggest_commands
    flags = list(_TOOL_FLAG_HANDLERS.keys())
    bare_names = [f.lstrip("-") for f in flags]
    candidates = flags + bare_names
    matches = suggest_commands(user_cmd, candidates, n=3, cutoff=0.5)
    normalized = []
    for m in matches:
        c = f"--{m}" if not m.startswith("-") else m
        if c not in normalized:
            normalized.append(c)
    print(f"{_b}Unknown command:{_r} {user_cmd}")
    if normalized:
        hint = ", ".join(normalized)
        print(f"  {_d}Did you mean: {hint}?{_r}")
    print(f"  {_d}Use TOOL --help for available commands.{_r}")

if __name__ == "__main__":
    main()
