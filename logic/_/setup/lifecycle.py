import sys
import json
from pathlib import Path

from logic._.config import get_color
from logic._.setup.engine import ToolEngine

def install_tool(tool_name: str, project_root: Path) -> bool:
    engine = ToolEngine(tool_name, project_root)
    return engine.install()

def reinstall_tool(tool_name: str, project_root: Path) -> bool:
    engine = ToolEngine(tool_name, project_root)
    return engine.reinstall()

def uninstall_tool(tool_name: str, project_root: Path, force_yes: bool = False, translation_func = None) -> bool:
    tool_dir = project_root / "tool" / tool_name
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    BOLD = get_color("BOLD", "\033[1m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    if not tool_dir.exists():
        print(f"{BOLD}{RED}" + _("label_error", "Error") + f"{RESET}: " + _("tool_not_found_local", "Tool '{name}' is not installed.", name=tool_name))
        return False

    if not force_yes:
        if sys.stdin.isatty():
            confirm_msg = _("confirm_uninstall", "Are you sure you want to uninstall '{name}'? (y/N): ", name=tool_name)
            confirm = input(confirm_msg)
            # Move up one line and erase the confirmation prompt
            sys.stdout.write(f"\033[A\r\033[K")
            sys.stdout.flush()
            
            if confirm.lower() not in ['y', 'yes']:
                print(_("uninstall_cancelled", "Uninstall cancelled."))
                return False
        else:
            print(_("non_interactive_skip", "Non-interactive session, skipping confirmation. Use -y to force."))
            return False

    engine = ToolEngine(tool_name, project_root)
    return engine.uninstall()

def list_tools(project_root: Path, force: bool = False, translation_func = None):
    """List all available tools and their status."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    cache_path = project_root / "data" / "tools.json"
    
    BOLD = get_color("BOLD", "\033[1m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RESET = get_color("RESET", "\033[0m")

    cache = {}
    cached_used = False
    if not force and cache_path.exists():
        try:
            with open(cache_path, 'r') as f: 
                cache = json.load(f)
                cached_used = True
        except: pass
    
    # Re-scan if empty or forced
    if not cache or force:
        registry_path = project_root / "tool.json"
        if not registry_path.exists():
            print(f"{BOLD}\033[31mError\033[0m: Global tool.json not found.")
            return
            
        with open(registry_path, 'r') as f:
            tools_list = json.load(f).get("tools", [])
        
        cache = {}
        for name in tools_list:
            tool_json = project_root / "tool" / name / "tool.json"
            info = {"installed": (project_root / "tool" / name).exists()}
            if tool_json.exists():
                try:
                    with open(tool_json, 'r') as f:
                        data = json.load(f)
                        info["description"] = data.get("description", "No description")
                        info["purpose"] = data.get("purpose", "No purpose")
                except:
                    info["description"] = "Error reading tool.json"
            else:
                info["description"] = _("tool_not_found_locally", "Not found locally (run 'TOOL install' to fetch)")
                info["purpose"] = "N/A"
            cache[name] = info
            
        # Save cache
        cache_path.parent.mkdir(exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)

    # Display
    for name, info in sorted(cache.items()):
        status = "[installed]" if info.get("installed") else "[available]"
        print(f"{BOLD}{name}{RESET} {status}")
        print(f"  {info.get('description', 'No description')}")
        purpose_label = _("tool_list_purpose_label", "Purpose:")
        print(f"  {purpose_label} {info.get('purpose', 'No purpose')}\n")

    if cached_used:
        warning_msg = _("tool_list_cache_warning", "Warning: Displaying cached data. Use --force to refresh.")
        print(f"{BOLD}{YELLOW}{warning_msg}{RESET}")

