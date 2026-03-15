"""LLM Brain — pluggable memory and reasoning layer.

The Brain manages an agent's cognitive state across turns:
- **Working memory**: Current task context (AgentEnvironment)
- **Short-term memory**: Recent conversation (SessionContext)
- **Long-term memory**: Persistent summaries, lessons, discoveries

This is the base implementation. Openclaw extends it with self-evolving
capabilities by overriding create_memory() and recall().

Architecture:
    Brain
    ├── MemoryStore (file-backed JSON)
    │   ├── session_summaries: Dict[session_id, summary_text]
    │   ├── tool_knowledge: Dict[tool_name, knowledge_text]
    │   └── lessons: List[str]
    ├── SessionContext (short-term, per-session)
    └── AgentEnvironment (working memory, per-session)
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Memory:
    """A single memory unit with metadata."""
    content: str
    source: str = ""
    created_at: float = field(default_factory=time.time)
    relevance: float = 1.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at,
            "relevance": self.relevance,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Memory":
        return cls(
            content=d["content"],
            source=d.get("source", ""),
            created_at=d.get("created_at", 0),
            relevance=d.get("relevance", 1.0),
            tags=d.get("tags", []),
        )


class MemoryStore:
    """File-backed persistent memory store."""

    def __init__(self, store_path: Path):
        self._path = store_path
        self._data: Dict[str, Any] = {
            "session_summaries": {},
            "tool_knowledge": {},
            "lessons": [],
            "codebase_context": {},
        }
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    self._data.update(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def save_session_summary(self, session_id: str, summary: str):
        self._data["session_summaries"][session_id] = {
            "summary": summary,
            "timestamp": time.time(),
        }
        self._save()

    def get_session_summary(self, session_id: str) -> Optional[str]:
        entry = self._data["session_summaries"].get(session_id)
        return entry["summary"] if entry else None

    def save_tool_knowledge(self, tool_name: str, knowledge: str):
        self._data["tool_knowledge"][tool_name] = {
            "knowledge": knowledge,
            "timestamp": time.time(),
        }
        self._save()

    def get_tool_knowledge(self, tool_name: str) -> Optional[str]:
        entry = self._data["tool_knowledge"].get(tool_name)
        return entry["knowledge"] if entry else None

    def add_lesson(self, lesson: str):
        self._data["lessons"].append({
            "lesson": lesson,
            "timestamp": time.time(),
        })
        if len(self._data["lessons"]) > 50:
            self._data["lessons"] = self._data["lessons"][-50:]
        self._save()

    def get_lessons(self, limit: int = 10) -> List[str]:
        return [l["lesson"] for l in self._data["lessons"][-limit:]]

    def save_codebase_context(self, codebase_root: str, context: Dict[str, Any]):
        self._data["codebase_context"][codebase_root] = {
            "context": context,
            "timestamp": time.time(),
        }
        self._save()

    def get_codebase_context(self, codebase_root: str) -> Optional[Dict[str, Any]]:
        entry = self._data["codebase_context"].get(codebase_root)
        return entry["context"] if entry else None

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class Brain:
    """Base LLM Brain — manages memory across sessions.

    This is the minimal viable brain. Openclaw extends it with:
    - Self-reflection loops (evaluate own performance)
    - Autonomous learning (extract patterns from failures)
    - Goal decomposition (break complex tasks into subtasks)

    The Brain is an interface layer: all methods can be overridden.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
        self._data_dir = data_dir
        self._store = MemoryStore(data_dir / "brain_memory.json")
        self._on_memory_cb: Optional[Callable] = None

    @property
    def store(self) -> MemoryStore:
        return self._store

    def on_memory_event(self, cb: Callable):
        """Register callback for memory creation events."""
        self._on_memory_cb = cb

    def _emit_memory(self, event_type: str, **kwargs):
        if self._on_memory_cb:
            self._on_memory_cb({"type": event_type, **kwargs})

    # ── Memory Creation ──

    def create_memory(self, content: str, source: str = "",
                      tags: Optional[List[str]] = None) -> Memory:
        """Create a new memory. Override in Openclaw for self-evolving behavior."""
        mem = Memory(content=content, source=source, tags=tags or [])
        self._emit_memory("memory_created", memory=mem.to_dict())
        return mem

    def learn_from_result(self, command: str, ok: bool, output: str):
        """Extract a lesson from a command execution result.

        Override in Openclaw to implement autonomous learning patterns.
        """
        if not ok and output:
            lesson = f"Command '{command[:60]}' failed: {output[:200]}"
            self._store.add_lesson(lesson)
            self._emit_memory("lesson_learned", lesson=lesson)

    def learn_from_tool(self, tool_name: str, doc_content: str):
        """Store discovered tool knowledge."""
        self._store.save_tool_knowledge(tool_name, doc_content[:2000])

    # ── Memory Recall ──

    def recall(self, query: str, context: Optional[str] = None,
               limit: int = 5) -> List[Memory]:
        """Recall relevant memories for a given query.

        Base implementation returns recent lessons. Openclaw overrides
        with semantic similarity search over the memory store.
        """
        lessons = self._store.get_lessons(limit)
        return [Memory(content=l, source="lesson") for l in lessons]

    def get_session_bootstrap(self, session_id: str,
                              codebase_root: Optional[str] = None) -> str:
        """Generate bootstrap context for a new or resumed session.

        Includes: working directory, relevant lessons, tool knowledge, codebase context.
        """
        parts = []

        if codebase_root:
            parts.append(
                f"[Working directory]\n"
                f"You are working in: {codebase_root}\n"
                f"All relative file paths resolve against this directory. "
                f"Use relative paths (e.g. 'main.py', not '{codebase_root}/main.py').\n"
                f"When you use exec, read_file, write_file, or search, they operate in this directory.")

        lessons = self._store.get_lessons(5)
        if lessons:
            parts.append("[Previous lessons]\n" + "\n".join(f"- {l}" for l in lessons))

        if codebase_root:
            ctx = self._store.get_codebase_context(codebase_root)
            if ctx:
                parts.append(f"[Codebase: {codebase_root}]\n{ctx.get('summary', '')}")

        prev_summary = self._store.get_session_summary(session_id)
        if prev_summary:
            parts.append(f"[Session context]\n{prev_summary}")

        return "\n\n".join(parts) if parts else ""

    # ── Session Lifecycle ──

    def on_session_end(self, session_id: str, summary: str):
        """Called when a session ends. Persists the session summary."""
        self._store.save_session_summary(session_id, summary)

    def on_codebase_discovered(self, codebase_root: str, file_tree: List[str]):
        """Called when a codebase is first explored. Stores structure."""
        self._store.save_codebase_context(codebase_root, {
            "summary": f"{len(file_tree)} files",
            "key_files": file_tree[:30],
            "timestamp": time.time(),
        })

    # ── Introspection ──

    def get_state(self) -> Dict[str, Any]:
        return {
            "data_dir": str(self._data_dir),
            "lessons_count": len(self._store.get_lessons(100)),
            "tools_known": list(self._store._data.get("tool_knowledge", {}).keys()),
            "sessions_summarized": list(self._store._data.get("session_summaries", {}).keys()),
        }
