"""XMind Turing Machine -- State management for the XMind MCP tool.

Tracks operational states for robust session management and recovery.
Persists state to disk for monitoring and cross-process coordination.
"""

import enum
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class XMState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    NAVIGATING = "navigating"
    VIEWING_HOME = "viewing_home"
    VIEWING_MAP = "viewing_map"
    EDITING = "editing"
    CREATING = "creating"
    EXPORTING = "exporting"
    ERROR = "error"
    RECOVERING = "recovering"


_VALID_TRANSITIONS = {
    XMState.UNINITIALIZED: {XMState.BOOTING},
    XMState.BOOTING: {XMState.IDLE, XMState.ERROR},
    XMState.IDLE: {XMState.NAVIGATING, XMState.VIEWING_HOME, XMState.CREATING, XMState.ERROR},
    XMState.NAVIGATING: {XMState.VIEWING_HOME, XMState.VIEWING_MAP, XMState.ERROR, XMState.RECOVERING},
    XMState.VIEWING_HOME: {XMState.NAVIGATING, XMState.VIEWING_MAP, XMState.CREATING, XMState.ERROR, XMState.RECOVERING},
    XMState.VIEWING_MAP: {XMState.EDITING, XMState.NAVIGATING, XMState.VIEWING_HOME, XMState.EXPORTING, XMState.ERROR, XMState.RECOVERING},
    XMState.EDITING: {XMState.VIEWING_MAP, XMState.NAVIGATING, XMState.ERROR, XMState.RECOVERING},
    XMState.CREATING: {XMState.VIEWING_MAP, XMState.ERROR, XMState.RECOVERING},
    XMState.EXPORTING: {XMState.VIEWING_MAP, XMState.ERROR, XMState.RECOVERING},
    XMState.ERROR: {XMState.RECOVERING, XMState.UNINITIALIZED},
    XMState.RECOVERING: {XMState.IDLE, XMState.VIEWING_HOME, XMState.VIEWING_MAP, XMState.ERROR},
}


class XMindStateMachine:
    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = XMState.UNINITIALIZED
        self._last_url: Optional[str] = None
        self._last_map_title: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery_attempts = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"xmind_{session_name}.json"
        self._load_state()

    @property
    def state(self) -> XMState:
        return self._state

    def transition(self, new_state: XMState, context: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False
            prev = self._state
            self._state = new_state
            ctx = context or {}
            if "url" in ctx:
                self._last_url = ctx["url"]
            if "map_title" in ctx:
                self._last_map_title = ctx["map_title"]
            if "error" in ctx:
                self._error_message = ctx["error"]
            if new_state not in (XMState.ERROR, XMState.RECOVERING):
                self._recovery_count = 0
            self._history.append({
                "from": prev.value, "to": new_state.value,
                "time": time.time(), "context": ctx,
            })
            if len(self._history) > 100:
                self._history = self._history[-50:]
            self._save_state()
            return True

    def set_url(self, url: str):
        self._last_url = url
        self._save_state()

    def can_recover(self) -> bool:
        return self._recovery_count < self._max_recovery_attempts

    def get_recovery_target(self) -> Dict[str, Any]:
        if self._last_url:
            return {"url": self._last_url, "state": self._state.value}
        return {"url": "https://app.xmind.com", "state": "home"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "last_url": self._last_url,
            "last_map_title": self._last_map_title,
            "error": self._error_message,
            "recovery_count": self._recovery_count,
        }

    def _save_state(self):
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            data = self.to_dict()
            data["session_name"] = self.session_name
            data["timestamp"] = time.time()
            self._state_file.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _load_state(self):
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text())
                saved_state = data.get("state", "uninitialized")
                try:
                    self._state = XMState(saved_state)
                except ValueError:
                    self._state = XMState.UNINITIALIZED
                self._last_url = data.get("last_url")
                self._last_map_title = data.get("last_map_title")
                self._error_message = data.get("error")
                self._recovery_count = data.get("recovery_count", 0)
                if self._state in (XMState.NAVIGATING, XMState.CREATING, XMState.EXPORTING):
                    self._state = XMState.ERROR
                    self._error_message = "Interrupted state detected on load"
        except Exception:
            pass

    def reset(self):
        with self._lock:
            self._state = XMState.UNINITIALIZED
            self._last_url = None
            self._last_map_title = None
            self._error_message = None
            self._recovery_count = 0
            self._history.clear()
            self._save_state()


_machines: Dict[str, XMindStateMachine] = {}


def get_machine(session_name: str = "default") -> XMindStateMachine:
    if session_name not in _machines:
        _machines[session_name] = XMindStateMachine(session_name)
    return _machines[session_name]
