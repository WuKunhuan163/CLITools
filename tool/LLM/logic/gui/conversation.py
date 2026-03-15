"""GUI-agnostic conversation manager for LLM agent sessions.

Provides a stateful middle layer between any GUI (HTML, tkinter, CLI)
and the LLM provider. All GUIs call the same methods; events are
emitted via a callback for rendering.

Usage:
    from tool.LLM.logic.gui.conversation import ConversationManager

    mgr = ConversationManager(provider_name="zhipu-glm-4-flash")
    mgr.on_event(lambda evt: push_to_gui(evt))

    mgr.new_session("s1")
    mgr.send_message("s1", "Explain SSE in 3 sentences")
    # Events emitted: user → thinking → text → complete

    title = mgr.generate_title("s1")
"""
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from tool.LLM.logic.session_context import SessionContext


@dataclass
class Session:
    id: str
    title: str = "New Task"
    status: str = "idle"
    context: SessionContext = field(default_factory=SessionContext)
    created_at: float = field(default_factory=time.time)
    message_count: int = 0


BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Execute a shell command. Returns stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
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
            "description": "Search for files or text patterns in the project.",
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
]


class ConversationManager:
    """Stateful conversation orchestrator.

    All GUI variants (HTML, CLI, tkinter) use this same interface.
    Events are dispatched via ``on_event`` callback in the protocol
    format expected by ``AgentGUIEngine``.
    """

    def __init__(self, provider_name: str = "zhipu-glm-4-flash",
                 system_prompt: str = "",
                 enable_tools: bool = False,
                 sandbox_policy: str = "ask"):
        self._provider_name = provider_name
        self._system_prompt = system_prompt
        self._enable_tools = enable_tools
        self._sandbox_policy = sandbox_policy
        self._tool_handlers: Dict[str, Callable] = {}
        self._sessions: Dict[str, Session] = {}
        self._active_session_id: Optional[str] = None
        self._event_cb: Optional[Callable] = None
        self._lock = threading.Lock()

        if enable_tools:
            self._register_default_tool_handlers()

    def on_event(self, cb: Callable):
        """Register event callback: ``cb(event_dict)``."""
        self._event_cb = cb

    def _emit(self, evt: dict):
        if self._event_cb:
            self._event_cb(evt)

    # ── Tool Registration ──

    def register_tool(self, name: str, handler: Callable):
        """Register a custom tool handler: ``handler(args_dict) -> dict``."""
        self._tool_handlers[name] = handler

    def _register_default_tool_handlers(self):
        self._tool_handlers["exec"] = self._handle_exec
        self._tool_handlers["read_file"] = self._handle_read_file
        self._tool_handlers["todo"] = self._handle_todo
        self._tool_handlers["search"] = self._handle_search

    def _handle_exec(self, args: dict) -> dict:
        import subprocess
        cmd = args.get("command", "")
        self._emit({"type": "tool", "name": "exec", "desc": cmd, "cmd": cmd})
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'),
            )
            output = result.stdout + result.stderr
            ok = result.returncode == 0
            self._emit({"type": "tool_result", "ok": ok, "output": output[:2000]})
            return {"ok": ok, "output": output[:2000]}
        except subprocess.TimeoutExpired:
            self._emit({"type": "tool_result", "ok": False, "output": "Command timed out (30s)"})
            return {"ok": False, "output": "Timeout"}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            return {"ok": False, "output": str(e)}

    def _handle_read_file(self, args: dict) -> dict:
        path = args.get("path", "")
        self._emit({"type": "tool", "name": "read", "desc": path, "cmd": path})
        try:
            content = open(path).read()[:3000]
            self._emit({"type": "tool_result", "ok": True, "output": content})
            return {"ok": True, "output": content}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            return {"ok": False, "output": str(e)}

    def _handle_todo(self, args: dict) -> dict:
        action = args.get("action", "init")
        items = args.get("items", [])
        if action == "init":
            self._emit({"type": "todo", "items": items})
        elif action == "update":
            for item in items:
                self._emit({"type": "todo_update", "id": item.get("id"), "status": item.get("status")})
        elif action == "delete":
            for item in items:
                self._emit({"type": "todo_delete", "id": item.get("id")})
        return {"ok": True}

    def _handle_search(self, args: dict) -> dict:
        import subprocess
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        self._emit({"type": "tool", "name": "search", "desc": f"Search: {pattern}", "cmd": f"rg '{pattern}' {path}"})
        try:
            result = subprocess.run(
                ["rg", "--max-count", "10", "--no-heading", pattern, path],
                capture_output=True, text=True, timeout=15,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'),
            )
            output = result.stdout[:2000] or "(no matches)"
            self._emit({"type": "tool_result", "ok": True, "output": output})
            return {"ok": True, "output": output}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            return {"ok": False, "output": str(e)}

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """Execute a single tool call from the LLM."""
        import json as _json
        func = tool_call.get("function", {})
        name = func.get("name", "")
        try:
            args = _json.loads(func.get("arguments", "{}"))
        except Exception:
            args = {}

        handler = self._tool_handlers.get(name)
        if handler:
            return handler(args)
        self._emit({"type": "text", "tokens": f"Unknown tool: {name}"})
        return {"ok": False, "output": f"Unknown tool: {name}"}

    # ── Session Management ──

    def new_session(self, session_id: str = None, title: str = "New Task") -> str:
        sid = session_id or str(uuid.uuid4())[:8]
        ctx = SessionContext(system_prompt=self._system_prompt)
        with self._lock:
            self._sessions[sid] = Session(id=sid, title=title, context=ctx)
            if self._active_session_id is None:
                self._active_session_id = sid
        self._emit({"type": "session_created", "id": sid, "title": title})
        return sid

    def rename_session(self, session_id: str, new_title: str):
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.title = new_title
        self._emit({"type": "session_renamed", "id": session_id, "title": new_title})

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            if self._active_session_id == session_id:
                remaining = list(self._sessions.keys())
                self._active_session_id = remaining[-1] if remaining else None
        self._emit({"type": "session_deleted", "id": session_id})

    def set_active(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._active_session_id = session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"id": s.id, "title": s.title, "status": s.status,
             "message_count": s.message_count, "created_at": s.created_at}
            for s in self._sessions.values()
        ]

    # ── Conversation ──

    def send_message(self, session_id: str, text: str, blocking: bool = False):
        """Send a user message and get LLM response.

        If ``blocking`` is False, runs in a background thread.
        Events are emitted via the callback as they occur.
        """
        if blocking:
            self._run_turn(session_id, text)
        else:
            t = threading.Thread(target=self._run_turn,
                                 args=(session_id, text), daemon=True)
            t.start()

    def _run_turn(self, session_id: str, text: str):
        session = self._sessions.get(session_id)
        if not session:
            self._emit({"type": "error", "message": f"Session {session_id} not found"})
            return

        session.status = "running"
        session.message_count += 1
        self._emit({"type": "session_status", "id": session_id, "status": "running"})

        self._emit({"type": "user", "text": text})
        session.context.add_user(text)

        auto_title = session.message_count == 1 and session.title == "New Task"

        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)

            if not provider.is_available():
                self._emit({"type": "text", "tokens": f"Error: Provider {self._provider_name} is not available."})
                self._emit({"type": "complete"})
                session.status = "idle"
                self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                return

            tools = None
            if self._enable_tools and provider.capabilities.supports_tool_calling:
                tools = BUILTIN_TOOLS
            max_tool_rounds = 5
            round_num = 0

            while round_num < max_tool_rounds:
                round_num += 1
                full_text = ""
                tool_calls_accum = []

                for chunk in provider.stream(
                    session.context.get_messages_for_api(),
                    temperature=0.7,
                    max_tokens=2048,
                    tools=tools,
                ):
                    if chunk.get("ok"):
                        t = chunk.get("text", "")
                        if t:
                            full_text += t
                        tc = chunk.get("tool_calls")
                        if tc:
                            tool_calls_accum.extend(tc)
                        if chunk.get("done"):
                            if chunk.get("tool_calls"):
                                tool_calls_accum = chunk["tool_calls"]
                            break
                    else:
                        err = chunk.get("error", "Unknown error")
                        self._emit({"type": "text", "tokens": f"Error: {err}"})
                        self._emit({"type": "complete"})
                        session.status = "idle"
                        self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                        return

                if full_text:
                    session.context.add_assistant(full_text)
                    self._emit({"type": "text", "tokens": full_text})

                if not tool_calls_accum:
                    break

                import json as _json
                session.context.add_message("assistant", _json.dumps({"tool_calls": tool_calls_accum}))

                for tc in tool_calls_accum:
                    result = self._execute_tool_call(tc)
                    tool_id = tc.get("id", "")
                    session.context.add_message("tool", _json.dumps({
                        "tool_call_id": tool_id,
                        "content": result.get("output", ""),
                    }))

            self._emit({"type": "complete"})

            if auto_title:
                self._generate_title_async(session_id, text, full_text)

        except Exception as e:
            self._emit({"type": "text", "tokens": f"Exception: {e}"})
            self._emit({"type": "complete"})

        session.status = "done"
        self._emit({"type": "session_status", "id": session_id, "status": "done"})

    def _generate_title_async(self, session_id: str, user_msg: str, assistant_msg: str):
        """Generate a short title for the conversation."""
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)
            result = provider.send([
                {"role": "system", "content": "Generate a concise title (5-8 words max) for this conversation. Output ONLY the title, nothing else."},
                {"role": "user", "content": f"User: {user_msg[:200]}\nAssistant: {assistant_msg[:200]}"},
            ], temperature=0.3, max_tokens=30)
            if result.get("ok"):
                title = result["text"].strip().strip('"').strip("'")
                if title and len(title) < 80:
                    self.rename_session(session_id, title)
        except Exception:
            pass

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

    # ── State Export ──

    def get_state(self) -> Dict[str, Any]:
        """Export full state for persistence or debugging."""
        return {
            "provider": self._provider_name,
            "active_session": self._active_session_id,
            "sessions": {
                sid: {
                    "id": s.id, "title": s.title, "status": s.status,
                    "message_count": s.message_count,
                    "context": s.context.to_dict(),
                }
                for sid, s in self._sessions.items()
            },
        }
