#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
ROOT_PROJECT_ROOT = setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color

class GoogleTool(ToolBase):
    def __init__(self):
        super().__init__("GOOGLE")

    def run(self):
        # Early intercept --mcp-login before argparse
        if "--mcp-login" in sys.argv:
            import importlib.util
            login_path = Path(__file__).resolve().parent / "logic" / "mcp" / "login.py"
            spec = importlib.util.spec_from_file_location("google_mcp_login", str(login_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            as_json_flag = "--json" in sys.argv
            email = None
            rest = [a for a in sys.argv[1:] if a not in ("--mcp-login", "--json", "--no-warning")]
            if rest:
                email = rest[0]
            sys.exit(mod.run_mcp_login(email=email, as_json=as_json_flag))

        parser = argparse.ArgumentParser(description="GOOGLE Tool: Ecosystem Proxy", add_help=False)
        parser.add_argument("command", nargs="?", help="Subcommand to run")
        parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the subcommand")
        parser.add_argument("-h", "--help", action="store_true", help="Show this help message")
        
        if self.handle_command_line(parser):
            return

        args = parser.parse_args()

        if args.help or not args.command:
            parser.print_help()
            self.print_rule()
            return

        # Initialize internal modules
        from tool.GOOGLE.logic.engine import GoogleEngine
        engine = GoogleEngine(self.project_root)

        if args.command == "search":
            if not args.args:
                print("Usage: GOOGLE search <query>")
                return
            engine.search(" ".join(args.args))
        elif args.command == "drive":
            if not args.args:
                print("Usage: GOOGLE drive <list|upload|download>")
                return
            subcmd = args.args[0]
            if subcmd == "list":
                engine.drive_list()
            else:
                print(f"Unknown drive command: {subcmd}")
        elif args.command == "trends":
            engine.trends()
        elif args.command == "login":
            self._handle_login(args.args)
        elif args.command == "logout":
            self._handle_logout()
        elif args.command == "boot":
            self._handle_boot()
        elif args.command == "auth-status":
            self._handle_auth_status()
        elif args.command == "open-tab":
            self._handle_open_tab(args.args)
        elif args.command == "tabs":
            self._handle_list_tabs()
        else:
            _KNOWN = {"boot", "auth-status", "open-tab", "tabs", "login", "logout", "search", "drive", "trends"}
            suggestion = ""
            normalized = args.command.replace("_", "-")
            if normalized in _KNOWN:
                suggestion = f" Did you mean '{normalized}'?"
            print(f"Unknown command: {args.command}.{suggestion}")
            print(f"Available: boot, auth-status, open-tab, tabs, login, logout, search, drive, trends")
            print(f"Note: Commands use hyphens, not underscores (e.g. open-tab, auth-status).")

    def _handle_auth_status(self):
        """Check and display Google account login state."""
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")

        from interface.chrome import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            print(f"{BOLD}{RED}Failed{RESET} Chrome CDP not available.")
            return

        from tool.GOOGLE.interface.main import check_login_state
        _log = lambda m: print(f"  {BOLD}{BLUE}[GOOGLE]{RESET} {m}")
        state = check_login_state(log_fn=_log)

        if state["signed_in"]:
            email = state.get("email") or "unknown"
            name = state.get("display_name") or ""
            label = f"{name} ({email})" if name else email
            print(f"{BOLD}{GREEN}Signed in{RESET} as {label}.")
        else:
            print(f"{BOLD}{RED}Not signed in{RESET} to any Google account.")

    def _handle_logout(self):
        """Sign out of the current Google account."""
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")

        from interface.chrome import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            print(f"{BOLD}{RED}Failed{RESET} Chrome CDP not available.")
            return

        from tool.GOOGLE.interface.main import sign_out
        _log = lambda m: print(f"  {BOLD}{BLUE}[GOOGLE]{RESET} {m}")
        ok = sign_out(log_fn=_log)
        if ok:
            print(f"{BOLD}{GREEN}Successfully signed out{RESET} of Google account.")
        else:
            print(f"{BOLD}{RED}Failed to sign out{RESET}.")

    def _handle_boot(self):
        """Ensure Chrome is running with CDP enabled."""
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")

        from interface.chrome import is_chrome_cdp_available
        if is_chrome_cdp_available():
            print(f"{BOLD}{GREEN}Already running{RESET} Chrome CDP is available.")
            return

        print(f"  {BOLD}{BLUE}Launching{RESET} Chrome with CDP...")
        try:
            from interface.cdmcp import load_cdmcp_sessions
            sm = load_cdmcp_sessions()
            result = sm.ensure_chrome()
        except ImportError:
            from interface.chrome import CDP_PORT
            import subprocess as _sp
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
            chrome_bin = None
            for p in chrome_paths:
                if Path(p).exists():
                    chrome_bin = p
                    break
            if not chrome_bin:
                print(f"{BOLD}{RED}Failed{RESET} Chrome binary not found.")
                return
            profile_dir = Path.home() / ".cursor" / "chrome-cdp-profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            _sp.Popen([
                chrome_bin,
                f"--remote-debugging-port={CDP_PORT}",
                f"--user-data-dir={str(profile_dir)}",
                "--remote-allow-origins=*",
            ])
            import time
            for _ in range(10):
                time.sleep(1)
                if is_chrome_cdp_available():
                    result = {"ok": True, "action": "relaunched"}
                    break
            else:
                result = {"ok": False, "error": "Timeout waiting for CDP"}

        if result.get("ok"):
            action = result.get("action", "ready")
            print(f"{BOLD}{GREEN}Ready{RESET} Chrome CDP is now available ({action}).")
        else:
            print(f"{BOLD}{RED}Failed{RESET} {result.get('error', 'Unknown error')}.")

    def _handle_open_tab(self, extra_args):
        """Open a new Chrome tab via CDP. Auto-boots Chrome if not running."""
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        RESET = get_color("RESET")

        url = extra_args[0] if extra_args else "about:blank"
        url = url.strip('"').strip("'")
        if not url.startswith(("http://", "https://", "about:", "chrome:")):
            url = "https://" + url

        from interface.chrome import is_chrome_cdp_available, open_tab
        if not is_chrome_cdp_available():
            print(f"  Chrome CDP not available, booting...")
            self._handle_boot()
            if not is_chrome_cdp_available():
                return

        ok = open_tab(url)
        if ok:
            print(f"{BOLD}{GREEN}Opened{RESET} new tab: {url}")
        else:
            print(f"{BOLD}{RED}Failed{RESET} to open tab.")

    def _handle_list_tabs(self):
        """List open Chrome tabs via CDP."""
        BOLD = get_color("BOLD")
        get_color("GREEN")
        RED = get_color("RED")
        RESET = get_color("RESET")

        from interface.chrome import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            print(f"{BOLD}{RED}Failed{RESET} Chrome CDP not available.")
            return

        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:9222/json/list", timeout=5) as resp:
                tabs = json.loads(resp.read().decode())
            if not tabs:
                print("  No open tabs.")
                return
            print(f"  {BOLD}Open tabs{RESET} ({len(tabs)}):")
            for i, t in enumerate(tabs[:20]):
                title = t.get("title", "")[:60]
                url = t.get("url", "")[:80]
                print(f"    {i+1}. {title}")
                print(f"       {url}")
        except Exception as e:
            print(f"{BOLD}{RED}Failed{RESET} to list tabs: {e}")

    def _handle_login(self, extra_args):
        """Sign in to a Google account via CDP automation."""
        import argparse as _ap

        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")

        p = _ap.ArgumentParser(prog="GOOGLE login", add_help=False)
        p.add_argument("--email", type=str, help="Google account email")
        p.add_argument("--password", type=str, help="Account password (prefer USERINPUT)")
        p.add_argument("--recovery-code", type=str, help="2FA recovery code")
        p.add_argument("--json", action="store_true", help="Output workflow as JSON")
        login_args, _ = p.parse_known_args(extra_args)

        if login_args.json:
            from tool.GOOGLE.logic.utils.mcp.login import run_mcp_login
            return run_mcp_login(email=login_args.email, as_json=True)

        from interface.chrome import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            print(f"{BOLD}{RED}Failed{RESET} Chrome CDP not available.")
            print("  Start Chrome with remote debugging: chrome --remote-debugging-port=9222")
            return

        email = login_args.email
        password = login_args.password

        if not email:
            print(f"{BOLD}{RED}Missing{RESET} --email argument.")
            print(f"  Usage: GOOGLE login --email <email> [--password <pwd>] [--recovery-code <code>]")
            print(f"  Tip: Use USERINPUT to collect password securely.")
            return

        if not password:
            print(f"{BOLD}{RED}Missing{RESET} --password argument.")
            print(f"  Usage: GOOGLE login --email {email} --password <pwd>")
            print(f"  Security: Collect password via USERINPUT, then pass it here.")
            return

        from tool.GOOGLE.interface.main import sign_in
        _log = lambda m: print(f"  {BOLD}{BLUE}[GOOGLE]{RESET} {m}")

        result = sign_in(
            email=email,
            password=password,
            recovery_code=login_args.recovery_code,
            log_fn=_log,
        )

        if result["success"]:
            print(f"{BOLD}{GREEN}Successfully signed in{RESET} as {email}.")
        else:
            print(f"{BOLD}{RED}Failed to sign in{RESET}: {result.get('error', 'unknown error')}.")


def main():
    tool = GoogleTool()
    tool.run()

if __name__ == "__main__":
    main()
