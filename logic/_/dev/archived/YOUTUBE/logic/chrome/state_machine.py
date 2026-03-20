"""YouTube Turing Machine State Management.

Provides robust state tracking and recovery for YouTube MCP operations.
Each session maintains a state machine that:
  - Tracks current operational state (IDLE, SEARCHING, WATCHING, etc.)
  - Persists state to disk for crash recovery
  - Detects tab closure and triggers automatic recovery
  - Restores the last known page/state after recovery

Multiple state machines can coexist (one per session). The main state
machine manages the session lifecycle; a sub-machine handles transcript
panel operations.
"""

import json
import time
import enum
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class YTState(str, enum.Enum):
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    IDLE = "idle"
    NAVIGATING = "navigating"
    SEARCHING = "searching"
    WATCHING = "watching"
    TRANSCRIPT = "transcript"
    ERROR = "error"
    RECOVERING = "recovering"


class TranscriptState(str, enum.Enum):
    CLOSED = "closed"
    OPENING = "opening"
    EXPANDED = "expanded"
    READING = "reading"
    DONE = "done"
    ERROR = "error"


_VALID_TRANSITIONS = {
    YTState.UNINITIALIZED: {YTState.BOOTING},
    YTState.BOOTING: {YTState.IDLE, YTState.ERROR},
    YTState.IDLE: {YTState.NAVIGATING, YTState.ERROR, YTState.RECOVERING},
    YTState.NAVIGATING: {YTState.IDLE, YTState.SEARCHING, YTState.WATCHING, YTState.ERROR},
    YTState.SEARCHING: {YTState.NAVIGATING, YTState.ERROR, YTState.RECOVERING},
    YTState.WATCHING: {YTState.NAVIGATING, YTState.TRANSCRIPT, YTState.ERROR, YTState.RECOVERING},
    YTState.TRANSCRIPT: {YTState.WATCHING, YTState.ERROR, YTState.RECOVERING},
    YTState.ERROR: {YTState.RECOVERING, YTState.UNINITIALIZED},
    YTState.RECOVERING: {YTState.IDLE, YTState.SEARCHING, YTState.WATCHING, YTState.ERROR, YTState.UNINITIALIZED},
}


