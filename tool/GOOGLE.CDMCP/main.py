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

from logic.tool.blueprint.base import ToolBase
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

    def run(self):
        parser = argparse.ArgumentParser(
            description="CDMCP: Chrome DevTools MCP with visual overlays",
            add_help=False,
        )
        sub = parser.add_subparsers(dest="command", help="Subcommand")

        sub.add_parser("status", help="Check Chrome CDP availability and managed tabs")
        sub.add_parser("tutorial", help="Run interactive setup tutorial")

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

        elif args.command == "navigate":
            r = api.navigate(args.url)
            if r.get("ok"):
                print(f"  {BOLD}{GREEN}Navigated{RESET} to {args.url} ({r.get('action', 'unknown')}).")
            else:
                print(f"  {BOLD}{RED}Failed{RESET} to navigate: {r.get('error', 'unknown')}")

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

        else:
            parser.print_help()


def _run_scan(api, args, BOLD, GREEN, RED, BLUE, RESET):
    """Scan a tab for all interactive elements."""
    import time
    from logic.chrome.session import (
        CDPSession, list_tabs, capture_screenshot, find_tab, dispatch_key,
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


def main():
    tool = CDMCPTool()
    tool.run()


if __name__ == "__main__":
    main()
