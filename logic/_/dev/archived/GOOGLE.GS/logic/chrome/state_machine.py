"""Google Scholar Turing machine state management.

Tracks the tool's operational state for robustness and recovery:
- UNINITIALIZED → BOOTING → IDLE
- IDLE → SEARCHING / VIEWING_PAPER / VIEWING_PROFILE / NAVIGATING
- Any → ERROR → RECOVERING → (target state)
"""

import enum
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_STATE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "state"


class GSState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    SEARCHING = "searching"
    VIEWING_PAPER = "viewing_paper"
    VIEWING_PROFILE = "viewing_profile"
    VIEWING_CITATIONS = "viewing_citations"
    NAVIGATING = "navigating"
    ERROR = "error"
    RECOVERING = "recovering"


_VALID_TRANSITIONS = {
    GSState.UNINITIALIZED: {GSState.BOOTING},
    GSState.BOOTING: {GSState.IDLE, GSState.ERROR},
    GSState.IDLE: {GSState.SEARCHING, GSState.VIEWING_PAPER,
                   GSState.VIEWING_PROFILE, GSState.VIEWING_CITATIONS,
                   GSState.NAVIGATING, GSState.ERROR},
    GSState.SEARCHING: {GSState.IDLE, GSState.VIEWING_PAPER, GSState.ERROR},
    GSState.VIEWING_PAPER: {GSState.IDLE, GSState.SEARCHING,
                            GSState.VIEWING_CITATIONS, GSState.VIEWING_PROFILE,
                            GSState.NAVIGATING, GSState.ERROR},
    GSState.VIEWING_PROFILE: {GSState.IDLE, GSState.SEARCHING,
                              GSState.VIEWING_PAPER, GSState.ERROR},
    GSState.VIEWING_CITATIONS: {GSState.IDLE, GSState.VIEWING_PAPER,
                                GSState.SEARCHING, GSState.ERROR},
    GSState.NAVIGATING: {GSState.IDLE, GSState.SEARCHING, GSState.VIEWING_PAPER,
                         GSState.VIEWING_PROFILE, GSState.ERROR},
    GSState.ERROR: {GSState.RECOVERING, GSState.IDLE, GSState.UNINITIALIZED},
    GSState.RECOVERING: {GSState.IDLE, GSState.ERROR},
}

_machine_cache: Dict[str, "GSStateMachine"] = {}


def get_machine(session_name: str = "default") -> "GSStateMachine":
    if session_name not in _machine_cache:
        _machine_cache[session_name] = GSStateMachine(session_name)
    return _machine_cache[session_name]


class GSStateMachine:
    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = GSState.UNINITIALIZED
        self._last_url: Optional[str] = None
        self._last_query: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"gs_{session_name}.json"
        self._load_state()

    @property
    def state(self) -> GSState:
        return self._state

    def transition(self, new_state: GSState,
                   context: Optional[Dict] = None) -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False
            old = self._state
            self._state = new_state
            entry = {
                "from": old.value, "to": new_state.value,
                "time": time.time(),
            }
            if context:
                entry["context"] = context
            self._history.append(entry)
            if len(self._history) > 100:
                self._history = self._history[-50:]
            if new_state == GSState.ERROR:
                self._error_message = (context or {}).get("error", "")
            elif new_state == GSState.RECOVERING:
                self._recovery_count += 1
            elif new_state == GSState.IDLE:
                self._recovery_count = 0
                self._error_message = None
            self._save_state()
            return True

    def set_url(self, url: str):
        self._last_url = url
        if "scholar.google" in url and "q=" in url:
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            self._last_query = qs.get("q", [""])[0]
        self._save_state()

    def can_recover(self) -> bool:
        return self._recovery_count < self._max_recovery

    def get_recovery_target(self) -> Dict[str, Any]:
        if self._last_query:
            return {"url": f"https://scholar.google.com/scholar?q={self._last_query}",
                    "state": GSState.SEARCHING}
        return {"url": "https://scholar.google.com/",
                "state": GSState.IDLE}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "session_name": self.session_name,
            "last_url": self._last_url,
            "last_query": self._last_query,
            "error": self._error_message,
            "recovery_count": self._recovery_count,
            "history_len": len(self._history),
        }

    def _save_state(self):
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._state_file, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
        except OSError:
            pass

    def _load_state(self):
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file) as f:
                data = json.load(f)
            self._last_url = data.get("last_url")
            self._last_query = data.get("last_query")
            self._recovery_count = data.get("recovery_count", 0)
            saved_state = data.get("state", "uninitialized")
            try:
                self._state = GSState(saved_state)
            except ValueError:
                self._state = GSState.UNINITIALIZED
        except Exception:
            pass
