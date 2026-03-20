#!/usr/bin/env python3
import sys
from pathlib import Path

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

_ECO_CMD_REGISTRY = {}

def _eco_cmd(name, args):
    """Dispatch to an EcoCommand subclass by symmetric command name."""
    if name not in _ECO_CMD_REGISTRY:
        _module_map = {
            "install": ("logic._.install", "InstallCommand"),
            "reinstall": ("logic._.reinstall", "ReinstallCommand"),
            "uninstall": ("logic._.uninstall", "UninstallCommand"),
            "list": ("logic._.list", "ListCommand"),
            "status": ("logic._.status", "StatusCommand"),
            "rule": ("logic._.rule", "RuleCommand"),
            "skills": ("logic._.skills", "SkillsCommand"),
            "migrate": ("logic._.migrate", "MigrateCommand"),
            "dev": ("logic._.dev.command", "DevCommand"),
            "test": ("logic._.test.command", "TestCommand"),
            "config": ("logic._.config.command", "ConfigCommand"),
            "audit": ("logic._.audit.command", "AuditCommand"),
            "lang": ("logic._.lang.command", "LangCommand"),
            "search": ("logic._.search.command", "SearchCommand"),
            "eco": ("logic._.eco.command", "EcoNavCommand"),
        }
        entry = _module_map.get(name)
        if not entry:
            print(f"  Unknown eco command: {name}")
            return 1
        mod_path, cls_name = entry
        import importlib
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        _ECO_CMD_REGISTRY[name] = cls(
            project_root=ROOT_PROJECT_ROOT,
            tool_name="TOOL",
            translation_func=_,
        )
    return _ECO_CMD_REGISTRY[name].handle(args)

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

# Maps --flag to handler function
_TOOL_FLAG_HANDLERS = {
    "--dev": lambda args: _eco_cmd("dev", args),
    "--test": lambda args: _eco_cmd("test", args),
    "--config": lambda args: _eco_cmd("config", args),
    "--install": lambda args: _eco_cmd("install", args),
    "--reinstall": lambda args: _eco_cmd("reinstall", args),
    "--uninstall": lambda args: _eco_cmd("uninstall", args),
    "--list": lambda args: _eco_cmd("list", args),
    "--status": lambda args: _eco_cmd("status", args),
    "--audit": lambda args: _eco_cmd("audit", args),
    "--lang": lambda args: _eco_cmd("lang", args),
    "--rule": lambda args: _eco_cmd("rule", args),
    "--search": lambda args: _eco_cmd("search", args),
    "--eco": lambda args: _eco_cmd("eco", args),
    "--hooks": lambda args: _root_tool._handle_hooks_command(args),
    "--call-register": lambda args: _root_tool._handle_call_register(args),
    "--assistant": lambda args: _root_tool._handle_assistant(args),
    "--setup": lambda args: _root_tool.run_setup(),
    "--skills": lambda args: _eco_cmd("skills", args),
    "--migrate": lambda args: _eco_cmd("migrate", args),
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
