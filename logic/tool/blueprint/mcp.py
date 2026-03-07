"""MCP Tool Blueprint — extends ToolBase with CDMCP session and browser MCP commands.

MCP-enabled tools inherit from MCPToolBase to gain:
  - create_session / boot / checkout commands
  - Auto-lock enforcement on browser tabs
  - Session window awareness (opens tabs in session window)
  - Shared CDMCP overlay and interaction interfaces
"""
import sys
import time
from pathlib import Path
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
                from logic.cdmcp_loader import (
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

        from logic.interface.config import get_color
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
                from logic.cdmcp_loader import load_cdmcp_server
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
