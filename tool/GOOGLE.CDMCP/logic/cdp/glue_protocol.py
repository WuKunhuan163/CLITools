"""Human-in-the-Loop (HITL) Protocol — attended automation with user intervention.

Implements the "User Intervention Point" pattern for browser automation:
when an automated workflow requires manual user action (e.g., login, CAPTCHA,
consent dialog, MFA), this module opens a tab, monitors it, and resumes
automation when the user completes their part.

Terminology:
  - HITL (Human-in-the-Loop): Automation that requires human participation
  - Attended Automation: RPA term for human-assisted automated workflows
  - User Intervention Point (UIP): A defined step where control passes to user
  - Handoff: The moment automation yields to human action
  - Completion Detector: Callback that determines when user action is done

Protocol flow:
  1. Agent opens a tab for the user action (handoff)
  2. Tab is monitored via a customizable completion detector
  3. Completion callback fires when user finishes
  4. Automation resumes (tab optionally auto-closes)

Default completion: fires on tab close (user closes the tab = action done).
Override: provide a custom `is_complete` callable for domain-specific detection
(e.g., Google auth cookie check, OAuth redirect, CAPTCHA solve).
"""

import json
import time
import threading
from typing import Optional, Dict, Any, Callable

from logic.chrome.session import CDPSession, CDP_PORT, list_tabs, close_tab

_active_trackers: Dict[str, "UserActionTracker"] = {}