class YouTubeStateMachine:
    """Main state machine for a YouTube MCP session."""

    def __init__(self, session_name: str = "default"):
        self.session_name = session_name
        self._state = YTState.UNINITIALIZED
        self._transcript_state = TranscriptState.CLOSED
        self._last_url: Optional[str] = None
        self._last_video_id: Optional[str] = None
        self._last_search_query: Optional[str] = None
        self._error_message: Optional[str] = None
        self._recovery_count = 0
        self._max_recovery_attempts = 3
        self._lock = threading.Lock()
        self._history: list = []
        self._state_file = _STATE_DIR / f"{session_name}.json"

        self._load_state()

    @property
    def state(self) -> YTState:
        return self._state

    @property
    def transcript_state(self) -> TranscriptState:
        return self._transcript_state

    def transition(self, new_state: YTState, context: Optional[Dict[str, Any]] = None) -> bool:
        """Attempt a state transition. Returns True if valid."""
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False

            old = self._state
            self._state = new_state
            self._history.append({
                "from": old.value,
                "to": new_state.value,
                "time": time.time(),
                "context": context or {},
            })

            if len(self._history) > 50:
                self._history = self._history[-30:]

            if new_state == YTState.ERROR:
                self._error_message = (context or {}).get("error", "Unknown error")
            elif new_state != YTState.RECOVERING:
                self._error_message = None
                self._recovery_count = 0

            if new_state == YTState.RECOVERING:
                self._recovery_count += 1

            self._save_state()
            return True

    def set_transcript_state(self, new_state: TranscriptState):
        with self._lock:
            self._transcript_state = new_state
            self._save_state()

    def set_url(self, url: str):
        with self._lock:
            self._last_url = url
            if "/watch" in url:
                import re
                m = re.search(r'[?&]v=([^&]+)', url)
                if m:
                    self._last_video_id = m.group(1)
            elif "/results" in url:
                import re
                m = re.search(r'search_query=([^&]+)', url)
                if m:
                    from urllib.parse import unquote_plus
                    self._last_search_query = unquote_plus(m.group(1))
            self._save_state()

    def can_recover(self) -> bool:
        return self._recovery_count < self._max_recovery_attempts

    def get_recovery_target(self) -> Dict[str, Any]:
        """Determine where to navigate after recovery, based on last known state."""
        last_good = None
        for entry in reversed(self._history):
            if entry["to"] not in (YTState.ERROR.value, YTState.RECOVERING.value):
                last_good = entry
                break

        target = {"url": "https://www.youtube.com", "state": YTState.IDLE}

        if not last_good:
            return target

        last_state = last_good["to"]

        if last_state == YTState.WATCHING.value and self._last_video_id:
            target["url"] = f"https://www.youtube.com/watch?v={self._last_video_id}"
            target["state"] = YTState.WATCHING
        elif last_state == YTState.SEARCHING.value and self._last_search_query:
            from urllib.parse import quote_plus
            target["url"] = f"https://www.youtube.com/results?search_query={quote_plus(self._last_search_query)}"
            target["state"] = YTState.SEARCHING
        elif last_state == YTState.TRANSCRIPT.value and self._last_video_id:
            target["url"] = f"https://www.youtube.com/watch?v={self._last_video_id}"
            target["state"] = YTState.WATCHING
            target["restore_transcript"] = True

        return target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_name": self.session_name,
            "state": self._state.value,
            "transcript_state": self._transcript_state.value,
            "last_url": self._last_url,
            "last_video_id": self._last_video_id,
            "last_search_query": self._last_search_query,
            "error": self._error_message,
            "recovery_count": self._recovery_count,
            "history_length": len(self._history),
        }

    def _save_state(self):
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "state": self._state.value,
                "transcript_state": self._transcript_state.value,
                "last_url": self._last_url,
                "last_video_id": self._last_video_id,
                "last_search_query": self._last_search_query,
                "error_message": self._error_message,
                "recovery_count": self._recovery_count,
                "history": self._history[-20:],
                "saved_at": time.time(),
            }
            self._state_file.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _load_state(self):
        try:
            if not self._state_file.exists():
                return
            data = json.loads(self._state_file.read_text())
            saved_state = data.get("state", "uninitialized")

            try:
                loaded = YTState(saved_state)
            except ValueError:
                return

            if loaded in (YTState.NAVIGATING, YTState.BOOTING, YTState.RECOVERING):
                self._state = YTState.ERROR
                self._error_message = f"Interrupted during {saved_state}"
            elif loaded == YTState.ERROR:
                self._state = YTState.ERROR
                self._error_message = data.get("error_message", "Previous error")
            else:
                self._state = loaded

            try:
                self._transcript_state = TranscriptState(data.get("transcript_state", "closed"))
            except ValueError:
                self._transcript_state = TranscriptState.CLOSED

            self._last_url = data.get("last_url")
            self._last_video_id = data.get("last_video_id")
            self._last_search_query = data.get("last_search_query")
            self._recovery_count = data.get("recovery_count", 0)
            self._history = data.get("history", [])
        except (OSError, json.JSONDecodeError):
            pass

    def reset(self):
        with self._lock:
            self._state = YTState.UNINITIALIZED
            self._transcript_state = TranscriptState.CLOSED
            self._last_url = None
            self._last_video_id = None
            self._last_search_query = None
            self._error_message = None
            self._recovery_count = 0
            self._history.clear()
            self._save_state()


_machines: Dict[str, YouTubeStateMachine] = {}


def get_machine(session_name: str = "default") -> YouTubeStateMachine:
    if session_name not in _machines:
        _machines[session_name] = YouTubeStateMachine(session_name)
    return _machines[session_name]
