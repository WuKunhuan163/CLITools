"""Session management for OPENCLAW.

Each session represents one task conversation with the remote agent.
Sessions are persisted to disk so they survive restarts.

Storage layout::

    data/sessions/
        {session_id}.json      -- state (title, messages, status)
        {session_id}/
            logs/
                s1.log.md      -- per-step operation log
                s2.log.md
"""
import json
import shutil
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

DEFAULT_LOG_LIMIT = 1024


@dataclass
class Message:
    role: str  # "user", "assistant", "system", "feedback"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    id: str
    title: str
    created_at: float
    updated_at: float
    messages: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "active"  # active, completed, error

    def add_message(self, role: str, content: str, **metadata):
        msg = Message(role=role, content=content, metadata=metadata)
        self.messages.append(asdict(msg))
        self.updated_at = time.time()

    def get_display_title(self) -> str:
        if self.title:
            return self.title
        return f"Session {self.id[:8]}"


class SessionLog:
    """Non-blocking per-operation log writer for a session step.

    Logs are stored as `data/sessions/{session_id}/logs/s{step}.log.md`.
    All file writes run in a background thread to avoid blocking the UI.
    """

    def __init__(self, session_dir: Path, session_id: str, step: int):
        self._log_dir = session_dir / session_id / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self.filename = f"s{step}.log.md"
        self.path = self._log_dir / self.filename
        self.ref = f"{session_id}/logs/{self.filename}"
        self._queue: list = []
        self._lock = threading.Lock()
        self._flushing = False

    def _bg_write(self, text: str):
        """Enqueue text and flush in order via a background thread."""
        with self._lock:
            self._queue.append(text)
            if self._flushing:
                return
            self._flushing = True

        def _drain():
            while True:
                with self._lock:
                    if not self._queue:
                        self._flushing = False
                        return
                    batch = self._queue[:]
                    self._queue.clear()
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write("".join(batch))

        threading.Thread(target=_drain, daemon=True).start()

    def write(self, label: str, data):
        """Append a labelled entry."""
        ts = time.strftime("%H:%M:%S")
        parts = [f"## {label} [{ts}]\n\n"]
        if isinstance(data, (dict, list)):
            parts.append("```json\n")
            parts.append(json.dumps(data, ensure_ascii=False, indent=2, default=str))
            parts.append("\n```\n\n")
        else:
            parts.append(str(data))
            parts.append("\n\n")
        self._bg_write("".join(parts))

    def write_messages(self, messages: list):
        """Write the full message array being sent to the LLM."""
        ts = time.strftime("%H:%M:%S")
        parts = [f"## Messages ({len(messages)}) [{ts}]\n\n"]
        for i, m in enumerate(messages):
            role = m.get("role", "?")
            content = m.get("content", "")
            parts.append(f"### [{i}] {role} ({len(content)} chars)\n\n")
            parts.append(content)
            parts.append("\n\n")
        self._bg_write("".join(parts))

    @staticmethod
    def rotate(session_dir: Path, session_id: str, max_logs: int = DEFAULT_LOG_LIMIT):
        """Keep only the newest *max_logs* log files for a session.

        When the limit is reached, deletes half of the oldest logs at once
        (same strategy as ``GitPersistenceManager._cleanup_old_caches``).
        """
        log_dir = session_dir / session_id / "logs"
        if not log_dir.exists():
            return 0
        logs = sorted(log_dir.glob("*.log.md"), key=lambda p: p.stat().st_mtime)
        if len(logs) < max_logs:
            return 0
        to_delete = len(logs) // 2
        removed = 0
        for i in range(to_delete):
            try:
                logs[i].unlink()
                removed += 1
            except OSError:
                pass
        return removed


class SessionManager:
    """Manages OPENCLAW sessions with persistence."""

    def __init__(self, data_dir: Path, log_limit: int = DEFAULT_LOG_LIMIT):
        self.data_dir = data_dir / "sessions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_limit = log_limit
        self._sessions: Dict[str, Session] = {}
        self._load_sessions()

    def _session_file(self, session_id: str) -> Path:
        return self.data_dir / f"{session_id}.json"

    def _load_sessions(self):
        """Load all sessions from disk."""
        for f in sorted(self.data_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                s = Session(
                    id=data["id"],
                    title=data.get("title", ""),
                    created_at=data["created_at"],
                    updated_at=data.get("updated_at", data["created_at"]),
                    messages=data.get("messages", []),
                    status=data.get("status", "active"),
                )
                self._sessions[s.id] = s
            except Exception:
                continue

    def _save_session(self, session: Session):
        """Save a session to disk."""
        path = self._session_file(session.id)
        data = {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": session.messages,
            "status": session.status,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create_session(self, title: str = "") -> Session:
        """Create a new session."""
        now = time.time()
        session = Session(
            id=str(uuid.uuid4())[:8],
            title=title,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session.id] = session
        self._save_session(session)
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update_title(self, session_id: str, title: str):
        session = self._sessions.get(session_id)
        if session:
            session.title = title
            self._save_session(session)

    def add_message(self, session_id: str, role: str, content: str, **metadata):
        session = self._sessions.get(session_id)
        if session:
            session.add_message(role, content, **metadata)
            self._save_session(session)

    def complete_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.status = "completed"
            self._save_session(session)

    def create_log(self, session_id: str, step: int) -> SessionLog:
        """Create an operation log for a session step, with auto-rotation."""
        log = SessionLog(self.data_dir, session_id, step)
        SessionLog.rotate(self.data_dir, session_id, self.log_limit)
        return log

    def list_sessions(self) -> List[Session]:
        """Return sessions sorted by most recent first."""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )

    def delete_session(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            path = self._session_file(session_id)
            if path.exists():
                path.unlink()
            session_dir = self.data_dir / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
