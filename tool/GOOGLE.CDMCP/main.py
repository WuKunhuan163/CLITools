#!/usr/bin/env python3
"""GOOGLE.CDMCP — Chrome DevTools MCP with visual overlays and tab management.

Provides agent-level browser automation with:
  - Tab group badges marking agent-controlled tabs
  - Focus indicators showing the current debug tab
  - Lock overlays preventing user interaction (with click-to-unlock)
  - Element highlighting via CSS selector
  - Privacy-aware configuration
"""
import sys
import argparse
import json
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.interface.tool import ToolBase
from logic.interface.config import get_color

_TOOL_DIR = Path(__file__).resolve().parent


def _load_api():
    """Lazy-load the CDMCP API module from the tool directory via importlib."""
    import importlib.util
    api_path = _TOOL_DIR / "logic" / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("cdmcp_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {
        "navigate": mod.navigate, "focus_tab": mod.focus_tab,
        "lock_tab": mod.lock_tab, "unlock_tab": mod.unlock_tab,
        "highlight_element": mod.highlight_element, "clear_highlight": mod.clear_highlight,
        "cleanup_tab": mod.cleanup_tab, "status": mod.status,
        "list_managed": mod.list_managed, "get_config": mod.get_config,
        "set_config_value": mod.set_config_value, "reset_config": mod.reset_config,
        "show_config_str": mod.show_config_str,
    }


class CDMCPTool(ToolBase):
    def __init__(self):
        super().__init__("GOOGLE.CDMCP")

    def run(self):
        parser = argparse.ArgumentParser(
            description="CDMCP: Chrome DevTools MCP with visual overlays",
            add_help=False,
        )
        sub = parser.add_subparsers(dest="command", help="Subcommand")

        sub.add_parser("status", help="Check Chrome CDP availability and managed tabs")

        p_nav = sub.add_parser("navigate", help="Open URL in a managed CDMCP tab")
        p_nav.add_argument("url", help="URL to navigate to")

        p_focus = sub.add_parser("focus", help="Set focus indicator on a tab")
        p_focus.add_argument("pattern", help="URL pattern to match the tab")

        p_lock = sub.add_parser("lock", help="Lock a tab with overlay")
        p_lock.add_argument("pattern", help="URL pattern to match the tab")

        p_unlock = sub.add_parser("unlock", help="Unlock a tab")
        p_unlock.add_argument("pattern", help="URL pattern to match the tab")

        p_hl = sub.add_parser("highlight", help="Highlight an element by CSS selector")
        p_hl.add_argument("pattern", help="URL pattern to match the tab")
        p_hl.add_argument("selector", help="CSS selector for the element")
        p_hl.add_argument("--label", default="", help="Label for the highlight")

        p_clear = sub.add_parser("clear", help="Clear highlight from a tab")
        p_clear.add_argument("pattern", help="URL pattern to match the tab")

        p_cleanup = sub.add_parser("cleanup", help="Remove all overlays from a tab")
        p_cleanup.add_argument("pattern", help="URL pattern to match the tab")

        p_config = sub.add_parser("config", help="View or modify CDMCP configuration")
        p_config.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"),
                              help="Set a config value")
        p_config.add_argument("--reset", action="store_true",
                              help="Reset to defaults")

        sub.add_parser("tabs", help="List all managed CDMCP tabs")

        if self.handle_command_line(parser):
            return

        args = parser.parse_args()
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        YELLOW = get_color("YELLOW")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")

        api = _load_api()

        if args.command == "status":
            r = api["status"]()
            avail = r.get("chrome_available", False)
            print(f"  Chrome CDP: {BOLD}{GREEN if avail else RED}{'Available' if avail else 'Not available'}{RESET}")
            print(f"  Managed tabs: {r.get('managed_tabs', 0)}")
            if r.get("focused_tab"):
                print(f"  Focused: {r['focused_tab']}")
            if r.get("locked_tab"):
                print(f"  Locked: {r['locked_tab']}")
            cfg = r.get("config", {})
            print(f"  OAuth allowed: {cfg.get('allow_oauth', True)}")
            print(f"  Logging: {cfg.get('log_interactions', True)}")

        elif args.command == "navigate":
            r = api["navigate"](args.url)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Navigated{RESET} to {args.url} ({r.get('action', 'unknown')}).")
            else:
                print(f"  {BOLD}{RED}Failed{RESET} to navigate: {r.get('error', 'unknown')}")

        elif args.command == "focus":
            r = api["focus_tab"](args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Focused{RESET} on tab: {r.get('url', args.pattern)}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "lock":
            r = api["lock_tab"](args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{BLUE}Locked{RESET} tab: {args.pattern}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "unlock":
            r = api["unlock_tab"](args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Unlocked{RESET} tab: {args.pattern}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "highlight":
            r = api["highlight_element"](args.pattern, args.selector, label=args.label)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Highlighted{RESET}: {r.get('selector', args.selector)}")
                rect = r.get("rect", {})
                if rect:
                    print(f"  Position: ({rect.get('left',0):.0f}, {rect.get('top',0):.0f}) "
                          f"Size: {rect.get('width',0):.0f}x{rect.get('height',0):.0f}")
                elem = r.get("element", {})
                if elem:
                    print(f"  Element: <{elem.get('tag','?')}> type={elem.get('type','-')} "
                          f"name={elem.get('name','-')}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "clear":
            r = api["clear_highlight"](args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Cleared{RESET} highlight.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "cleanup":
            r = api["cleanup_tab"](args.pattern)
            if r.get("ok"):
                removed = r.get("removed", [])
                print(f"  {BOLD}{GREEN}Cleaned up{RESET} {len(removed)} overlays.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "config":
            if args.reset:
                api["reset_config"]()
                print(f"  {BOLD}{GREEN}Reset{RESET} configuration to defaults.")
            elif args.set:
                key, val = args.set
                try:
                    parsed = json.loads(val)
                except json.JSONDecodeError:
                    parsed = val
                api["set_config_value"](key, parsed)
                print(f"  {BOLD}{GREEN}Set{RESET} {key} = {json.dumps(parsed)}")
            else:
                print(f"  {BOLD}CDMCP Configuration{RESET}:")
                print(api["show_config_str"]())

        elif args.command == "tabs":
            tabs = api["list_managed"]()
            if tabs:
                for i, t in enumerate(tabs):
                    focused = " [FOCUSED]" if t.get("_cdmcp_focused") else ""
                    locked = " [LOCKED]" if t.get("_cdmcp_locked") else ""
                    print(f"  [{i+1}] {t.get('title', '?')[:50]:<50} {focused}{locked}")
                    print(f"      {t.get('url', '?')}")
            else:
                print(f"  {YELLOW}No managed tabs.{RESET}")

        else:
            parser.print_help()


def main():
    tool = CDMCPTool()
    tool.run()


if __name__ == "__main__":
    main()
