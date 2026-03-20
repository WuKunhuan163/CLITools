#!/usr/bin/env python3
import sys
import argparse
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


_APP_URL = "https://coggle.it"
_URL_PATTERN = "coggle.it"


def main():
    tool = ToolBase("COGGLE")

    parser = argparse.ArgumentParser(
        description="Coggle mind mapping via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., COGGLE --mcp-boot",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand")

    sub.add_parser("boot", help="Boot Coggle CDMCP session")
    sub.add_parser("status", help="Check auth state and page info")
    sub.add_parser("state", help="Get full MCP state as JSON")
    sub.add_parser("session", help="Show session details")
    sub.add_parser("diagrams", help="List diagrams on current page")
    sub.add_parser("explore", help="Run DOM exploration on current page")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    cmd = args.command

    if not cmd:
        parser.print_help()
        return

    if cmd == "boot":
        _cmd_boot(tool)
    elif cmd == "status":
        _cmd_status(tool)
    elif cmd == "state":
        _cmd_state(tool)
    elif cmd == "session":
        _cmd_session(tool)
    elif cmd == "diagrams":
        _cmd_diagrams(tool)
    elif cmd == "explore":
        _cmd_explore(tool)
    else:
        parser.print_help()


def _cmd_boot(tool):
    from interface.cdmcp import load_cdmcp_sessions, load_cdmcp_overlay
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    try:
        sm = load_cdmcp_sessions()
    except ImportError as e:
        print(f"{BOLD}{RED}Error{RESET}: CDMCP not available ({e}).")
        return

    result = sm.boot_tool_session(session_name="coggle")
    if not result.get("ok"):
        print(f"{BOLD}{RED}Failed to boot{RESET}: {result.get('error', '?')}")
        return

    session = result.get("session")
    if not session:
        print(f"{BOLD}{RED}Failed to boot{RESET}: no session returned.")
        return

    tab_info = session.require_tab(
        label="coggle",
        url_pattern=_URL_PATTERN,
        open_url=_APP_URL,
        wait_sec=15.0,
    )

    if tab_info and tab_info.get("ws"):
        from interface.chrome import CDPSession
        try:
            ov = load_cdmcp_overlay()
            cdp = CDPSession(tab_info["ws"], timeout=10)
            ov.inject_badge(cdp, text="COGGLE", color="#62D0F1")
            ov.inject_focus(cdp, color="#62D0F1")
            ov.inject_favicon(cdp, svg_color="#62D0F1", letter="C")
            ov.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25, tool_name="COGGLE")
            cdp.close()
        except Exception:
            pass
        print(f"{BOLD}{GREEN}Successfully booted{RESET} Coggle session.")
        print(f"  Tab: {tab_info.get('url', '?')[:60]}")
    else:
        print(f"{BOLD}{GREEN}Successfully booted{RESET} session (no Coggle tab found).")
        print(f"  Please open {_APP_URL} in the session window.")


def _cmd_status(tool):
    from interface.chrome import CDPSession, is_chrome_cdp_available
    BOLD = get_color("BOLD")
    RED = get_color("RED")
    RESET = get_color("RESET")

    if not is_chrome_cdp_available():
        print(f"{BOLD}{RED}Error{RESET}: Chrome CDP not available.")
        return

    tab = _find_tab()
    if not tab:
        print(f"{BOLD}{RED}No Coggle tab{RESET} found. Run COGGLE --mcp-boot first.")
        return

    try:
        s = CDPSession(tab["webSocketDebuggerUrl"], timeout=10)
        title = s.evaluate("document.title || ''") or ""
        url = s.evaluate("window.location.href || ''") or ""
        s.close()
        print(f"{BOLD}Title{RESET}: {title}")
        print(f"{BOLD}URL{RESET}: {url}")
    except Exception as e:
        print(f"{BOLD}{RED}Error{RESET}: {e}")


def _cmd_state(tool):
    import json
    from interface.chrome import CDPSession, is_chrome_cdp_available

    state = {"cdp_available": False, "coggle_tab": None, "page": {}}

    if not is_chrome_cdp_available():
        print(json.dumps(state, indent=2))
        return

    state["cdp_available"] = True
    tab = _find_tab()
    if not tab:
        print(json.dumps(state, indent=2))
        return

    state["coggle_tab"] = {"id": tab.get("id", ""), "url": tab.get("url", "")}
    try:
        s = CDPSession(tab["webSocketDebuggerUrl"], timeout=10)
        page_info = s.evaluate("""
            (function(){
                return JSON.stringify({
                    title: document.title || '',
                    url: window.location.href || '',
                    pathname: window.location.pathname || '',
                });
            })()
        """)
        if page_info:
            state["page"] = json.loads(page_info)
        s.close()
    except Exception as e:
        state["error"] = str(e)

    print(json.dumps(state, indent=2))


