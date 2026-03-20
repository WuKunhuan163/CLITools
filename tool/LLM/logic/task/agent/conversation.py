"""GUI-agnostic conversation manager for LLM agent sessions.

Provides a stateful middle layer between any GUI (HTML, tkinter, CLI)
and the LLM provider. All GUIs call the same methods; events are
emitted via a callback for rendering.

Supports system context feeds that package runtime state alongside
user messages, providing the agent with short-term memory. As tools
are discovered and lessons learned, the context feed evolves.

Usage:
    from tool.LLM.logic.task.agent.conversation import ConversationManager

    mgr = ConversationManager(provider_name="zhipu-glm-4.7")
    mgr.on_event(lambda evt: push_to_gui(evt))

import logging as _logging
_log = _logging.getLogger(__name__)

    mgr.new_session("s1")
    mgr.send_message("s1", "Explain SSE in 3 sentences")
    # Events emitted: user → thinking → text → complete

    # With system context feed:
    mgr.send_message("s1", "Fix the BILIBILI bug",
                     context_feed={"hint": "BILIBILI search returns empty results"})
"""
import json
import threading
import time
import uuid
import platform
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

from tool.LLM.logic.session_context import SessionContext

_LLM_TOOL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..')
try:
    from interface.hooks import HooksEngine
    _HOOKS_AVAILABLE = True
except ImportError:
    _HOOKS_AVAILABLE = False


@dataclass
class AgentEnvironment:
    """Tracks what the agent has discovered — short-term memory.

    Mirrors OPENCLAW's AgentEnvironment. As the agent explores (exec,
    search, read), observations accumulate here and get serialized
    into the next turn's context.
    """
    visible_tools: Dict[str, str] = field(default_factory=dict)
    visible_skills: Dict[str, str] = field(default_factory=dict)
    last_results: List[Dict[str, Any]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def observe_tool(self, name: str, desc: str):
        self.visible_tools[name] = desc

    def record_result(self, cmd: str, ok: bool, preview: str = ""):
        self.last_results.append({
            "cmd": cmd, "ok": ok, "preview": preview[:300],
        })
        if len(self.last_results) > 5:
            self.last_results = self.last_results[-5:]

    def record_error(self, msg: str):
        self.errors.append(msg)
        if len(self.errors) > 3:
            self.errors = self.errors[-3:]

    def record_lesson(self, lesson: str):
        self.lessons.append(lesson)
        if len(self.lessons) > 5:
            self.lessons = self.lessons[-5:]

    def serialize(self) -> str:
        """Serialize into a context block for the next turn.

        Generates three types of awareness:
        1. State awareness: what tools/results are known
        2. Action awareness: what succeeded/failed recently
        3. Next-step hints: what the agent should consider doing next
        """
        parts = []
        if self.visible_tools:
            lines = ["[Discovered tools]"]
            for name, desc in self.visible_tools.items():
                lines.append(f"  {name}: {desc}")
            parts.append("\n".join(lines))
        if self.last_results:
            lines = ["[Recent command results]"]
            for r in self.last_results:
                status = "OK" if r["ok"] else "FAILED"
                lines.append(f"  [{status}] {r['cmd']}")
                if r["preview"]:
                    lines.append(f"    {r['preview'][:150]}")
            parts.append("\n".join(lines))

            awareness = self._generate_awareness()
            if awareness:
                parts.append(awareness)

        if self.errors:
            parts.append("[Errors to address]\n" + "\n".join(f"  - {e}" for e in self.errors))
        if self.lessons:
            parts.append("[Lessons learned]\n" + "\n".join(f"  - {l}" for l in self.lessons))
        return "\n\n".join(parts)

    def _generate_awareness(self) -> str:
        """Generate awareness cues based on current state."""
        cues = []
        if not self.last_results:
            return ""

        last = self.last_results[-1]

        failed_count = sum(1 for r in self.last_results if not r["ok"])
        if failed_count >= 3:
            cues.append(
                "WARNING: Multiple consecutive failures detected. "
                "Stop repeating the same approach. Try a completely different strategy: "
                "use a different tool, try a simpler command (ls, cat), or ask the user for help.")

        if last["cmd"].startswith("TOOL --search"):
            cues.append("Search completed. Execute the found command to get real data.")

        if not last["ok"]:
            cues.append(f"Last command failed. Consider: check tool docs or source code.")
            if self.errors:
                cues.append("Active errors exist. Fix them before proceeding.")

        if last["cmd"].startswith("read:") or last["cmd"].startswith("cat "):
            cues.append("File read completed. Use the information to proceed with the task.")

        has_search = any("--search" in r["cmd"] for r in self.last_results)
        has_exec = any(
            not r["cmd"].startswith("TOOL --search") and
            not r["cmd"].startswith("read:") and
            not r["cmd"].startswith("cat ") and
            not r["cmd"].startswith("search:")
            for r in self.last_results
        )
        if has_search and has_exec and last["ok"]:
            cues.append("Tool execution succeeded. Present results to the user.")

        if not cues:
            return ""
        return "[Next-step awareness]\n" + "\n".join(f"  - {c}" for c in cues)


_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))


def build_runtime_state() -> str:
    """Build a runtime state header with process/system info."""
    import datetime
    lines = [
        "---",
        f"timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"platform: {platform.system()} {platform.release()}",
        f"project_root: {_PROJECT_ROOT}",
        "---",
    ]
    return "\n".join(lines)


_SESSIONS_DIR = os.path.join(_PROJECT_ROOT, "runtime", "sessions")


@dataclass
class Session:
    id: str
    title: str = "New Task"
    status: str = "idle"
    mode: str = "agent"
    context: SessionContext = field(default_factory=SessionContext)
    environment: AgentEnvironment = field(default_factory=AgentEnvironment)
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    codebase_root: Optional[str] = None
    done_reason: Optional[str] = None

    @property
    def _dir(self) -> str:
        return os.path.join(_SESSIONS_DIR, self.id)

    def save(self, events: Optional[list] = None):
        """Persist session metadata, context, and UI events to disk."""
        session_dir = self._dir
        os.makedirs(session_dir, exist_ok=True)
        data = {
            "id": self.id,
            "title": self.title,
            "status": "idle" if self.status == "running" else self.status,
            "mode": self.mode,
            "created_at": self.created_at,
            "message_count": self.message_count,
            "codebase_root": self.codebase_root,
            "context": self.context.to_dict(),
        }
        if self.done_reason:
            data["done_reason"] = self.done_reason
        if events is not None:
            data["events"] = events
        path = os.path.join(session_dir, "history.json")
        import json as _json
        with open(path, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=1)

    @classmethod
    def load(cls, path: str) -> Optional["Session"]:
        """Load a session from disk.

        ``path`` may be:
        - ``runtime/sessions/<id>/history.json`` (new layout)
        - ``runtime/sessions/<id>.json`` (legacy flat file — auto-migrated)

        Reconstructs status and title from events when the persisted
        metadata is stale (e.g. status saved as "idle" while events show
        a completed session).
        """
        import json as _json
        try:
            with open(path, encoding="utf-8") as f:
                data = _json.load(f)
            ctx = SessionContext.from_dict(data.get("context", {}))

            title = data.get("title", "New Task")
            status = data.get("status", "idle")
            events = data.get("events", [])

            if events:
                for evt in reversed(events):
                    etype = evt.get("type")
                    if etype == "session_renamed":
                        title = evt.get("title", title)
                        break
                has_complete = any(e.get("type") == "complete" for e in events)
                if has_complete and status in ("idle", "running"):
                    status = "done"

            done_reason = data.get("done_reason")
            if not done_reason and status == "done" and events:
                for evt in reversed(events):
                    if evt.get("type") == "session_status" and evt.get("reason"):
                        done_reason = evt["reason"]
                        break
                    if evt.get("type") == "complete" and evt.get("reason"):
                        done_reason = evt["reason"]
                        break

            session = cls(
                id=data["id"],
                title=title,
                status=status,
                mode=data.get("mode", "agent"),
                context=ctx,
                created_at=data.get("created_at", time.time()),
                message_count=data.get("message_count", 0),
                codebase_root=data.get("codebase_root"),
                done_reason=done_reason,
            )
            if path.endswith(".json") and not path.endswith("history.json"):
                session.save(events=events)
                try:
                    os.remove(path)
                except OSError:
                    pass
            return session
        except Exception:
            return None


BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": (
                "Execute a shell command. By default blocks up to 30s (block_until_ms=30000). "
                "If the command hasn't finished by then, it continues in the background and "
                "the partial output so far is returned. Set block_until_ms=0 to run immediately "
                "in background (for dev servers, watchers). Set higher values for long commands. "
                "Use timeout_policy='error' if you need a non-zero exit on timeout."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "block_until_ms": {
                        "type": "integer",
                        "description": (
                            "Max milliseconds to wait for completion. Default 30000 (30s). "
                            "0 = run in background immediately. "
                            "If the command finishes before this, the full output is returned."
                        ),
                    },
                    "timeout_policy": {
                        "type": "string",
                        "enum": ["ok", "error"],
                        "description": (
                            "What to report when block_until_ms is exceeded: "
                            "'ok' (default) returns ok=true with partial output, "
                            "'error' returns ok=false."
                        ),
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a range of lines from a file. You MUST specify start_line and end_line. Best practice: first use search() to locate relevant line numbers, then read the precise range. NEVER blindly set start_line=1, end_line=9999 — read only what you need.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "start_line": {"type": "integer", "description": "First line to read (1-based)."},
                    "end_line": {"type": "integer", "description": "Last line to read (inclusive)."},
                },
                "required": ["path", "start_line", "end_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Manage a TODO list: init, update, or delete items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["init", "update", "delete"], "description": "Action: init (create list), update (change status), delete (remove item)"},
                    "items": {"type": "array", "items": {"type": "object"}, "description": "For init: [{id, text, status}]. For update: [{id, status}]. For delete: [{id}]."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search for text INSIDE files (like grep). Returns matching lines. NOT for listing files — use exec(command=\"find ...\") to list files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex or glob)"},
                    "path": {"type": "string", "description": "Directory to search in (default: project root)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Edit or create a file using line ranges.\n"
                "- Targeted edit: provide start_line, end_line, and new_text to "
                "replace lines [start_line, end_line] inclusive.\n"
                "- Create new file: provide path and new_text only (no line params).\n"
                "ALWAYS use read_file first to locate exact line numbers. "
                "Whole-file rewrites are extremely discouraged — prefer precise ranges."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit or create"},
                    "start_line": {"type": "integer", "description": "First line to replace (1-indexed). Required for existing files."},
                    "end_line": {"type": "integer", "description": "Last line to replace (1-indexed, inclusive). Required for existing files."},
                    "new_text": {"type": "string", "description": "Replacement text for the specified line range, or full content for new files."},
                },
                "required": ["path", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question and wait for their response. Use when you need clarification, approval, or feedback before proceeding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask the user"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "think",
            "description": (
                "Use this tool to think through complex problems step-by-step "
                "before acting. Write your reasoning in the 'thought' parameter. "
                "This is visible to the user as a thinking block. Use it when you "
                "need to plan an approach, weigh trade-offs, or reason about "
                "multiple steps before executing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your step-by-step reasoning or analysis",
                    },
                },
                "required": ["thought"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "experience",
            "description": "Record a lesson learned during this task. Lessons persist across sessions and help you avoid repeating mistakes. Use after fixing bugs, discovering non-obvious behavior, or learning a workaround.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lesson": {"type": "string", "description": "What you learned (specific and actionable)"},
                    "severity": {"type": "string", "enum": ["info", "warning", "critical"], "description": "info=convention, warning=bug-prone pattern, critical=data-loss/security"},
                    "tool": {"type": "string", "description": "Tool name if the lesson is tool-specific (e.g. 'GIT', 'PYTHON')"},
                },
                "required": ["lesson"],
            },
        },
    },
]


