"""Bilibili Turing Machine State Management.

Tracks operational states for Bilibili MCP sessions with disk persistence
and automatic recovery.
"""

import json
import time
import enum
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class BiliState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    NAVIGATING = "navigating"
    SEARCHING = "searching"
    WATCHING = "watching"
    ERROR = "error"
    RECOVERING = "recovering"


_VALID_TRANSITIONS = {
    BiliState.UNINITIALIZED: {BiliState.BOOTING},
    BiliState.BOOTING: {BiliState.IDLE, BiliState.ERROR},
    BiliState.IDLE: {BiliState.NAVIGATING, BiliState.ERROR, BiliState.RECOVERING},
    BiliState.NAVIGATING: {BiliState.IDLE, BiliState.SEARCHING, BiliState.WATCHING, BiliState.ERROR},
    BiliState.SEARCHING: {BiliState.NAVIGATING, BiliState.ERROR, BiliState.RECOVERING},
    BiliState.WATCHING: {BiliState.NAVIGATING, BiliState.ERROR, BiliState.RECOVERING},
    BiliState.ERROR: {BiliState.RECOVERING, BiliState.UNINITIALIZED},
    BiliState.RECOVERING: {BiliState.IDLE, BiliState.SEARCHING, BiliState.WATCHING,
                           BiliState.ERROR, BiliState.UNINITIALIZED},
}


class BilibiliStateMachine:
    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = BiliState.UNINITIALIZED
        self._last_url: Optional[str] = None
        self._last_bvid: Optional[str] = None
        self._last_query: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"bili_{session_name}.json"
        self._load_state()

    @property
    def state(self) -> BiliState:
        return self._state

    def transition(self, new_state: BiliState, context: Optional[Dict] = None) -> bool:
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
            if new_state == BiliState.ERROR:
                self._error_message = (context or {}).get("error", "Unknown error")
            elif new_state != BiliState.RECOVERING:
                self._error_message = None
                self._recovery_count = 0
            if new_state == BiliState.RECOVERING:
                self._recovery_count += 1
            self._save_state()
            return True

    def set_url(self, url: str):
        import re
        with self._lock:
            self._last_url = url
            m = re.search(r'/(BV[a-zA-Z0-9]+)', url)
            if m:
                self._last_bvid = m.group(1)
            if 'search' in url:
                m2 = re.search(r'keyword=([^&]+)', url)
                if m2:
                    from urllib.parse import unquote_plus
                    self._last_query = unquote_plus(m2.group(1))
            self._save_state()

    def can_recover(self) -> bool:
        return self._recovery_count < self._max_recovery

    def get_recovery_target(self) -> Dict[str, Any]:
        target = {"url": "https://www.bilibili.com", "state": BiliState.IDLE}
        if self._last_bvid:
            target["url"] = f"https://www.bilibili.com/video/{self._last_bvid}"
            target["state"] = BiliState.WATCHING
        elif self._last_query:
            from urllib.parse import quote_plus
            target["url"] = f"https://search.bilibili.com/all?keyword={quote_plus(self._last_query)}"
            target["state"] = BiliState.SEARCHING
        return target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "last_url": self._last_url,
            "last_bvid": self._last_bvid,
            "last_query": self._last_query,
            "error": self._error_message,
            "recovery_count": self._recovery_count,
        }

    def reset(self):
        with self._lock:
            self._state = BiliState.UNINITIALIZED
            self._last_url = None
            self._last_bvid = None
            self._last_query = None
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
                "last_bvid": self._last_bvid,
                "last_query": self._last_query,
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
            loaded = BiliState(data.get("state", "uninitialized"))
            if loaded in (BiliState.NAVIGATING, BiliState.BOOTING, BiliState.RECOVERING):
                self._state = BiliState.ERROR
                self._error_message = f"Interrupted during {loaded.value}"
            elif loaded == BiliState.ERROR:
                self._state = BiliState.ERROR
                self._error_message = data.get("error", "Previous error")
            else:
                self._state = loaded
            self._last_url = data.get("last_url")
            self._last_bvid = data.get("last_bvid")
            self._last_query = data.get("last_query")
            self._recovery_count = data.get("recovery_count", 0)
            self._history = data.get("history", [])
        except Exception:
            pass


_machines: Dict[str, BilibiliStateMachine] = {}


def get_machine(session_name: str = "default") -> BilibiliStateMachine:
    if session_name not in _machines:
        _machines[session_name] = BilibiliStateMachine(session_name)
    return _machines[session_name]
