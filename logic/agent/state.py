"""Agent session state management.

Tracks what the agent has discovered and done — short-term operational memory.
State is serialized into each turn's context to give the LLM awareness of:
1. What tools/files are known
2. What succeeded/failed recently
3. What to do next
"""
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


SESSIONS_DIR_NAME = "session"


@dataclass
class AgentEnvironment:
    """Short-term memory for an agent session."""

    visible_tools: Dict[str, str] = field(default_factory=dict)
    visible_skills: Dict[str, str] = field(default_factory=dict)
    last_results: List[Dict[str, Any]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)

    def observe_tool(self, name: str, desc: str):
        self.visible_tools[name] = desc

    def record_result(self, cmd: str, ok: bool, preview: str = ""):
        self.last_results.append({
            "cmd": cmd, "ok": ok, "preview": preview[:300],
            "ts": time.time(),
        })
        if len(self.last_results) > 8:
            self.last_results = self.last_results[-8:]

    def record_error(self, msg: str):
        self.errors.append(msg)
        if len(self.errors) > 5:
            self.errors = self.errors[-5:]

    def record_lesson(self, lesson: str):
        self.lessons.append(lesson)
        if len(self.lessons) > 5:
            self.lessons = self.lessons[-5:]

    def serialize(self) -> str:
        """Serialize into a context block for the next turn."""
        parts = []
        if self.visible_tools:
            lines = ["[Discovered tools]"]
            for name, desc in self.visible_tools.items():
                lines.append(f"  {name}: {desc}")
            parts.append("\n".join(lines))

        if self.last_results:
            lines = ["[Recent results]"]
            for r in self.last_results[-5:]:
                status = "OK" if r["ok"] else "FAILED"
                lines.append(f"  [{status}] {r['cmd']}")
                if r["preview"]:
                    lines.append(f"    {r['preview'][:120]}")
            parts.append("\n".join(lines))

            awareness = self._generate_awareness()
            if awareness:
                parts.append(awareness)

        if self.errors:
            parts.append("[Errors]\n" + "\n".join(f"  - {e}" for e in self.errors))
        if self.lessons:
            parts.append("[Lessons]\n" + "\n".join(f"  - {l}" for l in self.lessons))
        return "\n\n".join(parts)

    def _generate_awareness(self) -> str:
        """Generate next-step awareness cues based on current state."""
        cues = []
        if not self.last_results:
            return ""

        last = self.last_results[-1]
        failed_count = sum(1 for r in self.last_results if not r["ok"])

        if failed_count >= 3:
            cues.append(
                "WARNING: Multiple consecutive failures. "
                "Try a completely different strategy or ask_user for help.")

        if last["cmd"].startswith("TOOL --search"):
            cues.append("Search completed. Execute the found command.")

        if not last["ok"]:
            cues.append("Last command failed. Check docs or try a different approach.")
            if self.errors:
                cues.append("Active errors exist. Fix them before proceeding.")

        if not cues:
            return ""
        return "[Next-step awareness]\n" + "\n".join(f"  - {c}" for c in cues)


def _generate_session_id() -> str:
    """Generate a session ID: YYYYMMDD-HHMMSS-<6hex>."""
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    short_hash = uuid.uuid4().hex[:6]
    return f"{ts}-{short_hash}"


@dataclass
class AgentSession:
    """Persistent state for one agent session."""

    id: str = field(default_factory=_generate_session_id)
    tool_name: str = ""
    codebase_root: str = ""
    status: str = "idle"
    message_count: int = 0
    environment: AgentEnvironment = field(default_factory=AgentEnvironment)
    created_at: float = field(default_factory=time.time)
    provider_name: str = ""
    tier: int = 1
    mode: str = "agent"
    initial_prompt: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "codebase_root": self.codebase_root,
            "status": self.status,
            "message_count": self.message_count,
            "created_at": self.created_at,
            "provider_name": self.provider_name,
            "tier": self.tier,
            "mode": self.mode,
            "initial_prompt": self.initial_prompt[:500],
        }


def get_sessions_dir(project_root: str) -> Path:
    """Return the directory where agent sessions are stored."""
    d = Path(project_root) / "data" / SESSIONS_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_session(session: AgentSession, project_root: str):
    """Persist session state to disk."""
    d = get_sessions_dir(project_root)
    path = d / f"{session.id}.json"
    path.write_text(json.dumps(session.to_dict(), indent=2))


def load_session(session_id: str, project_root: str) -> Optional[AgentSession]:
    """Load a session from disk."""
    d = get_sessions_dir(project_root)
    path = d / f"{session_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        s = AgentSession(**{k: v for k, v in data.items()
                           if k in AgentSession.__dataclass_fields__})
        return s
    except Exception:
        return None


def list_sessions(project_root: str) -> List[dict]:
    """List all saved agent sessions."""
    d = get_sessions_dir(project_root)
    sessions = []
    for f in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            sessions.append(json.loads(f.read_text()))
        except Exception:
            continue
    return sessions
