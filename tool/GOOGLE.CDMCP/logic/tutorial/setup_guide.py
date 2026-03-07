"""CDMCP Setup Tutorial — Interactive guide for first-time setup.

Walks the user through:
  1. Verifying Chrome is running with CDP enabled
  2. Testing CDP connectivity
  3. Configuring privacy settings
  4. Running the first overlay injection
"""
import sys
import json
import time
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
BLUE = get_color("BLUE")
RESET = get_color("RESET")


def _check(label, passed, detail=""):
    status = f"{GREEN}OK{RESET}" if passed else f"{RED}FAIL{RESET}"
    line = f"  [{BOLD}{status}{RESET}] {label}"
    if detail:
        line += f" ({detail})"
    print(line)
    return passed


def run_setup_tutorial():
    print()
    print(f"  {BOLD}CDMCP Setup Tutorial{RESET}")
    print(f"  {'=' * 40}")
    print()

    # Step 1: Check Chrome CDP
    print(f"  {BOLD}Step 1:{RESET} Checking Chrome CDP availability...")
    from logic.chrome.session import is_chrome_cdp_available, CDP_PORT
    cdp_ok = is_chrome_cdp_available(CDP_PORT)
    _check("Chrome CDP on port 9222", cdp_ok,
           "Running" if cdp_ok else "Start Chrome with --remote-debugging-port=9222 --remote-allow-origins=*")
    if not cdp_ok:
        print()
        print(f"  {YELLOW}To start Chrome with CDP:{RESET}")
        print(f"    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
        print(f"      --remote-debugging-port=9222 --remote-allow-origins=*")
        print()
        print(f"  Or on Linux:")
        print(f"    google-chrome --remote-debugging-port=9222 --remote-allow-origins=*")
        print()
        return False
    print()

    # Step 2: List existing tabs
    print(f"  {BOLD}Step 2:{RESET} Checking existing browser tabs...")
    from logic.chrome.session import list_tabs
    tabs = list_tabs(CDP_PORT)
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    _check(f"Found {len(page_tabs)} open tabs", len(page_tabs) > 0)
    for i, t in enumerate(page_tabs[:5]):
        print(f"    [{i+1}] {t.get('title', '?')[:50]} - {t.get('url', '?')[:60]}")
    print()

    # Step 3: Test overlay injection
    print(f"  {BOLD}Step 3:{RESET} Testing overlay injection...")
    if page_tabs:
        from logic.cdmcp_loader import load_cdmcp_overlay
        _ov = load_cdmcp_overlay()
        get_session = _ov.get_session
        inject_badge = _ov.inject_badge
        remove_badge = _ov.remove_badge
        tab = page_tabs[0]
        session = get_session(tab)
        if session:
            badge_ok = inject_badge(session, text="CDMCP Setup", color="#1a73e8")
            _check("Badge injection", badge_ok, tab.get("title", "?")[:40])
            time.sleep(1)
            remove_badge(session)
            session.close()
        else:
            _check("Session connection", False, "Cannot connect to tab")
    print()

    # Step 4: Config
    print(f"  {BOLD}Step 4:{RESET} Configuration...")
    import importlib.util
    api_path = Path(__file__).resolve().parent.parent.parent / "logic" / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("cdmcp_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = mod.get_config()
    print(f"    OAuth windows: {BOLD}{'Allowed' if cfg.get('allow_oauth_windows') else 'Blocked'}{RESET}")
    print(f"    Interaction logging: {BOLD}{'Enabled' if cfg.get('log_interactions') else 'Disabled'}{RESET}")
    print(f"    Badge color: {cfg.get('badge_color', '#1a73e8')}")
    _check("Configuration loaded", True)
    print()

    # Summary
    print(f"  {BOLD}Setup Complete{RESET}")
    print(f"  {'=' * 40}")
    print(f"  Use 'CDMCP navigate <url>' to open a managed tab.")
    print(f"  Use 'CDMCP config' to adjust settings.")
    print(f"  Use 'CDMCP --help' for all commands.")
    print()
    return True


if __name__ == "__main__":
    run_setup_tutorial()