def _cmd_session(tool):
    try:
        from interface.cdmcp import load_cdmcp_sessions
        smod = load_cdmcp_sessions()
    except ImportError as e:
        print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: {e}")
        return
    session = smod.get_session("coggle")
    if not session:
        print(f"{get_color('BOLD')}No active session{get_color('RESET')}. Run COGGLE --mcp-boot.")
        return
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")
    print(f"{BOLD}Session ID{RESET}: {session.session_id}")
    print(f"{BOLD}Window ID{RESET}: {session.window_id}")


def _cmd_diagrams(tool):
    from interface.chrome import CDPSession
    tab = _find_tab()
    if not tab:
        print(f"{get_color('BOLD')}{get_color('RED')}No Coggle tab{get_color('RESET')} found.")
        return

    s = CDPSession(tab["webSocketDebuggerUrl"], timeout=10)
    diagrams = s.evaluate("""
        (function(){
            var items = document.querySelectorAll('[class*="diagram"], [class*="document"], a[href*="/diagram/"]');
            var out = [];
            for (var i = 0; i < Math.min(items.length, 30); i++) {
                var el = items[i];
                out.push({
                    text: (el.textContent || '').trim().substring(0, 80),
                    href: el.getAttribute('href') || '',
                    tag: el.tagName,
                    cls: (el.className || '').toString().substring(0, 60)
                });
            }
            return JSON.stringify(out);
        })()
    """)
    s.close()

    import json
    items = json.loads(diagrams or "[]")
    if not items:
        print("No diagrams found on current page.")
        return
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")
    for i, item in enumerate(items):
        print(f"  {BOLD}{i+1}{RESET}. {item.get('text', '?')[:60]}")


def _cmd_explore(tool):
    from interface.chrome import CDPSession, capture_screenshot
    tab = _find_tab()
    if not tab:
        print(f"{get_color('BOLD')}{get_color('RED')}No Coggle tab{get_color('RESET')} found.")
        return

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")
    s = CDPSession(tab["webSocketDebuggerUrl"], timeout=10)

    elements = s.evaluate("""
        (function(){
            var selectors = 'button, [role=button], [role=tab], [role=menuitem], '
                          + 'input, textarea, select, a[href], [contenteditable], '
                          + '[role=checkbox], [role=radio], [role=switch], '
                          + '[role=slider], [role=combobox], [role=listbox], '
                          + '[role=link], [role=option], [tabindex]';
            var all = document.querySelectorAll(selectors);
            var out = [];
            for(var i=0; i<all.length; i++){
                var el = all[i];
                var rect = el.getBoundingClientRect();
                if(rect.width <= 0 || rect.height <= 0) continue;
                out.push({
                    tag: el.tagName, id: el.id||'',
                    text: (el.textContent||'').trim().substring(0, 60),
                    title: el.getAttribute('title')||'',
                    aria: el.getAttribute('aria-label')||'',
                    role: el.getAttribute('role')||'',
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height)
                });
            }
            out.sort(function(a,b){ return a.y === b.y ? a.x - b.x : a.y - b.y; });
            return JSON.stringify(out);
        })()
    """)

    import json
    items = json.loads(elements or "[]")
    print(f"{BOLD}Found {len(items)} interactive elements{RESET}:")
    for item in items[:30]:
        label = item.get("text") or item.get("aria") or item.get("title") or item.get("id") or "?"
        print(f"  [{item['tag']}] {label[:50]}  ({item['x']},{item['y']} {item['w']}x{item['h']})")

    img = capture_screenshot(s)
    if img:
        out_path = _r / "tmp" / "coggle_explore.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(img)
        print(f"\n{BOLD}Screenshot{RESET}: {out_path}")

    s.close()


def _find_tab():
    from interface.chrome import list_tabs
    try:
        for t in list_tabs(9222):
            if t.get("type") == "page" and _URL_PATTERN in (t.get("url", "") or ""):
                return t
    except Exception:
        pass
    return None


if __name__ == "__main__":
    main()
