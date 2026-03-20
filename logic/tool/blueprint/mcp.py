"""MCP Tool Blueprint — extends ToolBase with CDMCP session and browser MCP commands.

MCP-enabled tools inherit from MCPToolBase to gain:
  - create_session / boot / checkout commands
  - Auto-lock enforcement on browser tabs
  - Session window awareness (opens tabs in session window)
  - Shared CDMCP overlay and interaction interfaces
  - MCP state reporting (get_mcp_state) for monitoring tab/tool status
"""
import sys
from typing import Optional, Dict, Any

from logic.tool.blueprint.base import ToolBase


class MCPToolBase(ToolBase):
    """Base class for tools that use CDMCP browser MCP integration."""

    def __init__(self, tool_name: str, session_name: str = ""):
        super().__init__(tool_name)
        self._session_name = session_name or tool_name.lower().replace(".", "_")
        self._overlay = None
        self._interact = None
        self._session_mgr = None

    def _load_cdmcp(self):
        """Lazily load CDMCP modules."""
        if self._overlay is None:
            try:
                from logic.utils.chrome.loader import (
                    load_cdmcp_overlay,
                    load_cdmcp_interact,
                    load_cdmcp_sessions,
                )
                self._overlay = load_cdmcp_overlay()
                self._interact = load_cdmcp_interact()
                self._session_mgr = load_cdmcp_sessions()
            except Exception:
                pass

    @property
    def overlay(self):
        self._load_cdmcp()
        return self._overlay

    @property
    def interact(self):
        self._load_cdmcp()
        return self._interact

    @property
    def session_mgr(self):
        self._load_cdmcp()
        return self._session_mgr

    def get_session(self):
        """Get the current CDMCP session for this tool (by name)."""
        if not self.session_mgr:
            return None
        return self.session_mgr.get_session(self._session_name)

    def get_session_window_id(self) -> Optional[int]:
        """Get the window ID of the active session, if any."""
        if not self.session_mgr:
            return None
        for info in self.session_mgr.list_sessions():
            wid = info.get("window_id")
            if wid:
                return wid
        return None

    def ensure_locked(self, cdp_session, auto_lock: bool = True) -> bool:
        """Ensure the tab is locked. If not locked and auto_lock=True, lock it.

        Returns True if locked, False if not locked and auto_lock is False.
        """
        if not self.overlay:
            return False
        if self.overlay.is_locked(cdp_session):
            return True
        if auto_lock:
            self.overlay.inject_lock(
                cdp_session, base_opacity=0.08, flash_opacity=0.25,
                tool_name=self.tool_name,
            )
            return True
        return False

    def apply_overlays(self, cdp_session, badge_text: str = "",
                       color: str = "#1a73e8", letter: str = ""):
        """Apply standard CDMCP overlays (badge, focus, favicon, lock)."""
        if not self.overlay:
            return
        if not badge_text:
            badge_text = f"{self.tool_name} [mcp]"
        if not letter:
            letter = self.tool_name[0]
        self.overlay.inject_badge(cdp_session, text=badge_text, color=color)
        self.overlay.inject_focus(cdp_session, color=color)
        self.overlay.inject_favicon(cdp_session, svg_color=color, letter=letter)
        self.overlay.inject_lock(
            cdp_session, base_opacity=0.08, flash_opacity=0.25,
            tool_name=self.tool_name,
        )

    def cleanup_overlays(self, cdp_session):
        """Remove all CDMCP overlays from the tab."""
        if self.overlay:
            try:
                self.overlay.remove_all_overlays(cdp_session)
            except Exception:
                pass

    def handle_command_line(self, parser=None, dev_handler=None, test_handler=None):
        """Override to intercept ``--mcp-state`` and reformat ``--help``."""
        if "--mcp-state" in sys.argv:
            sys.argv = [a for a in sys.argv if a != "--mcp-state"]
            self.print_mcp_state()
            return True
        if parser and any(a in sys.argv for a in ["-h", "--help", "help"]):
            self._print_mcp_help(parser)
            return True
        return super().handle_command_line(parser, dev_handler, test_handler)

    @staticmethod
    def _print_mcp_help(parser):
        """Print help with --mcp- prefix for all subcommands."""
        help_text = parser.format_help()
        subparsers_action = None
        for action in parser._actions:
            if hasattr(action, '_parser_class'):
                subparsers_action = action
                break
        if subparsers_action and hasattr(subparsers_action, 'choices'):
            cmds = list(subparsers_action.choices.keys())
            choices_str = ",".join(cmds)
            mcp_choices = ",".join(f"--mcp-{c}" for c in cmds)
            help_text = help_text.replace("{" + choices_str + "}", "{" + mcp_choices + "}")
            for cmd in cmds:
                help_text = help_text.replace(
                    f"\n    {cmd}" + " " * max(1, 20 - len(cmd)),
                    f"\n    --mcp-{cmd}" + " " * max(1, 14 - len(cmd)),
                )
        help_text += "\n  --mcp-state           Print comprehensive MCP state and exit\n"
        print(help_text)

    def handle_mcp_commands(self, args) -> bool:
        """Handle MCP-specific CLI subcommands. Returns True if handled.

        Recognized subcommands (after --mcp):
          session create <name>   Create a new session
          session boot [name]     Boot a session (open window + welcome page)
          session list            List active sessions
          session checkout <name> Switch to a session
        """
        if not args:
            return False

        cmd = args[0] if args else ""
        if cmd != "session":
            return False

        subcmd = args[1] if len(args) > 1 else "list"
        name = args[2] if len(args) > 2 else self._session_name

        from interface.config import get_color
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RESET = get_color("RESET")

        if subcmd == "create":
            self._load_cdmcp()
            if self.session_mgr:
                s = self.session_mgr.create_session(name, timeout_sec=86400)
                print(f"  {BOLD}{GREEN}Created{RESET} session '{name}' [{s.session_id[:8]}].")
            return True

        elif subcmd == "boot":
            self._load_cdmcp()
            if self.session_mgr:
                from logic.utils.chrome.loader import load_cdmcp_server
                server = load_cdmcp_server()
                server_url, _ = server.start_server()

                s = self.session_mgr.create_session(name, timeout_sec=86400)
                sid = s.session_id[:8]
                created_ts = int(s.created_at)
                welcome_url = (
                    f"{server_url}/welcome?session_id={sid}"
                    f"&port=9222&timeout_sec=86400&created_at={created_ts}"
                    f"&idle_timeout_sec=3600&last_activity={created_ts}"
                )
                boot_result = s.boot(welcome_url, new_window=True)
                if boot_result.get("ok"):
                    print(f"  {BOLD}{GREEN}Booted{RESET} session '{name}' [{sid}].")
                    print(f"  Window: {boot_result.get('windowId')}")
                else:
                    print(f"  Failed to boot: {boot_result.get('error')}")
            return True

        elif subcmd == "list":
            self._load_cdmcp()
            if self.session_mgr:
                sessions = self.session_mgr.list_sessions()
                if sessions:
                    for s in sessions:
                        print(f"  {s['name']} [{s['session_id'][:8]}] "
                              f"window={s.get('window_id')} "
                              f"expired={s.get('expired')}")
                else:
                    print("  No active sessions.")
            return True

        elif subcmd == "checkout":
            self._load_cdmcp()
            if self.session_mgr:
                s = self.session_mgr.get_session(name)
                if s:
                    self._session_name = name
                    print(f"  {BOLD}{GREEN}Checked out{RESET} session '{name}' [{s.session_id[:8]}].")
                else:
                    print(f"  Session '{name}' not found.")
            return True

        return False

    # ── MCP State Interface ──────────────────────────────────────────────

    def get_mcp_state(self, session_id: str = "",
                      tab_label: str = "") -> Dict[str, Any]:
        """Return the current MCP state for this tool.

        Subclasses MUST override _collect_mcp_state() to supply tool-specific
        state (e.g. Colab cells, YouTube video, XMind map structure).

        The base implementation wraps the tool-specific state with common
        CDMCP session information.

        Args:
            session_id: Optional session ID to query. Empty = active session.
            tab_label: Optional tab label to focus on.

        Returns:
            Dict with keys:
              tool: str           -- tool name
              session: dict|None  -- CDMCP session info
              tabs: list          -- registered session tabs
              state: dict         -- tool-specific state from _collect_mcp_state()
              timestamp: float    -- when state was collected
              ok: bool            -- whether collection succeeded
        """
        import time as _time

        result = {
            "tool": self.tool_name,
            "session": None,
            "tabs": [],
            "state": {},
            "timestamp": _time.time(),
            "ok": False,
        }

        self._load_cdmcp()
        sid = session_id or self._session_name
        session = None
        if self.session_mgr:
            session = self.session_mgr.get_session(sid)
            if not session:
                for info in self.session_mgr.list_sessions():
                    if session_id and info.get("session_id", "").startswith(session_id):
                        session = self.session_mgr.get_session(info["name"])
                        break
                    elif not session_id:
                        session = self.session_mgr.get_session(info["name"])
                        break

        if session:
            result["session"] = {
                "name": getattr(session, "name", sid),
                "session_id": getattr(session, "session_id", ""),
                "window_id": getattr(session, "window_id", None),
                "booted": getattr(session, "booted", False),
            }
            tabs_info = getattr(session, "tabs", {})
            if isinstance(tabs_info, dict):
                result["tabs"] = [
                    {"label": k, **v} for k, v in tabs_info.items()
                ]

        try:
            tool_state = self._collect_mcp_state(
                session=session, tab_label=tab_label,
            )
            result["state"] = tool_state or {}
            result["ok"] = True
        except Exception as exc:
            result["state"] = {"error": str(exc)}

        return result

    def _collect_mcp_state(self, session=None,
                           tab_label: str = "") -> Dict[str, Any]:
        """Override in subclass to return tool-specific MCP state.

        This is called by get_mcp_state(). Return a dict with whatever
        state is relevant for the tool. For example, GOOGLE.GC returns
        cell list, runtime status, etc.

        Args:
            session: The CDMCPSession object (or None).
            tab_label: Optional tab label to focus on.

        Returns:
            Dict with tool-specific state.
        """
        return {}

    def print_mcp_state(self, session_id: str = "",
                        tab_label: str = "") -> None:
        """Print a human-readable MCP state report."""
        import json as _json
        from interface.config import get_color
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        get_color("BLUE")
        RED = get_color("RED")
        YELLOW = get_color("YELLOW")
        RESET = get_color("RESET")

        state = self.get_mcp_state(session_id=session_id, tab_label=tab_label)

        status = f"{GREEN}OK{RESET}" if state["ok"] else f"{RED}ERROR{RESET}"
        print(f"  {BOLD}MCP State{RESET} [{self.tool_name}]: {status}")

        sess = state.get("session")
        if sess:
            sid = sess.get("session_id", "?")[:8]
            print(f"  {BOLD}Session{RESET}: {sess.get('name', '?')} [{sid}]"
                  f"  window={sess.get('window_id', '?')}")
        else:
            print(f"  {BOLD}{YELLOW}Session{RESET}: None")

        tabs = state.get("tabs", [])
        if tabs:
            print(f"  {BOLD}Tabs{RESET} ({len(tabs)}):")
            for tab in tabs:
                label = tab.get("label", "?")
                st = tab.get("state", "?")
                url = (tab.get("url", "") or "")[:60]
                print(f"    {label}: {st} | {url}")

        tool_state = state.get("state", {})
        if tool_state:
            print(f"  {BOLD}Tool State{RESET}:")
            for k, v in tool_state.items():
                if isinstance(v, list) and len(v) > 5:
                    print(f"    {k}: [{len(v)} items]")
                    for item in v[:5]:
                        if isinstance(item, dict):
                            summary = ", ".join(f"{kk}={vv}" for kk, vv in
                                                list(item.items())[:3])
                            print(f"      {summary}")
                        else:
                            print(f"      {item}")
                    if len(v) > 5:
                        print(f"      ... ({len(v) - 5} more)")
                elif isinstance(v, dict):
                    print(f"    {k}: {_json.dumps(v, ensure_ascii=False)}")
                else:
                    print(f"    {k}: {v}")
