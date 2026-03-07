"""Session management for OPENCLAW.

Each session represents one task conversation with the remote agent.
Sessions are persisted to disk so they survive restarts.
"""
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


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


class SessionManager:
    """Manages OPENCLAW sessions with persistence."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "sessions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
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
