"""Lucidchart Turing Machine State Management."""

import json
import time
import enum
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class LucidState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    NAVIGATING = "navigating"
    EDITING = "editing"
    ERROR = "error"
    RECOVERING = "recovering"


_VALID_TRANSITIONS = {
    LucidState.UNINITIALIZED: {LucidState.BOOTING},
    LucidState.BOOTING: {LucidState.IDLE, LucidState.ERROR},
    LucidState.IDLE: {LucidState.NAVIGATING, LucidState.EDITING, LucidState.ERROR, LucidState.RECOVERING},
    LucidState.NAVIGATING: {LucidState.IDLE, LucidState.EDITING, LucidState.ERROR},
    LucidState.EDITING: {LucidState.NAVIGATING, LucidState.IDLE, LucidState.ERROR, LucidState.RECOVERING},
    LucidState.ERROR: {LucidState.RECOVERING, LucidState.UNINITIALIZED},
    LucidState.RECOVERING: {LucidState.IDLE, LucidState.EDITING,
                            LucidState.ERROR, LucidState.UNINITIALIZED},
}


class LucidchartStateMachine:
    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = LucidState.UNINITIALIZED
        self._last_url: Optional[str] = None
        self._last_doc_id: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"lucid_{session_name}.json"
        self._load_state()

    @property
    def state(self) -> LucidState:
        return self._state

    def transition(self, new_state: LucidState, context: Optional[Dict] = None) -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False
            old = self._state
            self._state = new_state
            self._history.append({
                "from": old.value, "to": new_state.value,
                "time": time.time(), "context": context or {},
            })
            if len(self._history) > 50:
                self._history = self._history[-30:]
            if new_state == LucidState.ERROR:
                self._error_message = (context or {}).get("error", "Unknown error")
            elif new_state != LucidState.RECOVERING:
                self._error_message = None
                self._recovery_count = 0
            if new_state == LucidState.RECOVERING:
                self._recovery_count += 1
            self._save_state()
            return True

    def set_url(self, url: str):
        import re
        with self._lock:
            self._last_url = url
            m = re.search(r'/documents/(?:edit|view|embedded)/([a-f0-9-]+)', url)
            if m:
                self._last_doc_id = m.group(1)
            self._save_state()

    def can_recover(self) -> bool:
        return self._recovery_count < self._max_recovery

    def get_recovery_target(self) -> Dict[str, Any]:
        target = {"url": "https://lucid.app/documents", "state": LucidState.IDLE}
        if self._last_doc_id:
            target["url"] = f"https://lucid.app/lucidchart/{self._last_doc_id}/edit"
            target["state"] = LucidState.EDITING
        return target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "last_url": self._last_url,
            "last_doc_id": self._last_doc_id,
            "error": self._error_message,
            "recovery_count": self._recovery_count,
        }

    def reset(self):
        with self._lock:
            self._state = LucidState.UNINITIALIZED
            self._last_url = None
            self._last_doc_id = None
            self._error_message = None
            self._recovery_count = 0
            self._history.clear()
            self._save_state()

    def _save_state(self):
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps({
                "state": self._state.value,
                "last_url": self._last_url,
                "last_doc_id": self._last_doc_id,
                "error": self._error_message,
                "recovery_count": self._recovery_count,
                "history": self._history[-20:],
                "saved_at": time.time(),
            }, indent=2))
        except OSError:
            pass

    def _load_state(self):
        try:
            if not self._state_file.exists():
                return
            data = json.loads(self._state_file.read_text())
            loaded = LucidState(data.get("state", "uninitialized"))
            if loaded in (LucidState.NAVIGATING, LucidState.BOOTING, LucidState.RECOVERING):
                self._state = LucidState.ERROR
                self._error_message = f"Interrupted during {loaded.value}"
            elif loaded == LucidState.ERROR:
                self._state = LucidState.ERROR
                self._error_message = data.get("error", "Previous error")
            else:
                self._state = loaded
            self._last_url = data.get("last_url")
            self._last_doc_id = data.get("last_doc_id")
            self._recovery_count = data.get("recovery_count", 0)
            self._history = data.get("history", [])
        except Exception:
            pass


_machines: Dict[str, LucidchartStateMachine] = {}


def get_machine(session_name: str = "default") -> LucidchartStateMachine:
    if session_name not in _machines:
        _machines[session_name] = LucidchartStateMachine(session_name)
    return _machines[session_name]
