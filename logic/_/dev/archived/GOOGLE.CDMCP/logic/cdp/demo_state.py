"""CDMCP Demo Turing Machine — State management for the continuous demo.

Tracks demo lifecycle: booting, running interactions, waiting for relock,
countdown pauses, error recovery. Persists to disk for monitoring.
"""

import enum
import json
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_STATE_DIR = _TOOL_DIR / "data" / "state"


class DemoState(str, enum.Enum):
    IDLE = "idle"
    BOOTING = "booting"
    SELECTING_CONTACT = "selecting_contact"
    TYPING_MESSAGE = "typing_message"
    SENDING = "sending"
    VERIFYING = "verifying"
    COUNTDOWN = "countdown"
    WAITING_RELOCK = "waiting_relock"
    RECOVERING = "recovering"
    ERROR = "error"
    STOPPED = "stopped"


_VALID_TRANSITIONS = {
    DemoState.IDLE: {DemoState.BOOTING, DemoState.STOPPED},
    DemoState.BOOTING: {DemoState.SELECTING_CONTACT, DemoState.ERROR},
    DemoState.SELECTING_CONTACT: {DemoState.TYPING_MESSAGE, DemoState.ERROR, DemoState.RECOVERING, DemoState.WAITING_RELOCK},
    DemoState.TYPING_MESSAGE: {DemoState.SENDING, DemoState.ERROR, DemoState.RECOVERING},
    DemoState.SENDING: {DemoState.VERIFYING, DemoState.ERROR, DemoState.RECOVERING},
    DemoState.VERIFYING: {DemoState.COUNTDOWN, DemoState.SELECTING_CONTACT, DemoState.ERROR},
    DemoState.COUNTDOWN: {DemoState.SELECTING_CONTACT, DemoState.WAITING_RELOCK, DemoState.ERROR, DemoState.STOPPED},
    DemoState.WAITING_RELOCK: {DemoState.SELECTING_CONTACT, DemoState.COUNTDOWN, DemoState.ERROR, DemoState.STOPPED},
    DemoState.RECOVERING: {DemoState.SELECTING_CONTACT, DemoState.ERROR, DemoState.STOPPED},
    DemoState.ERROR: {DemoState.RECOVERING, DemoState.IDLE, DemoState.STOPPED},
    DemoState.STOPPED: {DemoState.IDLE, DemoState.BOOTING},
}


class DemoStateMachine:
    def __init__(self):
        self._state = DemoState.IDLE
        self._lock = threading.Lock()
        self._current_contact: Optional[str] = None
        self._current_message: Optional[str] = None
        self._messages_sent = 0
        self._errors = 0
        self._countdown_remaining = 0
        self._relock_remaining = 0.0
        self._state_file = _STATE_DIR / "demo.json"
        self._last_changed = time.time()

    @property
    def state(self) -> DemoState:
        return self._state

    def transition(self, new_state: DemoState, context: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            allowed = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                return False
            self._state = new_state
            self._last_changed = time.time()
            ctx = context or {}
            if "contact" in ctx:
                self._current_contact = ctx["contact"]
            if "message" in ctx:
                self._current_message = ctx["message"]
            if new_state == DemoState.VERIFYING:
                self._messages_sent += 1
            if new_state == DemoState.ERROR:
                self._errors += 1
            self._save()
            return True

    def set_countdown(self, remaining: int):
        self._countdown_remaining = remaining
        self._save()

    def set_relock_remaining(self, remaining: float):
        self._relock_remaining = remaining
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "contact": self._current_contact,
            "message": (self._current_message or "")[:50],
            "messages_sent": self._messages_sent,
            "errors": self._errors,
            "countdown_remaining": self._countdown_remaining,
            "relock_remaining": round(self._relock_remaining, 1),
            "last_changed": self._last_changed,
        }

    def _save(self):
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(self.to_dict(), indent=2))
        except OSError:
            pass

    def reset(self):
        with self._lock:
            self._state = DemoState.IDLE
            self._current_contact = None
            self._current_message = None
            self._messages_sent = 0
            self._errors = 0
            self._countdown_remaining = 0
            self._relock_remaining = 0.0
            self._save()


_machine: Optional[DemoStateMachine] = None


def get_demo_machine() -> DemoStateMachine:
    global _machine
    if _machine is None:
        _machine = DemoStateMachine()
    return _machine
