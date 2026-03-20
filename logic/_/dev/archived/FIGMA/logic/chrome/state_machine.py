"""Figma Turing Machine -- State management for the Figma MCP tool."""

import enum
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class FigmaState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    NAVIGATING = "navigating"
    VIEWING_HOME = "viewing_home"
    VIEWING_FILE = "viewing_file"
    EDITING = "editing"
    ERROR = "error"
    RECOVERING = "recovering"


_VALID_TRANSITIONS = {
    FigmaState.UNINITIALIZED: {FigmaState.BOOTING},
    FigmaState.BOOTING: {FigmaState.IDLE, FigmaState.ERROR},
    FigmaState.IDLE: {FigmaState.NAVIGATING, FigmaState.VIEWING_HOME, FigmaState.ERROR},
    FigmaState.NAVIGATING: {FigmaState.VIEWING_HOME, FigmaState.VIEWING_FILE, FigmaState.ERROR, FigmaState.RECOVERING},
    FigmaState.VIEWING_HOME: {FigmaState.NAVIGATING, FigmaState.VIEWING_FILE, FigmaState.ERROR, FigmaState.RECOVERING},
    FigmaState.VIEWING_FILE: {FigmaState.EDITING, FigmaState.NAVIGATING, FigmaState.VIEWING_HOME, FigmaState.ERROR, FigmaState.RECOVERING},
    FigmaState.EDITING: {FigmaState.VIEWING_FILE, FigmaState.NAVIGATING, FigmaState.ERROR, FigmaState.RECOVERING},
    FigmaState.ERROR: {FigmaState.RECOVERING, FigmaState.UNINITIALIZED},
    FigmaState.RECOVERING: {FigmaState.IDLE, FigmaState.VIEWING_HOME, FigmaState.VIEWING_FILE, FigmaState.ERROR},
}


class FigmaStateMachine:
    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = FigmaState.UNINITIALIZED
        self._last_url: Optional[str] = None
        self._last_file_name: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery_attempts = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"figma_{session_name}.json"
        self._load_state()

    @property
    def state(self) -> FigmaState:
        return self._state

    def transition(self, new_state: FigmaState, context: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False
            prev = self._state
            self._state = new_state
            ctx = context or {}
            if "url" in ctx:
                self._last_url = ctx["url"]
            if "file_name" in ctx:
                self._last_file_name = ctx["file_name"]
            if "error" in ctx:
                self._error_message = ctx["error"]
            if new_state not in (FigmaState.ERROR, FigmaState.RECOVERING):
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
        return {"url": "https://www.figma.com/files", "state": "home"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "last_url": self._last_url,
            "last_file_name": self._last_file_name,
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
                    self._state = FigmaState(saved_state)
                except ValueError:
                    self._state = FigmaState.UNINITIALIZED
                self._last_url = data.get("last_url")
                self._last_file_name = data.get("last_file_name")
                self._error_message = data.get("error")
                self._recovery_count = data.get("recovery_count", 0)
                if self._state in (FigmaState.NAVIGATING, FigmaState.EDITING):
                    self._state = FigmaState.ERROR
                    self._error_message = "Interrupted state detected on load"
        except Exception:
            pass

    def reset(self):
        with self._lock:
            self._state = FigmaState.UNINITIALIZED
            self._last_url = None
            self._last_file_name = None
            self._error_message = None
            self._recovery_count = 0
            self._history.clear()
            self._save_state()


_machines: Dict[str, FigmaStateMachine] = {}


def get_machine(session_name: str = "default") -> FigmaStateMachine:
    if session_name not in _machines:
        _machines[session_name] = FigmaStateMachine(session_name)
    return _machines[session_name]