class UserActionTracker:
    """Tracks a tab opened for user manual interaction.

    Args:
        session: The CDMCPSession that owns the tab.
        tab_id: Chrome tab ID to monitor.
        label: Human-readable label for this action (e.g., "google_login").
        is_complete: Callable(tab_ws, tab_url) -> bool. Called each poll cycle.
            Returns True when the user action is considered complete.
            Default: None (fires only on tab close).
        on_complete: Callable(result_dict) -> None. Called when action completes.
        auto_close: Whether to close the tab after completion detection.
        poll_interval: Seconds between poll cycles.
        timeout: Maximum seconds to wait before giving up (0 = no timeout).
        tip_text: Optional banner text shown on the monitored tab.
        tip_color: Banner background color.
    """

    def __init__(self,
                 session,
                 tab_id: str,
                 label: str = "user_action",
                 is_complete: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None,
                 auto_close: bool = True,
                 poll_interval: float = 1.5,
                 timeout: float = 0,
                 tip_text: str = "",
                 tip_color: str = "#1a73e8"):
        self.session = session
        self.tab_id = tab_id
        self.label = label
        self._is_complete = is_complete
        self._on_complete = on_complete
        self.auto_close = auto_close
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.tip_text = tip_text
        self.tip_color = tip_color

        self._running = False
        self._completed = False
        self._result: Dict[str, Any] = {}
        self._thread: Optional[threading.Thread] = None

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def result(self) -> Dict[str, Any]:
        return self._result

    def start(self):
        """Start monitoring in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True,
            name=f"glue-{self.label}-{self.tab_id[:8]}")
        self._thread.start()
        _active_trackers[self.tab_id] = self

    def stop(self):
        """Stop monitoring."""
        self._running = False
        _active_trackers.pop(self.tab_id, None)

    def wait(self, timeout: float = 0) -> Dict[str, Any]:
        """Block until action completes or timeout. Returns result dict."""
        deadline = time.time() + timeout if timeout > 0 else float('inf')
        while self._running and not self._completed:
            if time.time() > deadline:
                self.stop()
                return {"status": "timeout", "label": self.label}
            time.sleep(0.5)
        return self._result

    def _poll_loop(self):
        """Main polling loop."""
        start_time = time.time()
        overlay_injected = False

        try:
            while self._running and not self._completed:
                if self.timeout > 0 and (time.time() - start_time) > self.timeout:
                    self._finish("timeout")
                    break

                tabs = list_tabs(self.session.port)
                tab_alive = False
                tab_ws = None
                tab_url = ""

                for t in tabs:
                    if t.get("id") == self.tab_id:
                        tab_alive = True
                        tab_ws = t.get("webSocketDebuggerUrl")
                        tab_url = t.get("url", "")
                        break

                if not tab_alive:
                    self._finish("tab_closed")
                    break

                if tab_ws and self.tip_text and not overlay_injected:
                    self._inject_tip(tab_ws)
                    overlay_injected = True

                if tab_ws and self._is_complete:
                    try:
                        if self._is_complete(tab_ws, tab_url):
                            self._finish("complete", tab_url=tab_url)
                            break
                    except Exception:
                        pass

                time.sleep(self.poll_interval)
        finally:
            if not self._completed:
                self._finish("stopped")
            self._running = False
            _active_trackers.pop(self.tab_id, None)

    def _finish(self, status: str, tab_url: str = ""):
        """Mark the action as finished and invoke callbacks."""
        self._completed = True
        self._result = {
            "status": status,
            "label": self.label,
            "tab_id": self.tab_id,
            "url": tab_url,
        }

        if self.auto_close and status in ("complete", "tab_closed"):
            if status == "complete":
                try:
                    time.sleep(0.8)
                    close_tab(self.tab_id, self.session.port)
                except Exception:
                    pass

        if self._on_complete:
            try:
                self._on_complete(self._result)
            except Exception:
                pass

    def _inject_tip(self, ws: str):
        """Show a tip banner on the tab."""
        try:
            import importlib.util
            overlay_path = (
                self.session._tool_dir if hasattr(self.session, '_tool_dir')
                else self.session.__class__.__module__.replace('.', '/')
            )
            from pathlib import Path
            _TOOL_DIR = Path(__file__).resolve().parent.parent.parent
            ov_path = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
            spec = importlib.util.spec_from_file_location("cdmcp_ov_glue", str(ov_path))
            ov = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ov)
            cdp = CDPSession(ws, timeout=5)
            ov.inject_tip(cdp, self.tip_text, bg_color=self.tip_color)
            cdp.close()
        except Exception:
            pass


def track_user_action(session, url: str, label: str = "user_action",
                      is_complete: Optional[Callable] = None,
                      on_complete: Optional[Callable] = None,
                      auto_close: bool = True,
                      poll_interval: float = 1.5,
                      timeout: float = 0,
                      tip_text: str = "",
                      tip_color: str = "#1a73e8",
                      blocking: bool = False) -> UserActionTracker:
    """Open a tab for a user action and start tracking it.

    Convenience function that combines require_tab + UserActionTracker.

    Args:
        session: CDMCPSession instance.
        url: URL to open for the user action.
        label: Label for the tab and tracker.
        is_complete: Custom completion detector. Default: tab close only.
        on_complete: Callback when action completes.
        auto_close: Auto-close tab on completion.
        poll_interval: Seconds between polls.
        timeout: Max seconds to wait (0 = forever).
        tip_text: Banner text on the tab.
        tip_color: Banner color.
        blocking: If True, blocks until complete and returns tracker.

    Returns:
        UserActionTracker instance. If blocking=True, returns after completion.
    """
    tab_info = session.require_tab(
        label=label,
        url_pattern="",
        open_url=url,
        auto_lock=False,
    )
    if not tab_info:
        tracker = UserActionTracker(session, "", label=label)
        tracker._result = {"status": "failed", "error": "Could not open tab"}
        tracker._completed = True
        return tracker

    tracker = UserActionTracker(
        session=session,
        tab_id=tab_info["id"],
        label=label,
        is_complete=is_complete,
        on_complete=on_complete,
        auto_close=auto_close,
        poll_interval=poll_interval,
        timeout=timeout,
        tip_text=tip_text,
        tip_color=tip_color,
    )
    tracker.start()

    if blocking:
        tracker.wait(timeout=timeout)

    return tracker


def get_active_trackers() -> Dict[str, "UserActionTracker"]:
    """Return all currently active trackers."""
    return dict(_active_trackers)
