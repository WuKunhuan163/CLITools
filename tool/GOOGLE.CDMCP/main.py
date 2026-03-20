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
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color

_TOOL_DIR = Path(__file__).resolve().parent


def _load_api():
    """Lazy-load the CDMCP API module from the tool directory via importlib."""
    import importlib.util
    api_path = _TOOL_DIR / "logic" / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("cdmcp_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CDMCPTool(ToolBase):
    def __init__(self):
        super().__init__("GOOGLE.CDMCP")

    def _handle_endpoint(self, args):
        import importlib.util
        ep_path = _TOOL_DIR / "logic" / "endpoint.py"
        spec = importlib.util.spec_from_file_location("cdmcp_endpoint", str(ep_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.handle_cdmcp_endpoint(args)

    def run(self):
        parser = argparse.ArgumentParser(
            description="CDMCP: Chrome DevTools MCP with visual overlays",
            epilog="MCP commands use --mcp- prefix. Monitoring: --endpoint <path> (JSON). e.g., CDMCP --endpoint chrome/status",
            add_help=False,
        )
        sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

        sub.add_parser("status", help="Check Chrome CDP availability and managed tabs")
        sub.add_parser("state", help="Print comprehensive MCP state (sessions, tabs, window)")
        sub.add_parser("tutorial", help="Run interactive setup tutorial")

        p_nav = sub.add_parser("navigate", help="Open URL in a managed CDMCP tab")
        p_nav.add_argument("url", help="URL to navigate to")
        p_nav.add_argument("--tab-id", default="", help="Navigate an existing tab (by ID) instead of creating a new one")

        p_activate = sub.add_parser("activate", help="Bring a tab to the foreground by ID")
        p_activate.add_argument("tab_id", help="Target ID of the tab to activate")

        sub.add_parser("minimize", help="Minimize the session Chrome window")
        sub.add_parser("restore", help="Restore the session Chrome window")
        sub.add_parser("ensure-window", help="Verify session window is alive; reboot if needed")

        p_screenshot = sub.add_parser("screenshot", help="Capture a screenshot of a tab")
        p_screenshot.add_argument("--tab-id", default="", help="Tab ID (default: last session tab)")
        p_screenshot.add_argument("--output", default="", help="Output file path (default: data/report/last_screenshot.png)")

        p_fe = sub.add_parser("focus-element", help="Focus a DOM element in a tab by CSS selector")
        p_fe.add_argument("pattern", help="URL pattern to match the tab")
        p_fe.add_argument("selector", help="CSS selector for the element to focus")

        p_scroll = sub.add_parser("scroll", help="Scroll in a tab (horizontal/vertical)")
        p_scroll.add_argument("pattern", help="URL pattern to match the tab")
        p_scroll.add_argument("--dx", type=int, default=0, help="Horizontal scroll pixels (positive=right)")
        p_scroll.add_argument("--dy", type=int, default=0, help="Vertical scroll pixels (positive=down)")

        p_click = sub.add_parser("click", help="Click an element in a tab (by selector or focused element)")
        p_click.add_argument("pattern", help="URL pattern to match the tab")
        p_click.add_argument("selector", nargs="?", default="", help="CSS selector (omit to click focused element)")

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

        p_session = sub.add_parser("session", help="Manage CDMCP sessions")
        p_session.add_argument("action", choices=["create", "list", "close"],
                               help="Session action")
        p_session.add_argument("name", nargs="?", default="default",
                               help="Session name")
        p_session.add_argument("--timeout", type=int, default=None,
                               help="Session timeout in seconds (default 86400)")

        p_limit = sub.add_parser("session-limit",
                                 help="Set max concurrent sessions and overflow policy")
        p_limit.add_argument("--max", type=int, default=None, dest="max_sessions",
                             help="Max concurrent sessions (0 = unlimited)")
        p_limit.add_argument("--policy", choices=["fail", "kill_oldest_boot",
                                                   "kill_oldest_activity"],
                             default=None,
                             help="Overflow policy")

        p_boot = sub.add_parser("boot", help="Boot a session (opens welcome page in new window)")
        p_boot.add_argument("name", nargs="?", default="default",
                            help="Session name to boot")
        p_boot.add_argument("--url", default=None,
                            help="URL to open (default: welcome page)")

        sub.add_parser("chrome-clean", help="Kill all Chrome processes and remove lock files for a clean restart")

        p_tabs = sub.add_parser("session-tabs", help="List tabs in a session")
        p_tabs.add_argument("name", nargs="?", default="default",
                            help="Session name")

        p_demo = sub.add_parser("demo", help="Run interactive demo on Chat app")
        p_demo.add_argument("--delay", type=float, default=1.2,
                            help="Delay between steps (seconds)")
        p_demo.add_argument("--single", action="store_true",
                            help="Run single interaction only (default is continuous)")

        p_scan = sub.add_parser("scan", help="Scan a page for all interactive elements")
        p_scan.add_argument("pattern", help="URL pattern to match the tab")
        p_scan.add_argument("--shadow", action="store_true",
                            help="Also scan Shadow DOM hosts")
        p_scan.add_argument("--scroll", action="store_true",
                            help="Scan scrollable regions")
        p_scan.add_argument("--menus", action="store_true",
                            help="Click menus and scan items")
        p_scan.add_argument("--apis", action="store_true",
                            help="Discover JavaScript APIs")
        p_scan.add_argument("--full", action="store_true",
                            help="Enable all scan modes (shadow, scroll, menus, apis)")
        p_scan.add_argument("--output", default="",
                            help="Save JSON output to file path")
        p_scan.add_argument("--screenshot", default="",
                            help="Save a screenshot to file path")

        sub.add_parser("auth", help="Check Google account login state")
        sub.add_parser("login", help="Initiate Google account login flow")
        sub.add_parser("logout", help="Initiate Google account logout flow")

        p_ma = sub.add_parser("my-account", help="Google My Account operations")
        ma_sub = p_ma.add_subparsers(dest="ma_action")
        ma_sub.add_parser("profile", help="Show personal profile info")
        ma_sub.add_parser("security", help="Show security overview")
        ma_sub.add_parser("activity", help="Show recent security activity")
        ma_sub.add_parser("apps", help="List connected third-party apps")
        ma_sub.add_parser("devices", help="List signed-in devices")
        ma_sub.add_parser("storage", help="Show account storage usage")
        ma_nav = ma_sub.add_parser("navigate", help="Navigate to a sub-page")
        ma_nav.add_argument("page", choices=["home", "personal-info", "security",
                            "data-privacy", "people-sharing", "payments"],
                            help="Sub-page name")

        if self.handle_command_line(parser):
            return

        args = parser.parse_args()
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        YELLOW = get_color("YELLOW")
        BLUE = get_color("BLUE")
        DIM = get_color("DIM")
        RESET = get_color("RESET")

        api = _load_api()

        if args.command == "tutorial":
            try:
                import importlib.util
                tut_path = _TOOL_DIR / "logic" / "tutorial" / "setup_guide.py"
                spec = importlib.util.spec_from_file_location("cdmcp_tutorial", str(tut_path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.run_setup_tutorial()
            except Exception as e:
                print(f"  {BOLD}{RED}Failed{RESET} to run tutorial: {e}")
            return

        elif args.command == "status":
            r = api.status()
            avail = r.get("chrome_available", False)
            print(f"  Chrome CDP: {BOLD}{GREEN if avail else RED}{'Available' if avail else 'Not available'}{RESET}")
            print(f"  Managed tabs: {r.get('managed_tabs', 0)}")
            print(f"  Sessions: {r.get('sessions', 0)}")
            if r.get("focused_tab"):
                print(f"  Focused: {r['focused_tab']}")
            if r.get("locked_tab"):
                print(f"  Locked: {r['locked_tab']}")
            cfg = r.get("config", {})
            print(f"  OAuth allowed: {cfg.get('allow_oauth', True)}")
            print(f"  Logging: {cfg.get('log_interactions', True)}")

        elif args.command == "state":
            sm = api._get_session_mgr()
            sessions_info = []
            active_name = None
            if sm:
                for name, sess in sm._sessions.items():
                    info = {"name": name, "window_id": sess.window_id}
                    if sess.lifetime_tab_id:
                        info["lifetime_tab"] = sess.lifetime_tab_id[:12]
                    tabs = {}
                    for label, tinfo in (sess._tabs or {}).items():
                        tabs[label] = tinfo.get("id", "?")[:12] if isinstance(tinfo, dict) else str(tinfo)[:12]
                    info["tabs"] = tabs
                    sessions_info.append(info)
                active = sm.get_any_active_session()
                if active:
                    active_name = getattr(active, "_name", None) or getattr(active, "name", None)
            print(f"\n{BOLD}CDMCP State{RESET}")
            print(f"  Sessions: {len(sessions_info)}")
            if active_name:
                print(f"  Active: {BOLD}{active_name}{RESET}")
            for s in sessions_info:
                print(f"\n  [{BOLD}{s['name']}{RESET}]  window={s.get('window_id', '?')}")
                if s.get("lifetime_tab"):
                    print(f"    lifetime_tab: {s['lifetime_tab']}")
                for label, tid in s.get("tabs", {}).items():
                    print(f"    tab/{label}: {tid}")
            all_tabs = api.list_tabs()
            page_tabs = [t for t in all_tabs if t.get("type") == "page"]
            print(f"\n  Chrome tabs (page): {len(page_tabs)}")
            for t in page_tabs[:10]:
                url_short = (t.get("url") or "")[:60]
                print(f"    {t['id'][:12]}  {url_short}")
            win = api.ensure_session_window()
            print(f"\n  Window status: {BOLD}{GREEN if win['ok'] else RED}{win.get('action', win.get('error', '?'))}{RESET}")
            print()

        elif args.command == "navigate":
            if getattr(args, "tab_id", ""):
                r = api.navigate_tab(args.tab_id, args.url)
                if r.get("ok"):
                    print(f"  {BOLD}{GREEN}Navigated{RESET} tab {args.tab_id[:12]} to {args.url}.")
                    if r.get("title"):
                        print(f"  Title: {r['title']}")
                else:
                    print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")
            else:
                r = api.navigate(args.url)
                if r.get("ok"):
                    print(f"  {BOLD}{GREEN}Navigated{RESET} to {args.url} ({r.get('action', 'unknown')}).")
                else:
                    print(f"  {BOLD}{RED}Failed{RESET} to navigate: {r.get('error', 'unknown')}")

        elif args.command == "activate":
            r = api.activate_tab(args.tab_id)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Activated{RESET} tab {args.tab_id[:12]}.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "minimize":
            r = api.minimize_window()
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Minimized{RESET} window {r.get('windowId')}.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "restore":
            r = api.restore_window()
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Restored{RESET} window {r.get('windowId')}.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "ensure-window":
            r = api.ensure_session_window()
            if r.get("ok"):
                action = r.get("action", "unknown")
                print(f"  {BOLD}{GREEN}Window {action}{RESET}.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "screenshot":
            r = api.screenshot_tab(
                tab_id=getattr(args, "tab_id", "") or None,
                output=getattr(args, "output", ""),
            )
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Saved{RESET} screenshot to {r['path']}.")
                print(f"  Tab: {r.get('title', '?')[:50]}  Size: {r.get('size', 0)} bytes.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "focus-element":
            r = api.focus_element(args.pattern, args.selector)
            if r.get("ok"):
                tag = r.get("tag", "?")
                text = r.get("text", "")[:40]
                print(f"  {BOLD}{GREEN}Focused{RESET} <{tag}> at ({r.get('x',0)}, {r.get('y',0)}).")
                if text:
                    print(f"  Text: {text}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "scroll":
            r = api.scroll_tab(args.pattern, dx=args.dx, dy=args.dy)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Scrolled{RESET} dx={r.get('deltaX',0)} dy={r.get('deltaY',0)}.")
                print(f"  Position: scrollX={r.get('scrollX',0)} scrollY={r.get('scrollY',0)}.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "click":
            r = api.click_element(args.pattern, selector=args.selector)
            if r.get("ok"):
                c = r.get("clicked", {})
                print(f"  {BOLD}{GREEN}Clicked{RESET} <{c.get('tag','?')}> at ({c.get('x',0)}, {c.get('y',0)}).")
                if c.get("text"):
                    print(f"  Text: {c['text'][:50]}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "focus":
            r = api.focus_tab(args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Focused{RESET} on tab: {r.get('url', args.pattern)}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "lock":
            r = api.lock_tab(args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{BLUE}Locked{RESET} tab: {args.pattern}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "unlock":
            r = api.unlock_tab(args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Unlocked{RESET} tab: {args.pattern}")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "highlight":
            r = api.highlight_element(args.pattern, args.selector, label=args.label)
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
            r = api.clear_highlight(args.pattern)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Cleared{RESET} highlight.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "cleanup":
            r = api.cleanup_tab(args.pattern)
            if r.get("ok"):
                removed = r.get("removed", [])
                print(f"  {BOLD}{GREEN}Cleaned up{RESET} {len(removed)} overlays.")
            else:
                print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', 'unknown')}")

        elif args.command == "config":
            if args.reset:
                api.reset_config()
                print(f"  {BOLD}{GREEN}Reset{RESET} configuration to defaults.")
            elif args.set:
                key, val = args.set
                try:
                    parsed = json.loads(val)
                except json.JSONDecodeError:
                    parsed = val
                api.set_config_value(key, parsed)
                print(f"  {BOLD}{GREEN}Set{RESET} {key} = {json.dumps(parsed)}")
            else:
                print(f"  {BOLD}CDMCP Configuration{RESET}:")
                print(api.show_config_str())

        elif args.command == "tabs":
            tabs = api.list_managed()
            if tabs:
                for i, t in enumerate(tabs):
                    focused = " [FOCUSED]" if t.get("_cdmcp_focused") else ""
                    locked = " [LOCKED]" if t.get("_cdmcp_locked") else ""
                    print(f"  [{i+1}] {t.get('title', '?')[:50]:<50} {focused}{locked}")
                    print(f"      {t.get('url', '?')}")
            else:
                print(f"  {YELLOW}No managed tabs.{RESET}")

        elif args.command == "session":
            if args.action == "create":
                try:
                    s = api.create_session(args.name, timeout_sec=args.timeout)
                    print(f"  {BOLD}{GREEN}Created{RESET} session '{args.name}' (id: {s.session_id}).")
                except Exception as e:
                    if "Session limit reached" in str(e):
                        print(f"  {BOLD}{RED}Session limit reached{RESET}: {e}")
                        if hasattr(e, "active_sessions"):
                            for info in e.active_sessions:
                                print(f"    - {info['name']} ({info['session_id'][:8]}) idle={info['idle_sec']}s")
                    else:
                        raise
            elif args.action == "list":
                sessions = api.list_sessions()
                if sessions:
                    for s in sessions:
                        exp = " [EXPIRED]" if s.get("expired") else ""
                        boot = " [BOOTED]" if s.get("booted") else ""
                        tabs = s.get("tabs", [])
                        alive_ct = sum(1 for t in tabs if t.get("alive"))
                        tab_info = f" tabs={alive_ct}/{len(tabs)}" if tabs else ""
                        print(f"  {s['name']} ({s['session_id'][:8]}) age={s['age_sec']}s{boot}{exp}{tab_info}")
                else:
                    print(f"  {YELLOW}No active sessions.{RESET}")
            elif args.action == "close":
                if api.close_session(args.name):
                    print(f"  {BOLD}{GREEN}Closed{RESET} session '{args.name}'.")
                else:
                    print(f"  {BOLD}{RED}Not found{RESET}: session '{args.name}'")

        elif args.command == "session-tabs":
            sessions = api.list_sessions()
            found = None
            for s in sessions:
                if s["name"] == args.name:
                    found = s
                    break
            if not found:
                print(f"  {BOLD}{RED}Not found{RESET}: session '{args.name}'")
            elif not found.get("tabs"):
                print(f"  {YELLOW}No tabs in session '{args.name}'.{RESET}")
            else:
                print(f"  Session: {found['name']} ({found['session_id'][:8]})")
                for i, t in enumerate(found["tabs"]):
                    alive = f"{GREEN}ALIVE{RESET}" if t.get("alive") else f"{RED}GONE{RESET}"
                    label = t.get("label", "?")
                    print(f"    [{i}] {label:<20} {alive}  id={t.get('id', '?')[:16]}")
                    print(f"        {t.get('url', '?')[:80]}")

        elif args.command == "session-limit":
            if args.max_sessions is not None or args.policy is not None:
                cfg = api.get_max_sessions_config()
                new_max = args.max_sessions if args.max_sessions is not None else cfg["max_sessions"]
                new_pol = args.policy if args.policy is not None else cfg["overflow_policy"]
                api.set_max_sessions(new_max, new_pol)
                print(f"  {BOLD}{GREEN}Updated{RESET} session limit: max={new_max}, policy={new_pol}")
            else:
                cfg = api.get_max_sessions_config()
                print(f"  Max sessions: {cfg['max_sessions'] or 'unlimited'}")
                print(f"  Overflow policy: {cfg['overflow_policy']}")
                print(f"  Active sessions: {cfg['active_count']}")

        elif args.command == "boot":
            try:
                r = api.boot_session(args.name, url=args.url)
                if r.get("ok"):
                    sid = r.get("session_id_short", r.get("session_id", "?")[:8])
                    print(f"  {BOLD}{GREEN}Booted{RESET} session '{args.name}' [{sid}].")
                    print(f"  Window: {r.get('windowId', '?')}")
                else:
                    print(f"  {BOLD}{RED}Failed{RESET} to boot: {r.get('error', '?')}")
            except Exception as e:
                if "Session limit reached" in str(e):
                    print(f"  {BOLD}{RED}Session limit reached{RESET}: {e}")
                    if hasattr(e, "active_sessions"):
                        for info in e.active_sessions:
                            print(f"    - {info['name']} ({info['session_id'][:8]}) idle={info['idle_sec']}s")
                else:
                    raise

        elif args.command == "chrome-clean":
            from logic.utils.platform import cleanup_chrome
            result = cleanup_chrome()
            if result.get("killed"):
                print(f"  {BOLD}{GREEN}Chrome processes terminated.{RESET}")
            else:
                print(f"  {DIM}No Chrome processes found.{RESET}")
            if result.get("locks_removed"):
                print(f"  {DIM}Removed {result['locks_removed']} lock file(s).{RESET}")
            for err in result.get("errors", []):
                print(f"  {BOLD}{RED}Error:{RESET} {err}")
            print(f"  {BOLD}Clean state ready.{RESET} Use 'CDMCP boot' to restart Chrome with CDP.")

        elif args.command == "scan":
            r = _run_scan(api, args, BOLD, GREEN, RED, BLUE, RESET)
            if r:
                print(f"  {BOLD}{GREEN}Scan complete.{RESET}")
            else:
                print(f"  {BOLD}{RED}Scan failed.{RESET}")

        elif args.command == "demo":
            r = api.run_demo(delay=args.delay, continuous=not args.single)
            if r.get("ok"):
                print(f"\n  {BOLD}{GREEN}Demo completed successfully{RESET}.")
            else:
                print(f"\n  {BOLD}{RED}Demo had failures{RESET}: {r.get('error', 'check steps')}")

        elif args.command == "auth":
            r = api.google_auth_status()
            signed_in = r.get("signed_in", False)
            if signed_in:
                email = r.get("email")
                name = r.get("display_name")
                if email and name:
                    label = f"{name} ({email})"
                elif email:
                    label = email
                else:
                    label = "Signed in (email not available)"
                print(f"  {BOLD}Google Account:{RESET} {GREEN}{label}{RESET}")
            else:
                print(f"  {BOLD}Google Account:{RESET} {YELLOW}Not signed in{RESET}")
            checked = r.get("last_checked", 0)
            if checked:
                import datetime
                ts = datetime.datetime.fromtimestamp(checked).strftime("%H:%M:%S")
                print(f"  Last checked: {ts}")

        elif args.command == "login":
            _validate_session_tabs("pre-login")
            auth_result = api.google_auth_status()
            if auth_result.get("signed_in"):
                print(f"  {BOLD}Already signed in.{RESET}")
            else:
                r = api.google_auth_login(start_tracker=False)
                status = r.get("status", "unknown")
                if status in ("opened", "login_in_progress"):
                    tab_id = r.get("tab_id")
                    _unlock_tab_for_user(tab_id)
                    print(f"  {BOLD}Login tab opened (unlocked for sign-in).{RESET}")
                    _poll_login(tab_id, timeout=300)
                elif status == "already_signed_in":
                    print(f"  {BOLD}Already signed in.{RESET}")
                else:
                    print(f"  {BOLD}{RED}Failed to open login tab:{RESET} "
                          f"{r.get('error', 'unknown')}")
            _validate_session_tabs("post-login")

        elif args.command == "logout":
            _validate_session_tabs("pre-logout")
            r = api.google_auth_logout()
            status = r.get("status", "unknown")
            if status == "opened":
                tab_id = r.get("tab_id")
                print(f"  {BOLD}Logout tab opened.{RESET} Completing sign-out...")
                _poll_logout(tab_id, timeout=60)
            else:
                print(f"  {BOLD}{RED}Failed to open logout tab:{RESET} "
                      f"{r.get('error', 'unknown')}")
            _validate_session_tabs("post-logout")

        # save-auth / restore-auth removed: cookie restore doesn't survive
        # server-side session revocation after full Google logout.
        # Interface functions (_save_auth_cookies, _restore_auth_cookies) retained
        # for potential future re-implementation.

        elif args.command == "my-account":
            _run_my_account(api, args, BOLD, GREEN, RED, YELLOW, BLUE, RESET)

        else:
            parser.print_help()


def _run_my_account(api, args, BOLD, GREEN, RED, YELLOW, BLUE, RESET):
    """Handle --mcp-my-account sub-commands."""
    ma_mod = _load_myaccount_mod()
    sm = api._get_session_mgr()
    session = sm.get_any_active_session() if sm else None

    auth_check = ma_mod.check_login_required()
    if not auth_check.get("ok"):
        print(f"  {BOLD}{RED}Not signed in.{RESET} Run CDMCP --mcp-login first.")
        return
    if not session:
        print(f"  {BOLD}{RED}No active session.{RESET} Run CDMCP --mcp-session create first.")
        return

    action = args.ma_action
    if not action:
        print(f"  {BOLD}Google My Account{RESET} ({auth_check.get('email', '?')})")
        print(f"  Sub-commands: profile, security, activity, apps, devices, storage, navigate")
        return

    if action == "profile":
        print(f"  {BOLD}Fetching profile...{RESET}")
        r = ma_mod.get_profile(session)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Profile:{RESET}")
            for key in ("name", "gender", "birthday", "language", "phone"):
                if r.get(key):
                    print(f"    {key.capitalize()}: {r[key]}")
            if r.get("emails"):
                print(f"    Emails: {', '.join(r['emails'])}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "security":
        print(f"  {BOLD}Fetching security overview...{RESET}")
        r = ma_mod.get_security_overview(session)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Security:{RESET}")
            if r.get("two_factor"):
                color = GREEN if r["two_factor"] == "on" else YELLOW
                print(f"    2FA: {color}{r['two_factor']}{RESET}")
            if r.get("password_last_changed"):
                print(f"    Password changed: {r['password_last_changed']}")
            if r.get("active_sessions"):
                print(f"    Active sessions: {r['active_sessions']}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "activity":
        print(f"  {BOLD}Fetching recent activity...{RESET}")
        r = ma_mod.get_recent_activity(session)
        if r.get("ok"):
            activities = r.get("activities", [])
            if activities:
                print(f"  {BOLD}{GREEN}Recent activity:{RESET}")
                for a in activities:
                    print(f"    - {a}")
            else:
                print(f"  {BOLD}No recent activity found.{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "apps":
        print(f"  {BOLD}Fetching connected apps...{RESET}")
        r = ma_mod.get_connected_apps(session)
        if r.get("ok"):
            apps = r.get("apps", [])
            if apps:
                print(f"  {BOLD}{GREEN}Connected apps:{RESET}")
                for a in apps:
                    print(f"    - {a}")
            else:
                print(f"  {BOLD}No connected third-party apps.{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "devices":
        print(f"  {BOLD}Fetching devices...{RESET}")
        r = ma_mod.get_devices(session)
        if r.get("ok"):
            devices = r.get("devices", [])
            if devices:
                print(f"  {BOLD}{GREEN}Devices:{RESET}")
                for d in devices:
                    print(f"    - {d}")
            else:
                print(f"  {BOLD}No devices found.{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "storage":
        print(f"  {BOLD}Fetching storage usage...{RESET}")
        r = ma_mod.get_storage_usage(session)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Storage:{RESET}")
            if r.get("used") and r.get("total"):
                print(f"    Used: {r['used']} / {r['total']}")
            else:
                print(f"    Could not parse storage details.")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    elif action == "navigate":
        page = args.page
        print(f"  {BOLD}Navigating to {page}...{RESET}")
        r = ma_mod.navigate_page(session, page)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Navigated{RESET} to {r.get('title', page)}.")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', '?')}")

    else:
        print(f"  {BOLD}{YELLOW}Unknown action:{RESET} {action}")


def _load_myaccount_mod():
    """Lazy-load the myaccount module."""
    import importlib.util
    path = _TOOL_DIR / "logic" / "cdp" / "google_myaccount.py"
    spec = importlib.util.spec_from_file_location("cdmcp_myaccount", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_scan(api, args, BOLD, GREEN, RED, BLUE, RESET):
    """Scan a tab for all interactive elements."""
    import time
    from interface.chrome import (
        CDPSession, capture_screenshot, find_tab,
    )

    pattern = args.pattern
    do_shadow = args.shadow or args.full
    do_scroll = args.scroll or args.full
    do_menus = args.menus or args.full
    do_apis = args.apis or args.full
    output_path = args.output
    screenshot_path = args.screenshot

    tab = find_tab(pattern)
    if not tab:
        print(f"  {BOLD}{RED}No tab matching '{pattern}'.{RESET}")
        return False

    cdp = CDPSession(tab["webSocketDebuggerUrl"])
    result = {"url": tab.get("url", ""), "title": tab.get("title", ""),
              "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    # Core element scan
    print(f"  {BOLD}{BLUE}Scanning{RESET} interactive elements...")
    scan_js = '''
    (function(){
        var selectors = 'button:not([hidden]), [role=button]:not([hidden]), '
            + '[role=tab]:not([hidden]), [role=menuitem], '
            + 'input:not([hidden]), textarea:not([hidden]), select:not([hidden]), '
            + 'a[href]:not([hidden]), [contenteditable]:not([hidden]), '
            + '[role=checkbox], [role=radio], [role=switch], '
            + '[role=slider], [role=combobox], [role=listbox], '
            + '[role=link], [role=option], [tabindex]:not([tabindex="-1"])';
        var all = document.querySelectorAll(selectors);
        var out = [];
        for(var i=0; i<all.length; i++){
            var el = all[i];
            var rect = el.getBoundingClientRect();
            if(rect.width <= 0 || rect.height <= 0) continue;
            if(rect.y < -50 || rect.x < -50) continue;
            out.push({
                tag: el.tagName, id: el.id||'',
                text: (el.textContent||'').trim().substring(0, 80),
                title: el.getAttribute('title')||'',
                aria: el.getAttribute('aria-label')||'',
                role: el.getAttribute('role')||'',
                type: el.getAttribute('type')||'',
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
                cls: (el.className||'').toString().substring(0, 80),
                href: (el.getAttribute('href')||'').substring(0, 120)
            });
        }
        out.sort(function(a,b){ return a.y === b.y ? a.x - b.x : a.y - b.y; });
        return JSON.stringify(out);
    })()
    '''
    raw = cdp.evaluate(scan_js)
    elements = json.loads(raw) if raw else []
    result["elements"] = elements
    result["element_count"] = len(elements)
    print(f"    Found {BOLD}{len(elements)}{RESET} interactive elements.")

    # Shadow DOM scan
    if do_shadow:
        print(f"  {BOLD}{BLUE}Scanning{RESET} Shadow DOM...")
        shadow_js = '''
        (function(){
            var all = document.querySelectorAll('*');
            var out = [];
            for(var i=0; i<all.length; i++){
                var el = all[i];
                if(!el.shadowRoot) continue;
                var rect = el.getBoundingClientRect();
                if(rect.width <= 0 || rect.height <= 0) continue;
                var children = el.shadowRoot.querySelectorAll(
                    'button, [role=button], input, a, [role=tab], select, textarea'
                );
                var childData = [];
                for(var j=0; j<children.length && j<20; j++){
                    var c = children[j];
                    var cr = c.getBoundingClientRect();
                    if(cr.width <= 0) continue;
                    childData.push({
                        tag: c.tagName, id: c.id||'',
                        text: (c.textContent||'').trim().substring(0, 50),
                        aria: c.getAttribute('aria-label')||'',
                        x: Math.round(cr.x), y: Math.round(cr.y),
                        w: Math.round(cr.width), h: Math.round(cr.height)
                    });
                }
                if(childData.length > 0)
                    out.push({
                        host: el.tagName, hostId: el.id||'',
                        hostCls: (el.className||'').toString().substring(0, 60),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        children: childData
                    });
            }
            return JSON.stringify(out);
        })()
        '''
        raw = cdp.evaluate(shadow_js)
        shadow = json.loads(raw) if raw else []
        result["shadow_dom"] = shadow
        total_shadow_children = sum(len(s.get("children", [])) for s in shadow)
        print(f"    Found {BOLD}{len(shadow)}{RESET} shadow hosts with {total_shadow_children} children.")

    # Scrollable regions
    if do_scroll:
        print(f"  {BOLD}{BLUE}Scanning{RESET} scrollable regions...")
        scroll_js = '''
        (function(){
            var all = document.querySelectorAll('*');
            var out = [];
            for(var i=0; i<all.length; i++){
                var el = all[i];
                if((el.scrollHeight > el.clientHeight + 20) || (el.scrollWidth > el.clientWidth + 20)){
                    var r = el.getBoundingClientRect();
                    if(r.width < 50 || r.height < 50) continue;
                    out.push({
                        tag: el.tagName, id: el.id||'',
                        cls: (el.className||'').toString().substring(0, 60),
                        scrollH: el.scrollHeight, clientH: el.clientHeight,
                        scrollW: el.scrollWidth, clientW: el.clientWidth,
                        x: Math.round(r.x), y: Math.round(r.y),
                        w: Math.round(r.width), h: Math.round(r.height)
                    });
                }
            }
            return JSON.stringify(out);
        })()
        '''
        raw = cdp.evaluate(scroll_js)
        scrollable = json.loads(raw) if raw else []
        result["scrollable"] = scrollable
        print(f"    Found {BOLD}{len(scrollable)}{RESET} scrollable containers.")

    # Menu scanning
    if do_menus:
        print(f"  {BOLD}{BLUE}Scanning{RESET} menus...")
        menu_scan_js = '''
        (function(){
            var triggers = document.querySelectorAll(
                '[role=menubar] > *, [aria-haspopup=true], [aria-expanded]'
            );
            var out = [];
            for(var i=0; i<triggers.length; i++){
                var t = triggers[i];
                var r = t.getBoundingClientRect();
                if(r.width <= 0) continue;
                out.push({
                    tag: t.tagName, id: t.id||'',
                    text: (t.textContent||'').trim().substring(0, 40),
                    aria: t.getAttribute('aria-label')||'',
                    x: Math.round(r.x), y: Math.round(r.y),
                    w: Math.round(r.width), h: Math.round(r.height)
                });
            }
            return JSON.stringify(out);
        })()
        '''
        raw = cdp.evaluate(menu_scan_js)
        menu_triggers = json.loads(raw) if raw else []
        result["menu_triggers"] = menu_triggers
        print(f"    Found {BOLD}{len(menu_triggers)}{RESET} menu triggers.")

    # JavaScript API discovery
    if do_apis:
        print(f"  {BOLD}{BLUE}Scanning{RESET} JavaScript APIs...")
        api_js = '''
        (function(){
            var candidates = [
                'colab.global.notebook', 'colab.global',
                'ytInitialData', 'ytInitialPlayerResponse',
                'yt.config_', 'gapi.client', 'google.colab',
                'window.__INITIAL_STATE__', 'window.__NEXT_DATA__',
                'window.__NUXT__', 'window._sharedData'
            ];
            var result = {};
            for(var i=0; i<candidates.length; i++){
                try {
                    var obj = eval(candidates[i]);
                    if(obj){
                        var t = typeof obj;
                        if(t === 'object'){
                            var keys = Object.keys(obj).slice(0, 50);
                            var methods = keys.filter(function(k){ return typeof obj[k] === 'function'; });
                            result[candidates[i]] = {
                                type: Array.isArray(obj) ? 'array' : 'object',
                                key_count: Object.keys(obj).length,
                                method_count: methods.length,
                                sample_keys: keys.slice(0, 20),
                                sample_methods: methods.slice(0, 20)
                            };
                        } else {
                            result[candidates[i]] = {type: t, value: String(obj).substring(0, 100)};
                        }
                    }
                } catch(e) {}
            }
            return JSON.stringify(result);
        })()
        '''
        raw = cdp.evaluate(api_js)
        apis = json.loads(raw) if raw else {}
        result["js_apis"] = apis
        print(f"    Found {BOLD}{len(apis)}{RESET} JavaScript APIs.")
        for name, info in apis.items():
            if isinstance(info, dict) and "method_count" in info:
                print(f"      {name}: {info['key_count']} keys, {info['method_count']} methods")

    # Viewport info
    vp_js = 'JSON.stringify({w: window.innerWidth, h: window.innerHeight})'
    vp_raw = cdp.evaluate(vp_js)
    result["viewport"] = json.loads(vp_raw) if vp_raw else {}

    # Screenshot
    if screenshot_path:
        img = capture_screenshot(cdp)
        if img:
            with open(screenshot_path, "wb") as f:
                f.write(img)
            print(f"  {BOLD}{GREEN}Screenshot saved:{RESET} {screenshot_path}")

    # Print summary
    print(f"\n  {BOLD}Summary:{RESET}")
    print(f"    Elements: {result['element_count']}")
    if do_shadow:
        print(f"    Shadow DOM hosts: {len(result.get('shadow_dom', []))}")
    if do_scroll:
        print(f"    Scrollable: {len(result.get('scrollable', []))}")
    if do_menus:
        print(f"    Menu triggers: {len(result.get('menu_triggers', []))}")
    if do_apis:
        print(f"    JS APIs: {len(result.get('js_apis', {}))}")

    # Print top elements by region
    if elements:
        print(f"\n  {BOLD}Top elements (sorted by position):{RESET}")
        for e in elements[:30]:
            eid = e.get("id") or e.get("aria") or e.get("text", "")[:25]
            tag = e.get("tag", "?")
            role = e.get("role", "")
            x, y = e.get("x", 0), e.get("y", 0)
            print(f"    [{x:4d},{y:4d}] {tag:15s} role={role:10s} {eid}")

    # Save output
    if output_path:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  {BOLD}{GREEN}JSON saved:{RESET} {output_path}")
    else:
        default_path = str(Path(__file__).resolve().parent / "data" / "report" / "last_scan.json")
        Path(default_path).parent.mkdir(parents=True, exist_ok=True)
        with open(default_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  {BOLD}JSON saved:{RESET} {default_path}")

    cdp.close()
    return True


def _load_auth_mod():
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parent / "logic" / "cdp" / "google_auth.py"
    spec = importlib.util.spec_from_file_location("cdmcp_google_auth", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_AUTH_COOKIE_FILE = Path(__file__).resolve().parent / "data" / "config" / "saved_auth_cookies.json"


def _save_auth_cookies():
    """Save all Google cookies via Network.getAllCookies."""
    import json
    from interface.chrome import CDPSession, list_tabs, CDP_PORT
    tabs = list_tabs(CDP_PORT)
    for t in tabs:
        ws = t.get("webSocketDebuggerUrl")
        if ws and t.get("type") == "page":
            try:
                cdp = CDPSession(ws, timeout=5)
                cdp.send_and_recv("Network.enable", {})
                resp = cdp.send_and_recv("Network.getAllCookies", {})
                cookies = (resp or {}).get("result", {}).get("cookies", [])
                cdp.close()
                google_cookies = [c for c in cookies if
                                  "google" in c.get("domain", "").lower()]
                _AUTH_COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(_AUTH_COOKIE_FILE, "w") as f:
                    json.dump(google_cookies, f, indent=2)
                return {"ok": True, "count": len(google_cookies)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "No accessible tab"}


def _restore_auth_cookies():
    """Restore saved Google cookies via Network.setCookie."""
    import json
    from interface.chrome import CDPSession, list_tabs, CDP_PORT
    if not _AUTH_COOKIE_FILE.exists():
        return {"ok": False, "error": "No saved cookies. Run save-auth first."}
    with open(_AUTH_COOKIE_FILE) as f:
        cookies = json.load(f)
    tabs = list_tabs(CDP_PORT)
    for t in tabs:
        ws = t.get("webSocketDebuggerUrl")
        if ws and t.get("type") == "page":
            try:
                cdp = CDPSession(ws, timeout=5)
                cdp.send_and_recv("Network.enable", {})
                ok_count = 0
                for c in cookies:
                    params = {
                        "name": c["name"], "value": c["value"],
                        "domain": c.get("domain", ""),
                        "path": c.get("path", "/"),
                        "secure": c.get("secure", False),
                        "httpOnly": c.get("httpOnly", False),
                        "sameSite": c.get("sameSite", "Lax"),
                    }
                    if c.get("expires", -1) > 0:
                        params["expires"] = c["expires"]
                    resp = cdp.send_and_recv("Network.setCookie", params)
                    if (resp or {}).get("result", {}).get("success"):
                        ok_count += 1
                auth_mod = _load_auth_mod()
                state = auth_mod.check_auth_cookies(cdp, verify=False)
                cdp.close()
                return {"ok": True, "restored": ok_count,
                        "signed_in": state.get("signed_in", False)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "No accessible tab"}


def _unlock_tab_for_user(tab_id, tip_text="Please sign in to your Google account below"):
    """Remove lock, inject tip banner, focus the tab, and alert with a bell."""
    from interface.chrome import CDPSession, list_tabs, CDP_PORT
    tabs = list_tabs(CDP_PORT)
    for t in tabs:
        if t.get("id") == tab_id:
            ws = t.get("webSocketDebuggerUrl")
            if ws:
                try:
                    overlay_path = Path(__file__).resolve().parent / "logic" / "cdp" / "overlay.py"
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("cdmcp_ov_unlock", overlay_path)
                    ov = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(ov)
                    cdp = CDPSession(ws, timeout=5)
                    ov.remove_lock(cdp)
                    ov.inject_tip(cdp, tip_text, bg_color="#1a73e8")
                    ov.inject_badge(cdp, text="CDMCP Auth", color="#34a853")
                    cdp.close()
                except Exception:
                    pass
            _activate_tab(tab_id, CDP_PORT)
            _play_alert_bell()
            break


def _activate_tab(tab_id, port):
    """Bring a tab to the foreground via CDP Target.activateTarget."""
    import urllib.request
    try:
        url = f"http://localhost:{port}/json/activate/{tab_id}"
        urllib.request.urlopen(url, timeout=3)
    except Exception:
        pass


def _play_alert_bell():
    """Play bell.mp3 to alert the user (non-blocking). Falls back to system sound."""
    import subprocess, sys as _sys
    from pathlib import Path as _Path
    bell_mp3 = _Path(__file__).resolve().parent.parent.parent / "logic" / "asset" / "audio" / "bell.mp3"
    if bell_mp3.exists():
        subprocess.Popen(["afplay", str(bell_mp3)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif _sys.platform == "darwin":
        subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _validate_session_tabs(context=""):
    """TEMPORARY debug validator for session tab state consistency.

    Added to diagnose session recovery issues (missing welcome/demo tabs
    after Chrome window loss). Expected to be commented out once session
    recovery is stable and verified.

    Verifies:
      1. Active session exists with a lifetime (welcome) tab that's alive
      2. Demo tab is registered and alive

    Prints detailed diagnostics on any violation. Returns True if valid.
    """
    from interface.config import get_color
    from interface.chrome import list_tabs, CDP_PORT
    BOLD, RED, YELLOW, GREEN, RESET = (
        get_color("BOLD"), get_color("RED"), get_color("YELLOW"),
        get_color("GREEN"), get_color("RESET"))

    api = _load_api()
    sm = api._get_session_mgr()
    if not sm:
        print(f"  {BOLD}{RED}[VALIDATE]{RESET} No session manager loaded.")
        return False

    session = sm.get_any_active_session()
    if not session:
        print(f"  {BOLD}{YELLOW}[VALIDATE]{RESET} No active session (context: {context}).")
        return True

    label = f"[VALIDATE:{context}]" if context else "[VALIDATE]"
    all_tabs = list_tabs(CDP_PORT)
    alive_ids = {t.get("id") for t in all_tabs if t.get("type") == "page"}
    valid = True

    lt_id = session.lifetime_tab_id
    if not lt_id:
        print(f"  {BOLD}{RED}{label}{RESET} Session '{session.name}' has no lifetime_tab_id.")
        valid = False
    elif lt_id not in alive_ids:
        print(f"  {BOLD}{RED}{label}{RESET} Lifetime tab {lt_id[:12]} is dead.")
        print(f"    Expected: alive tab at {(session.lifetime_tab_url or '?')[:60]}")
        print(f"    Alive tabs: {[tid[:12] for tid in sorted(alive_ids)]}")
        valid = False

    demo_info = session._tabs.get("demo")
    if demo_info:
        demo_id = demo_info.get("id") if isinstance(demo_info, dict) else demo_info
        if demo_id and demo_id not in alive_ids:
            print(f"  {BOLD}{YELLOW}{label}{RESET} Demo tab {str(demo_id)[:12]} is dead.")
            valid = False

    if valid:
        tabs_summary = {lbl: (info.get("id", "?")[:12] if isinstance(info, dict) else str(info)[:12])
                        for lbl, info in session._tabs.items()}
        print(f"  {BOLD}{GREEN}{label}{RESET} Session '{session.name}' OK. Tabs: {tabs_summary}")

    return valid


def _close_google_auth_tabs(primary_tab_id, port):
    """Close the primary auth tab and any Google auth-flow tabs.

    Closes tabs matching sign-in/sign-out/ListAccounts URLs.
    Does NOT close general Google pages (e.g. user-opened myaccount.google.com).
    """
    from interface.config import get_color
    from interface.chrome import list_tabs, close_tab
    BOLD, RESET = get_color("BOLD"), get_color("RESET")
    _AUTH_URL_PATTERNS = (
        "accounts.google.com/signin",
        "accounts.google.com/v3/signin",
        "accounts.google.com/ServiceLogin",
        "accounts.google.com/AccountChooser",
        "accounts.google.com/signout",
        "accounts.google.com/ListAccounts",
        "accounts.google.com/Logout",
        "accounts.google.com/RotateCookie",
        "myaccount.google.com",
    )
    tabs = list_tabs(port)
    closed = 0
    for t in tabs:
        if t.get("type") != "page":
            continue
        tid = t.get("id", "")
        url = t.get("url", "")
        should_close = (tid == primary_tab_id or
                        any(p in url for p in _AUTH_URL_PATTERNS))
        if should_close:
            try:
                close_tab(tid, port)
                closed += 1
            except Exception:
                pass
    if closed:
        print(f"  {BOLD}Closed {closed} auth tab(s).{RESET}")


def _poll_login(tab_id, timeout=300):
    """Synchronous poll for login completion. Closes the tab on success."""
    import time as _t
    from interface.config import get_color
    from interface.chrome import CDPSession, list_tabs, CDP_PORT
    auth_mod = _load_auth_mod()
    BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
    completed = False
    for i in range(int(timeout / 2)):
        _t.sleep(2)
        tabs = list_tabs(CDP_PORT)
        tab_alive = any(t.get("id") == tab_id for t in tabs)
        if not tab_alive:
            print(f"  {BOLD}Login tab closed.{RESET}")
            completed = True
            break

        login_tab = next((t for t in tabs if t.get("id") == tab_id), None)
        ws = login_tab.get("webSocketDebuggerUrl") if login_tab else None
        if not ws:
            continue
        try:
            cdp = CDPSession(ws, timeout=3)
            state = auth_mod.check_auth_cookies(cdp, verify=False)
            if state.get("signed_in"):
                verified = auth_mod.check_auth_cookies(cdp, verify=True)
                cdp.close()
                email = verified.get("email") or ""
                name = verified.get("display_name") or ""
                label = email or name or ""
                if email or name:
                    auth_mod._push_identity_to_server({
                        "email": email or None,
                        "display_name": name or None,
                    })
                if label:
                    print(f"  {BOLD}{GREEN}Signed in{RESET} as {label}.")
                else:
                    print(f"  {BOLD}{GREEN}Signed in.{RESET}")
                _t.sleep(0.5)
                _close_google_auth_tabs(tab_id, CDP_PORT)
                completed = True
            else:
                cdp.close()
        except Exception:
            pass
        if completed:
            break
        if i % 15 == 14:
            print(f"  Waiting for sign-in... ({(i+1)*2}s)")
    if not completed:
        print(f"  {BOLD}Timeout.{RESET} Login tab left open for manual sign-in.")


def _poll_logout(tab_id, timeout=60):
    """Synchronous poll for logout completion. Locks tab, clicks Continue, closes tab."""
    import time as _t
    from interface.config import get_color
    from interface.chrome import CDPSession, list_tabs, CDP_PORT
    auth_mod = _load_auth_mod()
    BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
    clicked = False
    completed = False
    for i in range(int(timeout / 1.5)):
        _t.sleep(1.5)
        tabs = list_tabs(CDP_PORT)
        tab_alive = any(t.get("id") == tab_id for t in tabs)
        if not tab_alive:
            print(f"  {BOLD}{GREEN}Signed out.{RESET}")
            _t.sleep(1)
            _close_google_auth_tabs(tab_id, CDP_PORT)
            _t.sleep(2)
            _close_google_auth_tabs(tab_id, CDP_PORT)
            completed = True
            break
        if not clicked:
            _api = _load_api()
            r = _api.click_element("accounts.google.com",
                                   selector='a[href*="continue"], a[href*="ServiceLogin"]')
            if r.get("ok"):
                clicked = True
            else:
                clicked = auth_mod._try_click_signout_continue(tab_id, CDP_PORT)
        for t in tabs:
            ws = t.get("webSocketDebuggerUrl")
            if ws and t.get("type") == "page":
                try:
                    cdp = CDPSession(ws, timeout=5)
                    state = auth_mod.check_auth_cookies(cdp, verify=False)
                    cdp.close()
                    if not state.get("signed_in"):
                        print(f"  {BOLD}{GREEN}Signed out.{RESET}")
                        _t.sleep(1)
                        _close_google_auth_tabs(tab_id, CDP_PORT)
                        _t.sleep(2)
                        _close_google_auth_tabs(tab_id, CDP_PORT)
                        completed = True
                        break
                except Exception:
                    continue
        if completed:
            break
    if not completed:
        print(f"  {BOLD}Timeout.{RESET} Logout tab left open.")


def main():
    tool = CDMCPTool()
    tool.run()


if __name__ == "__main__":
    main()