class ConversationManager:
    """Stateful conversation orchestrator.

    All GUI variants (HTML, CLI, tkinter) use this same interface.
    Events are dispatched via ``on_event`` callback in the protocol
    format expected by ``AgentGUIEngine``.
    """

    def __init__(self, provider_name: str = "zhipu-glm-4.7",
                 system_prompt: str = "",
                 enable_tools: bool = False,
                 sandbox_policy: str = "ask",
                 default_codebase: Optional[str] = None,
                 brain=None):
        self._provider_name = provider_name
        self._system_prompt = system_prompt
        self._enable_tools = enable_tools
        self._sandbox_policy = sandbox_policy
        self._default_codebase = default_codebase
        self._tool_handlers: Dict[str, Callable] = {}
        self._sessions: Dict[str, Session] = {}
        self._active_session_id: Optional[str] = None
        self._current_turn_session_id: Optional[str] = None
        self._event_cb: Optional[Callable] = None
        self._load_persisted_sessions()
        self._lock = threading.Lock()
        self._cancel_requested = False
        self._task_queues: Dict[str, list] = {}  # session_id -> queued tasks
        self._next_task_id = 1

        if brain is not None:
            self._brain = brain
        else:
            from tool.LLM.logic.brain import Brain
            self._brain = Brain()

        self._hooks_engine = None
        if _HOOKS_AVAILABLE:
            try:
                from pathlib import Path
                self._hooks_engine = HooksEngine(
                    Path(_LLM_TOOL_DIR).resolve(),
                    tool_name="LLM")
            except Exception as e:
                _log.warning("Hooks engine init failed: %s", e)

        if enable_tools:
            self._register_default_tool_handlers()

    @property
    def brain(self):
        return self._brain

    @staticmethod
    def _check_mode_restriction(mode: str, tool_name: str,
                                 args: dict) -> Optional[str]:
        """Return an error message if the tool is blocked in the given mode."""
        if mode == "agent":
            return None
        if tool_name == "edit_file":
            return (f"BLOCKED: {tool_name} is not available in {mode} mode. "
                    f"Only read-only operations are permitted.")
        if tool_name == "exec" and mode in ("ask", "plan"):
            from interface.agent import _is_readonly_safe, _is_plan_safe
            cmd = args.get("command", "")
            checker = _is_plan_safe if mode == "plan" else _is_readonly_safe
            if not checker(cmd):
                return (f"BLOCKED: '{cmd}' is not allowed in {mode} mode. "
                        f"Only read-only commands are permitted.")
        return None

    def _fire_hook(self, event_name: str, **kwargs):
        """Fire a hook event if hooks engine is available."""
        if self._hooks_engine:
            try:
                return self._hooks_engine.fire(event_name, **kwargs)
            except Exception as e:
                _log.warning("Hook %s failed: %s", event_name, e)
        return []

    _RETRYABLE_CODES = {429, 500, 502, 503}

    def _try_fallback_provider(self, failed_provider_name: str):
        """Find a fallback provider after a retryable error.

        Returns (provider, pipeline, provider_name) or None.
        """
        try:
            from tool.LLM.logic.provider_manager import get_manager
            from tool.LLM.logic.auto import PRIMARY_LIST
            mgr = get_manager()
            mgr.report_result(failed_provider_name, None,
                              {"ok": False, "error_code": 429}, None)

            available = mgr.get_available_from_list(PRIMARY_LIST)
            for name in available:
                if name == failed_provider_name:
                    continue
                from tool.LLM.logic.registry import get_provider, get_pipeline
                candidate = get_provider(name)
                if candidate.is_available():
                    return candidate, get_pipeline(name), name
        except Exception as e:
            _log.warning("Fallback provider lookup failed: %s", e)
        return None

    def on_event(self, cb: Callable):
        """Register event callback: ``cb(event_dict)``."""
        self._event_cb = cb

    def register_tool_def(self, tool_def: dict):
        """Register an additional tool definition (OpenAI function-calling format).

        The handler must also be registered via ``register_tool(name, handler)``.
        """
        if not hasattr(self, '_extra_tools'):
            self._extra_tools: list = []
        self._extra_tools.append(tool_def)

    def _load_persisted_sessions(self):
        """Load sessions from disk on startup.

        Supports both:
        - New layout: ``runtime/sessions/<id>/history.json``
        - Legacy layout: ``runtime/sessions/<id>.json`` (auto-migrates)
        """
        if not os.path.isdir(_SESSIONS_DIR):
            return
        import glob
        for path in glob.glob(os.path.join(_SESSIONS_DIR, "*/history.json")):
            session = Session.load(path)
            if session and session.id not in self._sessions:
                self._sessions[session.id] = session
        for path in glob.glob(os.path.join(_SESSIONS_DIR, "*.json")):
            session = Session.load(path)
            if session and session.id not in self._sessions:
                self._sessions[session.id] = session

    def _persist_session(self, session_id: str):
        """Save a session to disk. If _event_provider is set, include events."""
        session = self._sessions.get(session_id)
        if session:
            try:
                events = None
                if hasattr(self, '_event_provider') and self._event_provider:
                    events = self._event_provider(session_id)
                session.save(events=events)
            except Exception as e:
                _log.warning("Failed to persist session %s: %s", session_id, e)

    def _emit(self, evt: dict):
        if self._event_cb:
            self._event_cb(evt)

    def _get_current_environment(self) -> Optional[AgentEnvironment]:
        """Return the AgentEnvironment for the session currently being processed."""
        sid = self._current_turn_session_id
        if sid and sid in self._sessions:
            return self._sessions[sid].environment
        return None

    def _package_message(self, session: Session, text: str,
                         context_feed: Optional[Dict[str, Any]] = None) -> str:
        """Package user text with system state for the LLM.

        Combines: runtime state + agent environment + context_feed + user text.
        Guidance level controls how much boilerplate is included:
          - full: first message (runtime state, cwd, file listing)
          - normal: subsequent (reminder + file listing)
          - minimal: capable models after round 3 (user text only + context_feed)
        """
        parts = []

        cwd = self._get_cwd()
        guidance = self._get_guidance_level(session)

        if guidance == "full":
            parts.append(build_runtime_state())
            parts.append(f"[Working directory] {cwd}\nAll relative paths resolve against this directory. Use relative paths.")
            try:
                files = os.listdir(cwd)
                if files:
                    listing = ", ".join(sorted(files)[:30])
                    parts.append(f"[Files in directory] {listing}")
                else:
                    parts.append("[Files in directory] (empty directory)")
            except OSError:
                pass
        elif guidance == "normal":
            try:
                files = [f for f in os.listdir(cwd)
                         if not f.startswith('.')]
                if files:
                    listing = ", ".join(sorted(files)[:20])
                    parts.append(
                        f"[IMPORTANT] Before modifying any file, you MUST "
                        f"read_file first to see current content. Files in "
                        f"directory: {listing}")
            except OSError:
                pass

        env_block = session.environment.serialize()
        if env_block:
            parts.append(env_block)

        if context_feed:
            feed_parts = []
            if context_feed.get("hint"):
                feed_parts.append(f"[System hint] {context_feed['hint']}")
            if context_feed.get("errors"):
                feed_parts.append("[Known errors]\n" +
                                  "\n".join(f"  - {e}" for e in context_feed["errors"]))
            if context_feed.get("tools_available"):
                lines = ["[Available tools]"]
                for name, desc in context_feed["tools_available"].items():
                    lines.append(f"  {name}: {desc}")
                feed_parts.append("\n".join(lines))
            if context_feed.get("lesson"):
                feed_parts.append(f"[Lesson] {context_feed['lesson']}")
            if feed_parts:
                parts.append("\n".join(feed_parts))

        parts.append(text)
        return "\n\n".join(parts)

    # ── Tool Registration ──

    def register_tool(self, name: str, handler: Callable):
        """Register a custom tool handler: ``handler(args_dict) -> dict``."""
        self._tool_handlers[name] = handler

    def _register_default_tool_handlers(self):
        try:
            from interface.agent import STANDARD_TOOLS, ToolContext
            self._std_tools = STANDARD_TOOLS
            self._ToolContext = ToolContext
        except ImportError:
            self._std_tools = {}
            self._ToolContext = None

        for name in ("exec", "read_file", "search",
                     "edit_file", "todo", "ask_user", "think", "experience"):
            if name in self._std_tools:
                self._tool_handlers[name] = self._make_std_handler(name)
            else:
                fallback = getattr(self, f"_handle_{name}", None)
                if fallback:
                    self._tool_handlers[name] = fallback

    def _make_std_handler(self, name: str):
        def handler(args: dict) -> dict:
            if name == 'edit_file':
                self._snapshot_file(args.get('path', ''))
            sid = self._current_turn_session_id or ""
            session = self._sessions.get(sid)
            session_mode = getattr(session, 'mode', 'agent') if session else 'agent'
            ctx = self._ToolContext(
                emit=self._emit,
                cwd=self._get_cwd(),
                project_root=_PROJECT_ROOT,
                brain=self._brain,
                env_obj=self._get_current_environment(),
                write_history=getattr(self, '_write_history', {}),
                dup_counts=getattr(self, '_dup_counts', {}),
                turn_writes=getattr(self, '_turn_writes', []),
                turn_reads=getattr(self, '_turn_reads', []),
                round_store=getattr(self, '_round_store', None),
                session_id=sid,
                round_num=getattr(self, '_current_round', 0),
                context_lines=self._get_context_lines(),
                mode=session_mode,
            )
            return self._std_tools[name](args, ctx)
        return handler

    def _snapshot_file(self, path: str):
        """Snapshot file content before first write for final diff."""
        if not path:
            return
        if not os.path.isabs(path):
            path = os.path.join(self._get_cwd(), path)
        snapshots = getattr(self, '_file_snapshots', {})
        if path not in snapshots:
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    snapshots[path] = f.read()
            except FileNotFoundError:
                snapshots[path] = None
            except Exception:
                snapshots[path] = None

    def _emit_file_summary(self):
        """Emit file_summary event with final diffs for all modified files."""
        snapshots = getattr(self, '_file_snapshots', {})
        if not snapshots:
            return
        import difflib
        files = []
        for path, original in snapshots.items():
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    current = f.read()
            except Exception:
                current = ''
            if original is None:
                added = len(current.split('\n')) if current else 0
                files.append({
                    "path": path,
                    "name": os.path.basename(path),
                    "type": "new",
                    "added": added,
                    "removed": 0,
                })
            else:
                orig_lines = original.split('\n')
                cur_lines = current.split('\n')
                diff = list(difflib.unified_diff(orig_lines, cur_lines, lineterm=''))
                added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
                removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
                if added or removed:
                    files.append({
                        "path": path,
                        "name": os.path.basename(path),
                        "type": "edit",
                        "added": added,
                        "removed": removed,
                    })
        if files:
            self._emit({"type": "file_summary", "files": files})

    def _get_guidance_level(self, session: Session) -> str:
        """Determine guidance level based on message count.

        Returns 'full' for first message, 'normal' for follow-ups,
        'minimal' for round 4+ (model already has the pattern).
        """
        if session.message_count <= 1:
            return "full"
        if session.message_count <= 3:
            return "normal"
        return "minimal"

    def _get_cwd(self) -> str:
        """Return working directory: session codebase or project root."""
        sid = self._current_turn_session_id
        if sid and sid in self._sessions:
            codebase = self._sessions[sid].codebase_root
            if codebase and os.path.isdir(codebase):
                return codebase
        return _PROJECT_ROOT

    def _get_context_lines(self) -> int:
        try:
            from tool.LLM.logic.config import get_config_value
            return int(get_config_value("context_lines", 2))
        except Exception:
            return 2

    def _mark_session_done(self, session_id: str, reason: str = "done"):
        """Set session status to done with a reason, emit event, and persist."""
        session = self._sessions.get(session_id)
        if session:
            session.status = "done"
            session.done_reason = reason
        self._emit({"type": "session_status", "id": session_id,
                    "status": "done", "reason": reason})
        self._persist_session(session_id)

    def _handle_think(self, args: dict) -> dict:
        return {"ok": True, "output": "[Thinking complete]"}

    @staticmethod
    def _truncate_tool_output(
        tool_name: str, output: str, max_chars: int = 2000, args_json: str = ""
    ) -> str:
        """Progressive context disclosure: compress tool output for LLM context.

        Full output is emitted to the UI via events, but only a compressed
        version enters the LLM context. Uses L0 heuristic summaries based on
        tool type to maximize information density per token.

        Args:
            tool_name: Name of the tool (read_file, exec, search, edit_file, etc.)
            output: Full tool output text
            max_chars: Maximum character limit for context inclusion
            args_json: JSON string of the tool call arguments (for richer summaries)
        """
        if not output or len(output) <= max_chars:
            return output

        lines = output.split("\n")
        total_lines = len(lines)

        args = {}
        if args_json:
            try:
                import json
                args = json.loads(args_json) if isinstance(args_json, str) else {}
            except Exception:
                args = {}

        if tool_name in ("read_file", "read"):
            path = args.get("path", "")
            read_limit = max(max_chars, 8000)
            if len(output) <= read_limit:
                return output
            l0_header = f"[L0: Read {path or 'file'} ({total_lines} lines, {len(output)} chars)]"
            head = "\n".join(lines[:60])
            tail = "\n".join(lines[-15:])
            return (
                f"{l0_header}\n{head}\n\n... [{total_lines - 75} lines omitted] "
                f"...\n\n{tail}\n"
                f"[Use start_line/end_line to read specific sections.]"
            )[:read_limit]

        if tool_name == "exec":
            cmd = args.get("command", "")[:80]
            exit_match = ""
            for line in lines[-5:]:
                if "exit code" in line.lower() or "exit_code" in line.lower():
                    exit_match = line.strip()
                    break
            status = exit_match or ("error" if any(
                kw in output[:500].lower() for kw in ("error", "traceback", "failed", "exception")
            ) else "ok")
            l0_header = f"[L0: Ran `{cmd}` ({total_lines} lines, status: {status})]"
            tail = "\n".join(lines[-20:])
            return f"{l0_header}\n{tail}"[:max_chars]

        if tool_name == "search":
            query = args.get("query", args.get("pattern", ""))[:60]
            match_count = total_lines
            for line in lines[:3]:
                if "match" in line.lower() or "result" in line.lower():
                    import re
                    nums = re.findall(r'\d+', line)
                    if nums:
                        match_count = int(nums[0])
                        break
            l0_header = f"[L0: Searched '{query}' ({match_count} results, {total_lines} lines)]"
            head = "\n".join(lines[:15])
            return f"{l0_header}\n{head}\n\n... [{total_lines - 15} more omitted]"[:max_chars]

        if tool_name in ("edit_file", "write_file"):
            path = args.get("path", "")
            l0_header = f"[L0: Wrote {path or 'file'} ({total_lines} lines output)]"
            head = "\n".join(lines[:10])
            return f"{l0_header}\n{head}"[:max_chars]

        l0_header = f"[L0: {tool_name} ({total_lines} lines, {len(output)} chars)]"
        head = "\n".join(lines[:20])
        return f"{l0_header}\n{head}\n\n... [truncated]"[:max_chars]

    @staticmethod
    def _merge_streaming_tool_calls(accumulated: list, deltas: list) -> list:
        """Merge streaming tool call deltas into accumulated tool calls.

        Streaming APIs send tool calls incrementally — the function name and
        arguments arrive across multiple chunks. This method merges them by
        matching on `index` (preferred) or `id`.
        """
        for delta in deltas:
            idx = delta.get("index")
            did = delta.get("id")
            func = delta.get("function", {})
            matched = None

            if idx is not None:
                while len(accumulated) <= idx:
                    accumulated.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                matched = accumulated[idx]
            elif did:
                for existing in accumulated:
                    if existing.get("id") == did:
                        matched = existing
                        break

            if matched is None:
                accumulated.append({
                    "id": did or delta.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": func.get("name") or "",
                        "arguments": func.get("arguments") or "",
                    },
                })
            else:
                if did and not matched.get("id"):
                    matched["id"] = did
                if func.get("name"):
                    matched["function"]["name"] = func["name"]
                if func.get("arguments"):
                    matched["function"]["arguments"] += func["arguments"]

        return accumulated

    @staticmethod
    def _parse_text_tool_calls(text: str):
        """Parse tool calls embedded in text (e.g. <tool_call>func(args)</tool_call>).

        Some models output tool calls as text instead of structured API calls.
        Returns (cleaned_text, tool_calls_list).
        """
        import re, json as _json, uuid as _uuid

        paren_patterns = [
            re.compile(
                r'<tool_call>\s*(\w+)\s*\(\s*(.*?)\s*\)\s*</tool_call>',
                re.DOTALL),
            re.compile(
                r'<tool_call>\s*(\w+)\s*\(\s*(.*?)\s*\)\s*$',
                re.DOTALL),
        ]

        xml_kv_pattern = re.compile(
            r'<tool_call>\s*(\w+)\s*((?:<arg_key>.*?</arg_value>)+)\s*(?:</tool_call>)?',
            re.DOTALL)
        xml_pair_pattern = re.compile(
            r'<arg_key>\s*(.*?)\s*</arg_key>\s*<arg_value>\s*(.*?)\s*</arg_value>',
            re.DOTALL)

        tool_calls = []
        cleaned = text

        for match in xml_kv_pattern.finditer(text):
            func_name = match.group(1)
            args_dict = {}
            for kv in xml_pair_pattern.finditer(match.group(2)):
                args_dict[kv.group(1)] = kv.group(2)
            if func_name and args_dict:
                tool_calls.append({
                    "id": f"text_tc_{_uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": _json.dumps(args_dict),
                    },
                })
                cleaned = cleaned.replace(match.group(0), "")

        for pattern in paren_patterns:
            for match in pattern.finditer(cleaned):
                func_name = match.group(1)
                args_raw = match.group(2)
                args_dict = {}
                try:
                    args_dict = _json.loads("{" + args_raw + "}")
                except Exception:
                    kv_re = re.compile(
                        r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
                        re.DOTALL)
                    for kv in kv_re.finditer(args_raw):
                        key = kv.group(1)
                        val = kv.group(2)
                        try:
                            import ast
                            args_dict[key] = ast.literal_eval(val)
                        except Exception:
                            args_dict[key] = val.strip('"').strip("'")

                if func_name and args_dict:
                    tool_calls.append({
                        "id": f"text_tc_{_uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": _json.dumps(args_dict),
                        },
                    })
                    cleaned = cleaned.replace(match.group(0), "")

        if not tool_calls:
            json_tc_pattern = re.compile(
                r'\{"index"\s*:\s*\d+\s*,\s*"finish_reason"\s*:\s*"tool_calls".*?"tool_calls"\s*:\s*\[(.+?)\]\s*}',
                re.DOTALL)
            for match in json_tc_pattern.finditer(cleaned):
                try:
                    tc_array_str = "[" + match.group(1) + "]"
                    raw_tcs = _json.loads(tc_array_str)
                    for rtc in raw_tcs:
                        fn = rtc.get("function", {})
                        if fn.get("name"):
                            fn_args = fn.get("arguments", "{}")
                            if isinstance(fn_args, str):
                                try:
                                    _json.loads(fn_args)
                                except _json.JSONDecodeError:
                                    fn_args = _json.dumps({"raw": fn_args})
                            else:
                                fn_args = _json.dumps(fn_args)
                            tool_calls.append({
                                "id": rtc.get("id", f"text_tc_{_uuid.uuid4().hex[:8]}"),
                                "type": "function",
                                "function": {
                                    "name": fn["name"],
                                    "arguments": fn_args,
                                },
                            })
                    if tool_calls:
                        cleaned = cleaned[:match.start()].strip()
                except Exception:
                    pass

            if not tool_calls:
                fn_call_pattern = re.compile(
                    r'\{"(?:name|function)"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(".*?"|\{.*?\})\s*\}',
                    re.DOTALL)
                for match in fn_call_pattern.finditer(cleaned):
                    fn_name = match.group(1)
                    fn_args = match.group(2)
                    if fn_name:
                        if fn_args.startswith('"'):
                            fn_args = fn_args.strip('"')
                        tool_calls.append({
                            "id": f"text_tc_{_uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": fn_args,
                            },
                        })
                        cleaned = cleaned[:match.start()].strip()

        return cleaned.strip(), tool_calls

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """Execute a single tool call from the LLM."""
        import json as _json
        func = tool_call.get("function", {})
        name = func.get("name", "")
        raw_args = func.get("arguments", "{}")
        try:
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str):
                raw_args = raw_args.strip()
                try:
                    args = _json.loads(raw_args)
                except _json.JSONDecodeError:
                    decoder = _json.JSONDecoder()
                    args, idx = decoder.raw_decode(raw_args)
                    remainder = raw_args[idx:].strip()
                    if remainder:
                        self._concat_json_remainder = remainder
            else:
                args = {}
        except Exception:
            args = {}

        sid = self._current_turn_session_id or ""
        session = self._sessions.get(sid)
        session_mode = getattr(session, 'mode', 'agent') if session else 'agent'
        blocked = self._check_mode_restriction(session_mode, name, args)
        if blocked:
            self._emit({"type": "tool", "name": name,
                         "desc": args.get("command", args.get("path", ""))[:80]})
            self._emit({"type": "tool_result", "ok": False, "output": blocked})
            return {"ok": False, "output": blocked}

        self._fire_hook("on_pre_tool_use",
                        session_id=sid, tool_name=name, tool_args=args,
                        round_num=getattr(self, '_current_round', 0))

        t0 = time.time()
        handler = self._tool_handlers.get(name)
        if handler:
            result = handler(args)
        else:
            self._emit({"type": "text", "tokens": f"Unknown tool: {name}"})
            result = {"ok": False, "output": f"Unknown tool: {name}"}

        remainder = getattr(self, '_concat_json_remainder', None)
        if remainder:
            self._concat_json_remainder = None
            result["output"] = (
                result.get("output", "") +
                "\n\n[WARNING] You tried to pass multiple JSON objects in one tool call. "
                "Only the first was used. Call each tool SEPARATELY for each file. "
                f"Ignored: {remainder[:100]}"
            )

        duration_ms = (time.time() - t0) * 1000
        self._fire_hook("on_post_tool_use",
                        session_id=sid, tool_name=name, tool_args=args,
                        result=result, round_num=getattr(self, '_current_round', 0),
                        duration_ms=duration_ms)
        return result

    # ── Session Management ──

    def new_session(self, session_id: str = None, title: str = "New Task",
                    codebase_root: Optional[str] = None,
                    mode: str = "agent") -> str:
        sid = session_id or str(uuid.uuid4())[:8]
        codebase = codebase_root or self._default_codebase

        prompt = self._system_prompt
        bootstrap = self._brain.get_session_bootstrap(sid, codebase)
        if bootstrap:
            prompt = prompt + "\n\n" + bootstrap

        ctx = SessionContext(system_prompt=prompt)
        with self._lock:
            self._sessions[sid] = Session(
                id=sid, title=title, context=ctx,
                codebase_root=codebase, mode=mode)
            if self._active_session_id is None:
                self._active_session_id = sid
        self._emit({"type": "session_created", "id": sid, "title": title,
                     "codebase_root": codebase, "mode": mode})
        self._fire_hook("on_session_start",
                        session_id=sid, codebase_root=codebase, title=title)
        self._persist_session(sid)
        return sid

    def rename_session(self, session_id: str, new_title: str):
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.title = new_title
        self._emit({"type": "session_renamed", "id": session_id, "title": new_title})
        self._persist_session(session_id)

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            if self._active_session_id == session_id:
                remaining = list(self._sessions.keys())
                self._active_session_id = remaining[-1] if remaining else None
        session_dir = os.path.join(_SESSIONS_DIR, session_id)
        if os.path.isdir(session_dir):
            try:
                import shutil
                shutil.rmtree(session_dir)
            except OSError:
                pass
        self._emit({"type": "session_deleted", "id": session_id})

    def set_active(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._active_session_id = session_id

    def cancel_current(self):
        self._cancel_requested = True

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"id": s.id, "title": s.title, "status": s.status,
             "mode": s.mode, "message_count": s.message_count,
             "created_at": s.created_at,
             **({"done_reason": s.done_reason} if s.done_reason else {})}
            for s in self._sessions.values()
        ]

    # ── Conversation ──

    def send_message(self, session_id: str, text: str,
                     blocking: bool = False,
                     context_feed: Optional[Dict[str, Any]] = None,
                     turn_limit: int = 0,
                     mode: str = "",
                     model: str = ""):
        """Send a user message and get LLM response.

        If the session is already running, the task is queued and will
        execute automatically when the current task completes.
        """
        session = self._sessions.get(session_id)
        if session and session.status == "running":
            task_id = f"q{self._next_task_id}"
            self._next_task_id += 1
            task = {"id": task_id, "text": text, "context_feed": context_feed,
                    "turn_limit": turn_limit, "mode": mode, "model": model}
            if session_id not in self._task_queues:
                self._task_queues[session_id] = []
            self._task_queues[session_id].append(task)
            self._emit({"type": "queue_updated",
                        "queue": self._serialize_queue(session_id)})
            return

        self._start_turn(session_id, text, blocking, context_feed, turn_limit)

    def _start_turn(self, session_id: str, text: str,
                    blocking: bool = False,
                    context_feed: Optional[Dict[str, Any]] = None,
                    turn_limit: int = 0):
        """Start a turn, processing any queued tasks on completion."""
        if blocking:
            self._run_turn(session_id, text, context_feed, turn_limit)
            self._drain_task_queue(session_id)
        else:
            def _safe_run():
                try:
                    self._run_turn(session_id, text, context_feed, turn_limit)
                except Exception as e:
                    import traceback, sys
                    traceback.print_exc(file=sys.stderr)
                    self._emit({"type": "system_notice",
                                "text": f"Thread exception: {e}",
                                "level": "error"})
                    self._emit({"type": "complete", "reason": "error"})
                    session = self._sessions.get(session_id)
                    if session:
                        self._mark_session_done(session_id)
                self._drain_task_queue(session_id)
            t = threading.Thread(target=_safe_run, daemon=True)
            t.start()

    def _drain_task_queue(self, session_id: str):
        """Process queued tasks for a session after a turn completes."""
        queue = self._task_queues.get(session_id, [])
        while queue:
            task = queue.pop(0)
            self._emit({"type": "queue_task_started",
                        "task_id": task.get("id", ""),
                        "mode": task.get("mode", ""),
                        "model": task.get("model", ""),
                        "remaining": len(queue)})
            self._emit({"type": "queue_updated",
                        "queue": self._serialize_queue(session_id)})
            try:
                self._run_turn(session_id, task["text"],
                               task.get("context_feed"),
                               task.get("turn_limit", 0))
            except Exception as e:
                import traceback, sys
                traceback.print_exc(file=sys.stderr)
                self._emit({"type": "system_notice",
                            "text": f"Queue task exception: {e}",
                            "level": "error"})
                self._emit({"type": "complete", "reason": "error"})
                session = self._sessions.get(session_id)
                if session:
                    self._mark_session_done(session_id)

    def _serialize_queue(self, session_id: str) -> list:
        """Return a serializable snapshot of the task queue."""
        return [
            {"id": t.get("id", ""), "text": t.get("text", "")[:120],
             "mode": t.get("mode", ""), "model": t.get("model", ""),
             "turn_limit": t.get("turn_limit", 0)}
            for t in self._task_queues.get(session_id, [])
        ]

    def get_task_queue(self, session_id: str) -> list:
        """Return the current task queue for a session."""
        return self._serialize_queue(session_id)

    def clear_task_queue(self, session_id: str) -> int:
        """Clear all queued tasks for a session. Returns count removed."""
        queue = self._task_queues.get(session_id, [])
        count = len(queue)
        queue.clear()
        if count:
            self._emit({"type": "queue_updated", "queue": []})
        return count

    def update_queued_task(self, session_id: str, task_id: str,
                           updates: dict) -> bool:
        """Update mode/model/turn_limit for a queued task. Returns True if found."""
        queue = self._task_queues.get(session_id, [])
        for task in queue:
            if task.get("id") == task_id:
                for k in ("mode", "model", "turn_limit"):
                    if k in updates:
                        task[k] = updates[k]
                self._emit({"type": "queue_updated",
                            "queue": self._serialize_queue(session_id)})
                return True
        return False

    def remove_queued_task(self, session_id: str, task_id: str) -> bool:
        """Remove a queued task by ID. Returns True if found."""
        queue = self._task_queues.get(session_id, [])
        for i, task in enumerate(queue):
            if task.get("id") == task_id:
                queue.pop(i)
                self._emit({"type": "queue_updated",
                            "queue": self._serialize_queue(session_id)})
                return True
        return False

    def reorder_queued_task(self, session_id: str, task_id: str,
                            new_index: int) -> bool:
        """Move a queued task to a new position. Returns True if found."""
        queue = self._task_queues.get(session_id, [])
        for i, task in enumerate(queue):
            if task.get("id") == task_id:
                queue.pop(i)
                new_index = max(0, min(new_index, len(queue)))
                queue.insert(new_index, task)
                self._emit({"type": "queue_updated",
                            "queue": self._serialize_queue(session_id)})
                return True
        return False

    _STREAM_HEARTBEAT_S = 90
    _STREAM_RECONNECT_ATTEMPTS = 2

    def _resilient_stream(self, provider, messages, temperature, max_tokens, tools):
        """Wrap provider.stream() with heartbeat timeout and reconnection.

        Yields chunks from the provider.  If the stream stalls for
        _STREAM_HEARTBEAT_S seconds or a network error occurs, retries
        up to _STREAM_RECONNECT_ATTEMPTS times before raising.
        """
        import queue as _q

        for attempt in range(self._STREAM_RECONNECT_ATTEMPTS):
            chunk_queue: _q.Queue = _q.Queue(maxsize=64)
            error_holder: list = []
            cancel_signal = threading.Event()

            def _producer(q, cancel, errs):
                try:
                    for chunk in provider.stream(
                        messages, temperature=temperature,
                        max_tokens=max_tokens, tools=tools,
                    ):
                        if cancel.is_set():
                            return
                        try:
                            q.put(chunk, timeout=5)
                        except _q.Full:
                            if cancel.is_set():
                                return
                            q.put(chunk)
                    q.put(None)
                except Exception as e:
                    errs.append(e)
                    q.put(None)

            t = threading.Thread(
                target=_producer,
                args=(chunk_queue, cancel_signal, error_holder),
                daemon=True,
            )
            t.start()

            try:
                while True:
                    try:
                        chunk = chunk_queue.get(timeout=self._STREAM_HEARTBEAT_S)
                    except _q.Empty:
                        cancel_signal.set()
                        raise TimeoutError("Stream heartbeat timeout")
                    if chunk is None:
                        if error_holder:
                            raise error_holder[0]
                        return
                    yield chunk
                    if chunk.get("done"):
                        return
            except (TimeoutError, ConnectionError, OSError) as exc:
                cancel_signal.set()
                is_last = attempt == self._STREAM_RECONNECT_ATTEMPTS - 1
                self._emit({"type": "system_notice",
                            "text": f"Stream interrupted: {exc}"
                                    + (" Retrying..." if not is_last else ""),
                            "level": "warning"})
                if is_last:
                    raise
            except Exception as exc:
                cancel_signal.set()
                exc_name = type(exc).__name__
                _network_errors = (
                    "ChunkedEncodingError", "ConnectionError",
                    "ReadTimeout", "ConnectTimeout", "Timeout",
                    "RemoteDisconnected", "IncompleteRead",
                    "ProtocolError", "ProxyError",
                )
                if exc_name in _network_errors:
                    is_last = attempt == self._STREAM_RECONNECT_ATTEMPTS - 1
                    self._emit({"type": "system_notice",
                                "text": f"Network error ({exc_name}): {exc}"
                                        + (" Retrying..." if not is_last else ""),
                                "level": "warning"})
                    if is_last:
                        raise
                else:
                    raise

    def _run_turn(self, session_id: str, text: str,
                  context_feed: Optional[Dict[str, Any]] = None,
                  turn_limit: int = 0):
        session = self._sessions.get(session_id)
        if not session:
            self._emit({"type": "error", "message": f"Session {session_id} not found"})
            return

        session_mode = getattr(session, 'mode', 'agent')
        session.status = "running"
        session.done_reason = None
        session.message_count += 1
        self._cancel_requested = False
        self._current_turn_session_id = session_id
        self._current_round = 0
        self._turn_writes = []
        self._turn_reads: List[str] = []
        self._quality_warnings: Dict[str, List[str]] = {}
        self._file_snapshots: Dict[str, Optional[str]] = {}
        self._auto_tried = set()
        self._auto_retry_count = 0
        self._auto_confirmed = False
        self._emit({"type": "session_status", "id": session_id, "status": "running"})
        self._fire_hook("on_turn_start",
                        session_id=session_id, user_text=text,
                        message_count=session.message_count)

        try:
            # Build user event with prompt + ecosystem context + system state
            ecosystem = {}
            system_state = {"nudge_triggered": False}
            contextual = {}
            try:
                from interface.agent import build_ecosystem_info, build_system_state, build_contextual_suggestions
                _proj = getattr(self, "_project_root", None) or _PROJECT_ROOT
                ecosystem = build_ecosystem_info(str(_proj))
                contextual = build_contextual_suggestions(str(_proj), text, top_k=3)
                system_state = build_system_state(
                    session_env=session.environment,
                    nudge_triggered=False,
                    quality_warnings=self._quality_warnings,
                    last_tool_results=session.environment.last_results if session.environment else None,
                )
            except Exception:
                pass
            user_evt = {
                "type": "user",
                "prompt": text,
                "ecosystem": ecosystem,
                "user_rationale": ecosystem.get("user_rationale", ""),
                "system_state": system_state,
            }
            if contextual:
                user_evt["suggestions"] = contextual
            self._emit(user_evt)

            _compression_ratio = 0.5
            try:
                from tool.LLM.logic.config import get_config_value
                _compression_ratio = float(get_config_value("compression_ratio", 0.5))
            except Exception:
                pass
            _compression_ratio = max(0.25, min(0.75, _compression_ratio))
            if session.context.needs_compression(trigger_ratio=_compression_ratio):
                self._compress_context(session)

            packaged = self._package_message(session, text, context_feed)
            session.context.add_user(packaged)

            auto_title = session.message_count == 1 and session.title == "New Task"
            from tool.LLM.logic.registry import get_provider, get_pipeline

            is_auto = self._provider_name == "auto"
            actual_provider_name = self._provider_name

            if is_auto:
                self._emit({
                    "type": "model_decision_start",
                    "text": "Choosing model\u2026",
                })
                try:
                    from tool.LLM.logic.auto import auto_decide
                    chosen, _ = auto_decide(user_prompt=text)
                    if chosen:
                        actual_provider_name = chosen
                    else:
                        self._emit({"type": "model_decision_end", "chosen": None,
                                    "error": "No available providers"})
                        self._emit({"type": "system_notice", "text": "No available providers for Auto mode.", "level": "error"})
                        self._emit({"type": "complete", "reason": "error"})
                        self._mark_session_done(session_id, "error")
                        return
                except Exception as e:
                    self._emit({"type": "model_decision_end", "chosen": None,
                                "error": str(e)})
                    self._emit({"type": "system_notice", "text": f"Auto decision failed: {e}", "level": "error"})
                    self._emit({"type": "complete", "reason": "error"})
                    self._mark_session_done(session_id, "error")
                    return
                self._emit({
                    "type": "model_decision_proposed",
                    "proposed": actual_provider_name,
                })

            provider = get_provider(actual_provider_name)

            if not provider.is_available():
                self._emit({"type": "system_notice", "text": f"Provider {actual_provider_name} is not available.", "level": "error"})
                self._emit({"type": "complete", "reason": "error"})
                self._mark_session_done(session_id, "error")
                return

            tools = None
            if self._enable_tools and provider.capabilities.supports_tool_calling:
                tools = list(BUILTIN_TOOLS)
                if session_mode in ("ask", "plan"):
                    _write_tools = {"edit_file", "todo"}
                    tools = [t for t in tools
                             if t.get("function", {}).get("name") not in _write_tools]
                if hasattr(self, '_extra_tools'):
                    tools.extend(self._extra_tools)
            pipeline = get_pipeline(actual_provider_name)

            from tool.LLM.logic.config import get_config_value
            cfg_turn_limit = get_config_value("default_turn_limit", 20)
            cfg_max_output = get_config_value("max_output_tokens", 16384)

            HARD_ROUND_CAP = 10000
            ZOMBIE_CHECK_INTERVAL = 50
            _is_unlimited = (turn_limit == 0)
            if turn_limit < 0:
                turn_limit = int(cfg_turn_limit) or 20
            elif turn_limit == 0:
                turn_limit = HARD_ROUND_CAP
            max_rounds = min(turn_limit, HARD_ROUND_CAP)
            effective_limit = 0 if _is_unlimited else turn_limit
            self._emit({"type": "turn_limit_set", "turn_limit": effective_limit})
            round_num = 0
            empty_retries = 0
            max_empty_retries = pipeline.get_max_retries()
            consecutive_empty = 0
            MAX_CONSECUTIVE_EMPTY = 3
            _tool_call_history: List[str] = []

            provider_max = getattr(provider.capabilities, 'max_output_tokens', 4096) or 4096
            default_max_tokens = min(provider_max, int(cfg_max_output))
            current_max_tokens = default_max_tokens

            _wrapup_nudged = False
            _silent_rounds = 0
            _zombie_checks = 0
            _was_cancelled = False
            _turn_t0 = time.time()

            while round_num < max_rounds:
                if self._cancel_requested:
                    self._cancel_requested = False
                    _was_cancelled = True
                    break

                if round_num > 0 and self._provider_name != actual_provider_name:
                    new_name = self._provider_name
                    if new_name == "auto":
                        self._emit({"type": "system_notice",
                                    "text": "Switched to Auto. Re-deciding model\u2026",
                                    "level": "info"})
                        try:
                            from tool.LLM.logic.auto import auto_decide
                            chosen, _ = auto_decide(user_prompt=text)
                            if chosen:
                                actual_provider_name = chosen
                                provider = get_provider(actual_provider_name)
                                pipeline = get_pipeline(actual_provider_name)
                                is_auto = True
                                self._auto_confirmed = False
                            else:
                                self._emit({"type": "system_notice",
                                            "text": "Auto re-decision failed: no available providers.",
                                            "level": "warning"})
                        except Exception as e:
                            self._emit({"type": "system_notice",
                                        "text": f"Auto re-decision failed: {e}",
                                        "level": "warning"})
                    else:
                        old_name = actual_provider_name
                        actual_provider_name = new_name
                        try:
                            provider = get_provider(actual_provider_name)
                            pipeline = get_pipeline(actual_provider_name)
                        except Exception as e:
                            self._emit({"type": "system_notice",
                                        "text": f"Failed to switch to {new_name}: {e}",
                                        "level": "warning"})
                            actual_provider_name = old_name
                            provider = get_provider(actual_provider_name)
                            pipeline = get_pipeline(actual_provider_name)
                        is_auto = False
                        self._emit({"type": "system_notice",
                                    "text": f"Switched to {actual_provider_name}.",
                                    "level": "info"})
                        self._emit({"type": "model_confirmed",
                                    "provider": actual_provider_name})

                round_num += 1
                self._current_round = round_num
                self._emit({"type": "debug",
                             "text": f"Round {round_num}/{turn_limit} (max_rounds={max_rounds})"})
                full_text = ""
                tool_calls_accum = []
                _cancelled_mid_stream = False

                if (not _is_unlimited and turn_limit > 3
                        and round_num == turn_limit - 1
                        and not _wrapup_nudged):
                    _wrapup_nudged = True
                    session.context.add_user(
                        "[System] You are approaching the turn limit. "
                        "Complete ALL remaining sub-tasks now. If you "
                        "have multiple parts to address, do them in this "
                        "round. Summarize your findings concisely.")
                elif (not _is_unlimited and round_num == turn_limit):
                    session.context.add_user(
                        "[SYSTEM] FINAL ROUND. After this response the "
                        "task ends. Include a text summary alongside any "
                        "tool calls. Do NOT rely on another round.")

                use_streaming = empty_retries == 0
                _fallback_attempted = False

                for _llm_attempt in range(2):
                    llm_req_evt = {
                        "type": "llm_request",
                        "provider": actual_provider_name if _llm_attempt == 0 else getattr(provider, 'name', '?'),
                        "round": round_num,
                    }
                    self._emit(llm_req_evt)

                    first_chunk = True
                    api_messages = pipeline.prepare_messages(
                        session.context.get_messages_for_api(),
                        turn_number=session.message_count,
                    )
                    api_tools = pipeline.prepare_tools(tools, provider.capabilities)

                    _llm_error = None

                    _STREAMABLE = {"edit_file", "edit", "think"}
                    _streaming_tc_map = {}

                    if use_streaming:
                        for chunk in self._resilient_stream(
                            provider, api_messages,
                            temperature=0.7,
                            max_tokens=current_max_tokens,
                            tools=api_tools,
                        ):
                            if self._cancel_requested:
                                self._cancel_requested = False
                                full_text = ""
                                tool_calls_accum = []
                                _cancelled_mid_stream = True
                                _was_cancelled = True
                                break
                            if first_chunk and chunk.get("ok"):
                                first_chunk = False
                                if is_auto and not getattr(self, '_auto_confirmed', False):
                                    self._auto_confirmed = True
                                    self._emit({
                                        "type": "model_confirmed",
                                        "provider": actual_provider_name,
                                    })
                                self._emit({"type": "llm_response_start", "round": round_num})

                            if chunk.get("ok"):
                                r = chunk.get("reasoning", "")
                                if r:
                                    self._emit({"type": "thinking", "tokens": r})
                                t = chunk.get("text", "")
                                if t:
                                    full_text += t
                                    self._emit({"type": "text", "tokens": t})
                                tc = chunk.get("tool_calls")
                                if tc:
                                    for delta in tc:
                                        idx = delta.get("index", 0)
                                        fn = delta.get("function", {})
                                        fn_name = fn.get("name", "")
                                        fn_args = fn.get("arguments", "")
                                        if fn_name and fn_name in _STREAMABLE and idx not in _streaming_tc_map:
                                            _streaming_tc_map[idx] = fn_name
                                            self._emit({"type": "tool_stream_start",
                                                        "index": idx, "name": fn_name,
                                                        "round": round_num})
                                            if fn_args:
                                                self._emit({"type": "tool_stream_delta",
                                                            "index": idx, "content": fn_args})
                                        elif idx in _streaming_tc_map and fn_args:
                                            self._emit({"type": "tool_stream_delta",
                                                        "index": idx, "content": fn_args})
                                        elif fn_name and fn_name in _STREAMABLE and idx in _streaming_tc_map:
                                            pass
                                        elif not fn_name and idx not in _streaming_tc_map:
                                            if len(tool_calls_accum) > idx:
                                                existing_name = tool_calls_accum[idx].get("function", {}).get("name", "")
                                                if existing_name in _STREAMABLE:
                                                    _streaming_tc_map[idx] = existing_name
                                                    self._emit({"type": "tool_stream_start",
                                                                "index": idx, "name": existing_name,
                                                                "round": round_num})
                                                    if fn_args:
                                                        self._emit({"type": "tool_stream_delta",
                                                                    "index": idx, "content": fn_args})
                                    self._merge_streaming_tool_calls(tool_calls_accum, tc)
                                if chunk.get("done"):
                                    for sidx in _streaming_tc_map:
                                        self._emit({"type": "tool_stream_end",
                                                    "index": sidx, "round": round_num})
                                    if chunk.get("tool_calls") and not tool_calls_accum:
                                        tool_calls_accum = chunk["tool_calls"]
                                    latency = chunk.get("latency_s")
                                    self._last_finish_reason = chunk.get("finish_reason", "")
                                    self._last_usage = chunk.get("usage", {})
                                    stream_end_evt = {
                                        "type": "llm_response_end",
                                        "round": round_num,
                                        "latency_s": latency,
                                        "has_tool_calls": bool(tool_calls_accum),
                                        "provider": actual_provider_name,
                                        "model": chunk.get("model", actual_provider_name),
                                        "_full_text": full_text,
                                    }
                                    if chunk.get("usage"):
                                        stream_end_evt["usage"] = chunk["usage"]
                                    self._emit(stream_end_evt)
                                    if turn_limit > 0 and not tool_calls_accum and round_num >= turn_limit:
                                        if auto_title:
                                            self._generate_title_async(session_id, text, full_text)
                                        self._emit({"type": "complete", "reason": "round_limit",
                                                    "round": round_num, "turn_limit": turn_limit})
                                        self._mark_session_done(session_id, "round_limit")
                                        return
                                    break
                            else:
                                for sidx in _streaming_tc_map:
                                    self._emit({"type": "tool_stream_end",
                                                "index": sidx, "round": round_num})
                                _streaming_tc_map.clear()
                                _llm_error = chunk
                                break
                    else:
                        self._emit({"type": "llm_response_start", "round": round_num})
                        import time as _time
                        t0 = _time.time()
                        result = provider.send(
                            api_messages,
                            temperature=0.7,
                            max_tokens=current_max_tokens,
                            tools=api_tools,
                        )
                        latency = _time.time() - t0
                        self._last_finish_reason = result.get("finish_reason", "")
                        self._last_usage = result.get("usage", {})
                        if result.get("ok"):
                            full_text = result.get("text", "") or ""
                            if result.get("tool_calls"):
                                tool_calls_accum = result["tool_calls"]
                        else:
                            _llm_error = result

                    if _llm_error is None:
                        try:
                            from tool.LLM.logic.provider_manager import get_manager
                            get_manager().report_result(
                                actual_provider_name, None,
                                {"ok": True}, None)
                        except Exception:
                            pass
                        break

                    err = _llm_error.get("error", "Unknown error")
                    error_code = _llm_error.get("error_code", 0)
                    if not error_code and ("429" in err or "rate limit" in err.lower()):
                        error_code = 429
                    failed_name = getattr(provider, 'name', actual_provider_name)

                    try:
                        from tool.LLM.logic.provider_manager import get_manager
                        get_manager().report_result(
                            failed_name, None,
                            {"ok": False, "error_code": error_code,
                             "error": err}, None)
                    except Exception:
                        pass

                    # Auto fallback: try next model (works both pre and post confirmation)
                    _MAX_AUTO_RETRIES = 3
                    _auto_retries = getattr(self, '_auto_retry_count', 0)
                    if is_auto and _auto_retries < _MAX_AUTO_RETRIES:
                        try:
                            from tool.LLM.logic.auto import get_next_available
                            _tried = getattr(self, '_auto_tried', set())
                            _tried.add(failed_name)
                            self._auto_tried = _tried
                            fallback = get_next_available(exclude=list(_tried))
                            if fallback:
                                self._auto_retry_count = _auto_retries + 1
                                self._auto_confirmed = False
                                actual_provider_name = fallback
                                provider = get_provider(actual_provider_name)
                                pipeline = get_pipeline(actual_provider_name)
                                tools_reload = list(BUILTIN_TOOLS) if self._enable_tools and provider.capabilities.supports_tool_calling else None
                                if tools_reload and session_mode in ("ask", "plan"):
                                    _write_tools = {"edit_file", "todo"}
                                    tools_reload = [t for t in tools_reload
                                                    if t.get("function", {}).get("name") not in _write_tools]
                                if tools_reload is not None:
                                    tools = tools_reload
                                self._emit({
                                    "type": "llm_response_end",
                                    "round": round_num,
                                    "error": True,
                                    "error_code": error_code,
                                    "latency_s": 0,
                                    "has_tool_calls": False,
                                    "provider": failed_name,
                                })
                                self._emit({"type": "system_notice",
                                            "text": f"{failed_name} failed: {err}",
                                            "level": "warning"})
                                self._emit({"type": "debug",
                                            "text": f"Auto retry ({_auto_retries+1}/{_MAX_AUTO_RETRIES}): {failed_name} → {actual_provider_name}"})
                                self._emit({
                                    "type": "model_decision_proposed",
                                    "proposed": actual_provider_name,
                                })
                                round_num -= 1
                                continue
                        except Exception:
                            pass

                    self._emit({
                        "type": "llm_response_end",
                        "round": round_num,
                        "error": True,
                        "error_code": error_code,
                        "latency_s": 0,
                        "has_tool_calls": False,
                        "provider": failed_name,
                    })
                    self._emit({"type": "system_notice", "text": f"Error: {err}", "level": "error"})
                    self._emit({"type": "complete", "reason": "error"})
                    self._mark_session_done(session_id, "error")
                    return

                if not use_streaming and _llm_error is None:
                    resp_event = {
                        "type": "llm_response_end",
                        "round": round_num,
                        "latency_s": round(latency, 3),
                        "has_tool_calls": bool(tool_calls_accum),
                        "provider": getattr(provider, 'name', self._provider_name),
                        "model": result.get("model", self._provider_name),
                        "_full_text": full_text,
                    }
                    if result.get("usage"):
                        resp_event["usage"] = result["usage"]
                    self._emit(resp_event)

                if _cancelled_mid_stream:
                    break

                if full_text and not tool_calls_accum:
                    _has_embedded = ("<tool_call>" in full_text
                                     or '"tool_calls"' in full_text
                                     or '"function"' in full_text)
                    if _has_embedded:
                        cleaned, parsed_tcs = self._parse_text_tool_calls(full_text)
                        if parsed_tcs:
                            self._emit({"type": "text",
                                        "tokens": f"[Parsed {len(parsed_tcs)} text-embedded tool call(s)]\n"})
                            tool_calls_accum.extend(parsed_tcs)
                            full_text = cleaned

                if full_text or tool_calls_accum:
                    consecutive_empty = 0
                if full_text and not use_streaming:
                    self._emit({"type": "text", "tokens": full_text})

                if turn_limit > 0 and not tool_calls_accum and round_num >= turn_limit:
                    if full_text:
                        session.context.add_assistant(full_text)
                    if auto_title:
                        self._generate_title_async(session_id, text, full_text)
                    self._emit({"type": "complete", "reason": "round_limit",
                                "round": round_num, "turn_limit": turn_limit})
                    self._mark_session_done(session_id, "round_limit")
                    return

                if not full_text and not tool_calls_accum:
                    consecutive_empty += 1
                    if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                        self._emit({"type": "text",
                                    "tokens": f"[{consecutive_empty} consecutive empty responses — "
                                    "stopping to avoid wasting API calls.]\n"})
                        break

                    last_finish = getattr(self, '_last_finish_reason', "")
                    last_usage = getattr(self, '_last_usage', {})
                    validation = pipeline.validate_response(
                        full_text, tool_calls_accum, last_finish, last_usage)
                    if not validation.get("valid", True) and validation.get("retry"):
                        if validation.get("increase_max_tokens"):
                            new_max = pipeline.get_recommended_max_tokens(
                                current_max_tokens)
                            if new_max > current_max_tokens:
                                current_max_tokens = new_max
                                self._emit({"type": "text",
                                            "tokens": f"[Reasoning model budget exceeded, "
                                            f"retrying with max_tokens={current_max_tokens}...]\n"})
                            else:
                                self._emit({"type": "text",
                                            "tokens": "[Reasoning budget maxed out, retrying...]\n"})
                        else:
                            self._emit({"type": "text",
                                        "tokens": f"[{validation.get('reason', 'Retrying')}]\n"})
                        continue

                if not tool_calls_accum:
                    if full_text:
                        session.context.add_assistant(full_text)
                        if (tools and round_num <= 6
                                and self._should_nudge(full_text, round_num)):
                            has_read = any(
                                r.get("cmd", "").startswith("read:")
                                for r in session.environment.last_results)
                            if has_read:
                                nudge = (
                                    "You already read the file. Now use "
                                    "edit_file to apply your fix. Provide "
                                    "start_line, end_line, and new_text. "
                                    "Only replace the lines that change.")
                            else:
                                nudge = (
                                    "You described changes but didn't apply them. "
                                    "First read_file to locate exact line numbers, "
                                    "then use edit_file with start_line, end_line, "
                                    "and new_text.")
                            session.context.add_user(nudge)
                            self._emit({"type": "debug",
                                         "text": "Nudging agent to apply changes"})
                            continue

                        unfixed = self._get_unfixed_quality_warnings()
                        if unfixed and round_num <= 12:
                            parts = []
                            for fpath, warns in list(unfixed.items())[:2]:
                                fname = os.path.basename(fpath)
                                parts.append(
                                    f"{fname}: " + "; ".join(warns[:2]))
                            fix_nudge = (
                                "UNRESOLVED QUALITY ISSUES — fix these before "
                                "finishing:\n" + "\n".join(parts))
                            session.context.add_user(fix_nudge)
                            self._emit({"type": "debug",
                                         "text": "Nudging agent to fix quality issues"})
                            continue

                        if session.message_count >= 2:
                            unverified = self._get_unverified_writes()
                            if unverified and round_num <= 12:
                                verify_nudge = (
                                    f"You wrote {len(unverified)} file(s) but never "
                                    f"read them back to verify. Use read_file to "
                                    f"confirm ALL requested changes are present: "
                                    + ", ".join(os.path.basename(p) for p in unverified[:3]))
                                session.context.add_user(verify_nudge)
                                self._emit({"type": "debug",
                                             "text": "Nudging agent to verify written files"})
                                continue
                    elif tools and empty_retries < max_empty_retries:
                        empty_retries += 1
                        session.context.add_assistant(
                            "I understand. Let me take action now.")
                        retry_prompt = (
                            "Your last response was empty. Use edit_file "
                            "to create/update files, or exec to run commands. "
                            "Take action NOW — call a tool.")
                        session.context.add_user(retry_prompt)
                        self._emit({"type": "debug",
                                     "text": f"Empty response retry {empty_retries}/{max_empty_retries}"})
                        round_num -= 1
                        continue
                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": tool_calls_accum,
                }
                session.context.add_raw_message(assistant_msg)

                parallel_tcs = []
                linear_tcs = []
                PARALLEL_TOOLS = {"read_file", "search"}
                for tc in tool_calls_accum:
                    fn_name = tc.get("function", {}).get("name", "")
                    if fn_name in PARALLEL_TOOLS:
                        parallel_tcs.append(tc)
                    else:
                        linear_tcs.append(tc)

                tool_results_map: Dict[str, dict] = {}

                if parallel_tcs and len(parallel_tcs) > 1:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(
                            max_workers=min(4, len(parallel_tcs))) as pool:
                        futures = {
                            pool.submit(self._execute_tool_call, tc): tc
                            for tc in parallel_tcs
                        }
                        for fut in concurrent.futures.as_completed(futures):
                            tc = futures[fut]
                            tool_results_map[tc.get("id", "")] = fut.result()
                elif parallel_tcs:
                    tc = parallel_tcs[0]
                    tool_results_map[tc.get("id", "")] = self._execute_tool_call(tc)

                for tc in linear_tcs:
                    if self._cancel_requested:
                        self._cancel_requested = False
                        _was_cancelled = True
                        break
                    result = self._execute_tool_call(tc)
                    tool_results_map[tc.get("id", "")] = result
                    if not result.get("ok", True):
                        break

                if _was_cancelled:
                    break

                for tc in tool_calls_accum:
                    tool_id = tc.get("id", "")
                    result = tool_results_map.get(tool_id, {"output": "[skipped]"})
                    fn_name = tc.get("function", {}).get("name", "")
                    fn_args = tc.get("function", {}).get("arguments", "")
                    full_output = result.get("output", "")
                    context_output = self._truncate_tool_output(
                        fn_name, full_output, args_json=fn_args
                    )
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": context_output,
                    }
                    session.context.add_raw_message(tool_msg)

                    fn = tc.get("function", {})
                    call_sig = f"{fn.get('name','')}:{fn.get('arguments','')[:200]}"
                    _tool_call_history.append(call_sig)

                if tool_calls_accum and not full_text:
                    _silent_rounds += 1
                else:
                    _silent_rounds = 0
                if _silent_rounds >= 3:
                    session.context.add_user(
                        "[System] You made 3+ rounds of tool calls without "
                        "any explanatory text. Write a text response describing "
                        "what you've found so far. What is the current status?")
                    self._emit({"type": "debug",
                                 "text": "Nudging for text explanation"})
                    _silent_rounds = 0

                if len(_tool_call_history) >= 4:
                    recent = _tool_call_history[-4:]
                    unique_recent = set(recent)
                    if len(unique_recent) <= 2:
                        loop_nudge = (
                            "You are repeating the same tool calls. Stop reading "
                            "and SYNTHESIZE what you have learned so far. "
                            "Respond to the user with your findings now.")
                        session.context.add_user(loop_nudge)
                        self._emit({"type": "debug",
                                     "text": "Loop detected — nudging synthesis"})

                if (_is_unlimited
                        and round_num > 0
                        and round_num % ZOMBIE_CHECK_INTERVAL == 0):
                    _zombie_checks += 1
                    session.context.add_user(
                        f"[System: Round {round_num} check] You are running in "
                        "unlimited mode. Assess: is the original task complete? "
                        "If yes, call 'complete' now. If not, briefly state what "
                        "remains and continue. Do NOT repeat work already done.")
                    self._emit({"type": "debug",
                                 "text": f"Zombie check #{_zombie_checks} at round {round_num}"})

                if not _is_unlimited and turn_limit > 0 and round_num == turn_limit - 1:
                    session.context.add_user(
                        "[SYSTEM] Next round is the LAST. Finish all remaining "
                        "work in one more round and include a text summary.")
                    self._emit({"type": "debug",
                                 "text": f"Warning: round {round_num} is second-to-last"})

                if not _is_unlimited and turn_limit > 0 and round_num >= turn_limit:
                    if full_text:
                        session.context.add_assistant(full_text)
                    self._emit_file_summary()
                    _elapsed_s = round(time.time() - _turn_t0)
                    self._emit({"type": "complete", "reason": "round_limit",
                                "round": round_num, "turn_limit": turn_limit,
                                "elapsed_s": _elapsed_s})
                    self._mark_session_done(session_id, "round_limit")
                    if auto_title:
                        self._generate_title_async(session_id, text, full_text)
                    self._fire_hook("on_turn_end",
                                    session_id=session_id, round_count=round_num,
                                    tool_calls_count=len(_tool_call_history),
                                    status="round_limit")
                    return

            _elapsed_s = round(time.time() - _turn_t0)
            self._emit_file_summary()
            if _was_cancelled:
                self._emit({"type": "complete", "reason": "cancelled",
                            "round": round_num, "elapsed_s": _elapsed_s})
            elif turn_limit > 0 and round_num >= turn_limit:
                self._emit({"type": "complete", "reason": "round_limit",
                            "round": round_num, "turn_limit": turn_limit,
                            "elapsed_s": _elapsed_s})
            else:
                self._emit({"type": "complete", "elapsed_s": _elapsed_s})
            _done_reason = "cancelled" if _was_cancelled else (
                "round_limit" if (turn_limit > 0 and round_num >= turn_limit) else "done")
            self._fire_hook("on_turn_end",
                            session_id=session_id, round_count=round_num,
                            tool_calls_count=len(_tool_call_history),
                            status=_done_reason)
            self._mark_session_done(session_id, _done_reason)

            if auto_title:
                self._generate_title_async(session_id, text, full_text)

        except Exception as e:
            self._emit({"type": "system_notice", "text": f"Exception: {e}", "level": "error"})
            self._emit_file_summary()
            try:
                _err_elapsed = round(time.time() - _turn_t0)
            except NameError:
                _err_elapsed = 0
            self._emit({"type": "complete", "reason": "error",
                        "elapsed_s": _err_elapsed})
            self._fire_hook("on_turn_end",
                            session_id=session_id,
                            round_count=getattr(self, '_current_round', 0),
                            tool_calls_count=0, status="error")
            self._mark_session_done(session_id, "error")

    def _generate_title_async(self, session_id: str, user_msg: str, assistant_msg: str):
        """Generate a short title using the fast auto_generate_title interface."""
        session = self._sessions.get(session_id)
        if not session or session.title != "New Task":
            return
        try:
            from tool.LLM.logic.auto import auto_generate_title
            title = auto_generate_title(user_msg)
            if title and len(title) < 50:
                self.rename_session(session_id, title)
        except Exception as e:
            _log.debug("Auto-title generation failed for %s: %s", session_id, e)

    def generate_title(self, session_id: str) -> Optional[str]:
        """Synchronously generate and set a title. Returns the title or None."""
        session = self._sessions.get(session_id)
        if not session or session.message_count == 0:
            return None
        msgs = session.context.messages
        user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
        asst_msg = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
        if not user_msg:
            return None
        self._generate_title_async(session_id, user_msg, asst_msg)
        return self._sessions.get(session_id, Session(id="")).title

    # ── Verification ──

    def _get_unverified_writes(self) -> List[str]:
        """Return files that were written this turn but never read back."""
        writes = getattr(self, '_turn_writes', [])
        reads = set(getattr(self, '_turn_reads', []))
        return [w for w in writes if w not in reads]

    def _get_unfixed_quality_warnings(self) -> Dict[str, List[str]]:
        """Return quality warnings that haven't been resolved by a rewrite."""
        return dict(getattr(self, '_quality_warnings', {}))

    # ── Nudge Detection ──

    @staticmethod
    def _should_nudge(text: str, round_num: int = 0) -> bool:
        """Detect if the agent described code changes without applying them.

        Returns True if the text looks like a description of code changes
        (contains code blocks, file references, or change verbs) rather
        than a final answer to a question.
        """
        text_lower = text.lower()

        if round_num <= 1 and len(text) < 100:
            return True

        code_indicators = ["```", "def ", "class ", "import ",
                           "<html", "function ", "const "]
        has_code = any(ind in text_lower for ind in code_indicators)

        action_indicators = [
            "here's the updated", "here is the", "i would",
            "you can add", "modify", "change the",
            "update the", "replace", "add the following",
            "here's how",
            "我将", "首先创建", "接下来", "然后创建",
            "开始创建", "第一步", "第二步", "下面",
            "创建以下", "编写", "修改",
        ]
        has_action_desc = any(ind in text_lower for ind in action_indicators)

        applied_indicators = [
            "i've created", "i've updated", "i've fixed",
            "i have created", "i have updated", "done.",
            "file has been", "successfully",
            "已创建", "已完成", "已修改", "已写入", "创建完毕",
        ]
        already_applied = any(ind in text_lower for ind in applied_indicators)

        summary_indicators = [
            "summary", "analysis", "conclusion", "finding",
            "总结", "分析", "结论", "发现", "如果", "会怎样",
            "依赖链", "接口", "调用关系", "追踪",
        ]
        is_summary = any(ind in text_lower for ind in summary_indicators)
        if is_summary and len(text) > 150:
            return False

        return (has_code or has_action_desc) and not already_applied

    # ── Context Compression ──

    def _compress_context(self, session: Session):
        """Compress conversation context when it grows too large."""
        before_tokens = session.context._estimate_tokens()
        effective_limit = self._get_effective_context_limit()

        before_pct = (before_tokens / effective_limit * 100) if effective_limit else 0
        self._emit({"type": "notice", "level": "info",
                     "text": f"Summarizing context ({before_pct:.1f}%)...",
                     "id": "ctx-compress"})
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)
            prompt = session.context.build_compression_prompt(target_ratio=0.15)
            result = provider.send(
                session.context.get_messages_for_api() + [
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            if result.get("ok") and result.get("text"):
                summary = result["text"]
                session.context.apply_compression(summary)
                after_tokens = session.context._estimate_tokens()
                self._brain.on_session_end(session.id, summary)
                after_pct = (after_tokens / effective_limit * 100) if effective_limit else 0
                self._emit({"type": "notice", "level": "success",
                             "text": f"Chat context summarized ({before_pct:.1f}% → {after_pct:.1f}%)",
                             "id": "ctx-compress", "replace": True})
            else:
                self._emit({"type": "notice", "level": "warning",
                             "text": "Context compression returned empty result."})
        except Exception as e:
            self._emit({"type": "notice", "level": "warning",
                         "text": f"Context compression failed: {e}"})

    def _get_effective_context_limit(self) -> int:
        """Return effective context limit (max_ctx * compression_ratio)."""
        max_ctx = 0
        try:
            from tool.LLM.logic.registry import list_models
            for m in list_models():
                if any(self._provider_name.endswith(p) or p in self._provider_name
                       for p in [m["model"]]):
                    max_ctx = m.get("capabilities", {}).get("max_context_tokens", 0)
                    break
        except Exception:
            pass
        ratio = 0.5
        try:
            from tool.LLM.logic.config import get_config_value
            ratio = float(get_config_value("compression_ratio", 0.5))
        except Exception:
            pass
        return int(max_ctx * ratio) if max_ctx else 0

    # ── State Export ──

    def get_state(self) -> Dict[str, Any]:
        """Export full state for persistence or debugging."""
        max_ctx = 0
        try:
            from tool.LLM.logic.registry import list_models
            for m in list_models():
                if any(self._provider_name.endswith(p) or p in self._provider_name
                       for p in [m["model"]]):
                    max_ctx = m.get("capabilities", {}).get("max_context_tokens", 0)
                    break
        except Exception:
            pass
        compression_ratio = 0.5
        try:
            from tool.LLM.logic.config import get_config_value
            compression_ratio = float(get_config_value("compression_ratio", 0.5))
        except Exception:
            pass
        effective_limit = int(max_ctx * compression_ratio) if max_ctx else 0
        return {
            "provider": self._provider_name,
            "active_session": self._active_session_id,
            "max_context_tokens": max_ctx,
            "effective_context_limit": effective_limit,
            "compression_ratio": compression_ratio,
            "sessions": {
                sid: {
                    "id": s.id, "title": s.title, "status": s.status,
                    "message_count": s.message_count,
                    "context": s.context.to_dict(),
                }
                for sid, s in self._sessions.items()
            },
        }
