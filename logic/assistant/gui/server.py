"""Live agent server for the LLM Agent GUI.

Wires ConversationManager → SSE → browser, with HTTP API endpoints
for message sending, session management, and automation control.

Usage:
    from logic.assistant.gui.server import start_server
    server = start_server(port=0)
    # → http://localhost:{port}/

RESTful API:

  Sessions:
    GET  /api/sessions                           List all sessions
    POST /api/sessions                           Create new session
    DELETE /api/sessions                          Clear all + create fresh

  Session (per-session):
    GET  /api/session/<sid>/state                 Session state
    GET  /api/session/<sid>/history               Event history
    POST /api/session/<sid>/send                  Send message
    POST /api/session/<sid>/cancel                Cancel running task
    POST /api/session/<sid>/rename                Rename session
    POST /api/session/<sid>/activate              Set as active
    DELETE /api/session/<sid>                      Delete session
    POST /api/session/<sid>/input                 Inject user input (GUI animation)
    POST /api/session/<sid>/inject                Inject single SSE event
    POST /api/session/<sid>/inject-batch          Inject multiple SSE events

  Edit blocks (per-session):
    GET  /api/session/<sid>/edit                  List edit blocks
    POST /api/session/<sid>/edit/<idx>            Accept/revert hunk

  Model:
    GET  /api/model/list                          Configured models
    POST /api/model/switch                        Switch model

  Keys:
    POST /api/key/validate                        Validate API key
    POST /api/key/save                            Save API key
    POST /api/key/delete                          Delete API key
    POST /api/key/states                          Get key states
    POST /api/key/reverify                        Reverify a key

  System:
    GET  /api/state                               Full system state
    GET  /api/usage                               Usage data

  Frontend-specific:
    POST /api/send {"_config":true,...}       Save config values
    POST /api/revert-hunk                     Text-based hunk revert
    POST /api/activate/<sid>                  Activate session
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

_dir = Path(__file__).resolve().parent
_root = _dir.parent.parent.parent
sys.path.insert(0, str(_root))

from logic.assistant.gui.round_store import (
    RoundStore, render_token_page, render_read_page,
    render_edit_page, _not_found_page
)

from tool.LLM.logic.task.agent.conversation import ConversationManager


_SYSTEM_PROMPT = """\
You are an autonomous AI Agent. You can independently plan, execute, and verify tasks.

## Available Tools

1. **exec(command=...)** — Run shell commands. For CLI tools, viewing files, installing deps.
2. **edit_file(path=..., start_line=..., end_line=..., new_text=...)** — Edit or create files. Two modes:
   - **Targeted edit**: Provide start_line, end_line, and new_text to replace lines [start_line, end_line] inclusive.
   - **Create new file**: Provide path and new_text only (no line params). Creates parent directories automatically.
3. **read_file(path=..., start_line=..., end_line=...)** — Read a range of lines from ONE file. start_line and end_line are REQUIRED. Best practice: use search() first to locate relevant line numbers, then read only the precise range you need.
4. **search(pattern=..., path=...)** — Search for text INSIDE files (grep-style). NOT for listing files. To list files, use exec(command="find <dir> -name '*.py'").
5. **todo(action=..., items=...)** — Manage a task list.
6. **ask_user(question=...)** — Ask the user a question for feedback.
7. **think(thought=...)** — Think step-by-step before acting. Use this when facing complex decisions, multi-step plans, or debugging. Write your reasoning as a structured analysis. The user sees your thinking process.

## Agent Workflow

When receiving a task, **use tools immediately**. Do NOT explore the project first — go straight to creating/modifying files.

1. **Act first**: If the task is clear (e.g., "create X file"), call edit_file immediately.
2. **Verify**: Optionally use read_file to confirm key content after writing
3. **Report**: Briefly summarize what was done

## Key Behaviors

- **Act immediately**: When asked to "create a file", your FIRST tool call should be edit_file.
- **Continuous execution**: After creating one file, immediately create the next. Don't stop to explain mid-way.
- **One call at a time**: Each tool call takes exactly ONE set of arguments. To read multiple files, call read_file separately for each file.
- **Complete output**: When creating a new file, new_text must contain complete, runnable code. No ellipsis or placeholders.
- **File creation**: A website needs HTML+CSS(+JS) files. Use edit_file to create all required files.
- **Tool discovery**: If the task requires external tools (search videos, fetch data), first use exec(command="TOOL --search tools-deep 'keywords'") to discover tools.
- **Self-repair**: If a command errors, read the source code to find the cause and fix it.
- **Follow ALL instructions**: Every specific change the user requests MUST appear in the written code. Before writing, mentally check each request.

## Cost-Efficient Editing (IMPORTANT)

**Always prefer edit_file with start_line/end_line for modifying existing files.** Output tokens are expensive. Line-range edits only output the changed portion, saving significant cost on large files.

- **Modifying existing files**: Use edit_file(path, start_line=N, end_line=M, new_text=<replacement>). First read_file to find exact line numbers, then replace only the lines that change.
- **Creating new files**: Use edit_file(path, new_text=<full file>) without line params. Only used for brand-new files.
- **Multiple changes to one file**: Make separate edit_file calls for each change. This is cheaper than rewriting the whole file.
- **NEVER rewrite an entire file** when you only need to change a few lines. A 500-line file with a 3-line fix should use start_line/end_line, not a full rewrite.

## Quality Standards

When creating web pages or UI:
- Use a distinctive color palette (NEVER use #333/#f5f5f5/#fff as primary colors)
- Use realistic sample content (real names, specific descriptions), never "placeholder" text
- CSS must include complete properties: padding, background-color, border-radius, transition
- Cards/sections need background colors, inner padding, and proper spacing
- Use Google Fonts or a quality font stack

When writing code:
- Include proper error handling
- Use meaningful variable names
- Add necessary imports

## File Modification Rules
- **Modify existing files**: ALWAYS use edit_file(start_line, end_line, new_text) for targeted changes. First read_file to find exact line numbers, then replace only the lines that change. This is MUCH cheaper than rewriting the whole file.
- **Create new files**: Use edit_file(path, new_text=<full content>) without line params. Content must be COMPLETE, runnable code.
- **Reading strategy**: ALWAYS use search() first to locate relevant code, then read_file with precise start_line/end_line to read only the needed range. Do NOT re-read the same file repeatedly.
- **Cost rule**: For a file with N lines where you change K lines, a targeted edit costs ~K tokens. A full rewrite costs ~N tokens. When K << N, targeted edit saves (N-K) output tokens.

### edit_file Example
If the file contains (lines 1-2):
```python
def hello():
    print("hello")
```
To add a parameter: edit_file(path="file.py", start_line=1, end_line=2, new_text='def hello(name):\\n    print(f"hello {name}")')
To append after line 2: edit_file(path="file.py", start_line=2, end_line=2, new_text='    print("hello")\\n\\ndef goodbye():\\n    print("bye")')

## Debugging Rules
- When tests fail, first determine whether the bug is in the test or the implementation. Pick ONE side to fix, don't oscillate between both.
- Before editing, use read_file to check the current file content and the full error message.
- After editing, immediately re-run tests to verify.
- assertIn(a, list) checks for exact element equality, NOT substring matching.

## Test Writing Rules
- Test expected values must exactly match the tool's documented behavior. If a tool is case-sensitive by default, test expectations must also be case-sensitive.
- `"".split("\n")` produces `[""]` (length 1), not `[]`. To check empty output, use `stdout.strip() == ""` instead of `len(lines) == 0`.
- Before writing a test, mentally simulate the tool's exact output for the test input. Verify character-by-character. Never assume.
- If a test fails for 2+ rounds, check whether the test's expected values are reasonable FIRST, then check the implementation.

## Handling User Corrections
- When the user gives specific fix instructions (e.g., "change X to Y"), **execute immediately**. Do NOT re-analyze the project.
- Every round MUST include at least one write/edit/exec action. Do NOT spend multiple rounds only reading files.
- If the user says "the test is unreasonable", fix the test directly. Do NOT try to fix the implementation to match unreasonable tests.

## Forbidden
- Never fabricate execution results
- Never say "I will create..." without actually calling edit_file
- Never use non-ASCII variable names in code
- Never claim you made a change that is not actually in the written code

## Response Guidelines (STRICT)
- Reply in English.
- **KEY RULE: Every response MUST contain text.** Even when making tool calls, you MUST write explanatory text BEFORE the tool call. Responses that contain only tool calls with no text are forbidden.
- If a search finds no results, immediately state your conclusion in text. Do NOT keep trying different variations. Maximum 2 search attempts.
- When your task is complete, you MUST write a text summary describing what you did, what you found, and the outcome. A task without a summary is considered incomplete.
- Before ending your turn, ensure ALL planned files have been created.
"""


def get_system_prompt(lang: str = "en") -> str:
    """Return the agent system prompt."""
    return _SYSTEM_PROMPT


AGENT_SYSTEM_PROMPT = _SYSTEM_PROMPT


class AgentServer:
    """Manages the live agent server lifecycle."""

    def __init__(
        self,
        provider_name: str = "zhipu-glm-4.7-flash",
        system_prompt: str = "",
        enable_tools: bool = True,
        port: int = 0,
        lang: str = "en",
        default_codebase: str = None,
        brain=None,
        scope_name: str = "TOOL",
    ):
        self.provider_name = provider_name
        self.system_prompt = system_prompt or get_system_prompt(lang)
        self.enable_tools = enable_tools
        self.port = port
        self.lang = lang
        self.default_codebase = default_codebase
        self.scope_name = scope_name

        self._mgr = ConversationManager(
            provider_name=provider_name,
            system_prompt=self.system_prompt,
            enable_tools=enable_tools,
            default_codebase=default_codebase,
            brain=brain,
        )
        self._server = None
        self._default_session_id = None
        self._usage_calls = []
        self._event_history: Dict[str, list] = {}  # session_id -> [events]
        self._round_store = RoundStore()
        self._mgr._event_provider = lambda sid: self._event_history.get(sid, [])
        self._mgr._round_store = self._round_store
        self._load_persisted_events()

    def _load_persisted_events(self):
        """Load event history from persisted session files.

        Supports both new layout (``<id>/history.json``) and legacy (``<id>.json``).
        Also reconstructs round store token data from persisted events.
        """
        import glob
        sessions_dir = os.path.join(str(_root), "runtime", "sessions")
        if not os.path.isdir(sessions_dir):
            return
        for path in glob.glob(os.path.join(sessions_dir, "*/history.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id")
                events = data.get("events", [])
                if sid and events:
                    self._event_history[sid] = events
                    self._reconstruct_round_store(sid, events)
            except Exception:
                continue
        for path in glob.glob(os.path.join(sessions_dir, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id")
                if sid and sid not in self._event_history:
                    events = data.get("events", [])
                    if events:
                        self._event_history[sid] = events
                        self._reconstruct_round_store(sid, events)
            except Exception:
                continue

    def _reconstruct_round_store(self, sid: str, events: list):
        """Rebuild round store token/file data from persisted events."""
        user_texts = []
        current_round = 0
        pending_tool = None
        read_counter = {}
        edit_counter = {}

        for evt in events:
            etype = evt.get("type")
            if etype == "user":
                user_texts.append(evt.get("prompt", evt.get("text", "")))
            elif etype == "llm_request":
                current_round = evt.get("round", current_round)
            elif etype == "llm_response_end":
                round_num = evt.get("round", 0)
                if not round_num:
                    continue
                current_round = round_num
                output = evt.get("_full_text", "")
                input_text = "\n\n---\n\n".join(user_texts) if user_texts else ""
                self._round_store.record_round(
                    sid, round_num,
                    input_tokens=input_text,
                    output_tokens=output,
                )
            elif etype == "tool":
                name = evt.get("name", "")
                if name == "read":
                    path = evt.get("cmd", "")
                    pending_tool = {"name": "read", "path": path}
                elif name in ("edit_file", "write_file"):
                    pending_tool = {"name": name}
            elif etype == "tool_result" and pending_tool:
                if pending_tool["name"] == "read" and evt.get("ok"):
                    path = pending_tool.get("path", "")
                    if path:
                        rel = os.path.basename(path)
                        try:
                            cwd = os.getcwd()
                            rel = os.path.relpath(path, cwd) if os.path.isabs(path) else path
                        except ValueError:
                            rel = path
                        rkey = (current_round, rel)
                        op_id = read_counter.get(rkey, 0)
                        read_counter[rkey] = op_id + 1
                        self._round_store.record_file_op(
                            sid, current_round, "read", rel,
                            content=evt.get("output", ""),
                            op_id=op_id)
                pending_tool = None

    def _api_handler(self, method: str, path: str, body: Optional[dict]) -> dict:
        """Route API requests — RESTful paths with legacy aliases."""
        path = path.split("?")[0]
        body = body or {}
        import re as _re

        # ── /api/session/<sid>/... ──────────────────────────────
        _ses_match = _re.match(r'/api/session/([^/]+)(?:/(.+))?$', path)
        if _ses_match:
            sid = _ses_match.group(1)
            if sid == "default":
                sid = self._default_session_id or ""
            sub = (_ses_match.group(2) or "").strip("/")
            return self._route_session(method, sid, sub, body)

        # ── /api/sessions ──────────────────────────────────────
        if path == "/api/sessions":
            if method == "GET":
                return {"ok": True, "sessions": self._mgr.list_sessions()}
            elif method == "POST":
                return self._api_create_session(body)
            elif method == "DELETE":
                return self._api_clear_all()

        # ── /api/model/... ─────────────────────────────────────
        if path == "/api/model/list" or path == "/api/configured_models":
            return self._get_configured_models()
        if path in ("/api/model/switch", "/api/model"):
            return self._api_switch_model(body)

        # ── /api/key/... ───────────────────────────────────────
        if path in ("/api/key/validate", "/api/validate-key"):
            return self._api_validate_key(body)
        if path in ("/api/key/save", "/api/save-key"):
            return self._api_save_key(body)
        if path in ("/api/key/delete", "/api/delete-key"):
            return self._api_delete_key(body)
        if path in ("/api/key/states", "/api/key-states"):
            return self._api_key_states(body)
        if path in ("/api/key/reverify", "/api/reverify-key"):
            return self._api_reverify_key(body)
        if path == "/api/provider/status":
            return self._api_provider_status(body)

        # ── System ─────────────────────────────────────────────
        if path == "/api/state":
            state = self._mgr.get_state()
            state["scope_name"] = self.scope_name
            return {"ok": True, "state": state}
        if path == "/api/scope":
            return {"ok": True, "scope_name": self.scope_name}
        if path == "/api/usage":
            return {"ok": True, "usage": self._get_usage_data()}
        if path == "/api/session_config" and method == "GET":
            return self._get_session_config()
        if path == "/api/currencies":
            return self._get_currencies()
        if path == "/api/file-lines" and method == "POST":
            return self._read_file_lines(body)

        # ── Settings panel control ──
        if path == "/api/settings/open" and method == "POST":
            tab = body.get("tab", "")
            self._push_sse({"type": "settings_open", "tab": tab})
            return {"ok": True, "tab": tab}
        if path == "/api/settings/close" and method == "POST":
            self._push_sse({"type": "settings_close"})
            return {"ok": True}

        # ── Essential frontend routes (config saves, text-based revert) ──
        if method == "POST":
            if path == "/api/send" and body.get("_config"):
                return self._save_session_config(body.get("key"), body.get("value"))
            if path == "/api/revert-hunk":
                return self._revert_hunk(body)
            if path.startswith("/api/activate/"):
                sid = path.split("/api/activate/")[1].strip("/")
                return self._api_activate(sid)

        return {"ok": False, "error": f"Unknown endpoint: {method} {path}"}

    def _route_session(self, method: str, sid: str, sub: str, body: dict) -> dict:
        """Route /api/session/<sid>/<sub> requests."""
        import re as _re

        if not sub:
            if method == "GET":
                return self._api_session_state(sid)
            elif method == "DELETE":
                return self._api_delete_session(sid)

        if sub == "state":
            return self._api_session_state(sid)
        if sub == "history":
            events = self._event_history.get(sid, [])
            return {"ok": True, "events": events}
        if sub == "send":
            return self._api_send(sid, body)
        if sub == "cancel":
            return self._api_cancel(sid)
        if sub == "rename":
            return self._api_rename(sid, body)
        if sub == "activate":
            return self._api_activate(sid)
        if sub == "input":
            return self._api_input(sid, body)
        if sub == "inject":
            return self._api_inject_event(sid, body)
        if sub == "inject-batch":
            return self._api_inject_events(sid, body)
        if sub == "queue":
            return self._api_queue(sid, body)

        # /api/session/<sid>/edit[/<idx>]
        _edit_m = _re.match(r'edit(?:/(\d+))?$', sub)
        if _edit_m:
            idx = _edit_m.group(1)
            if method == "GET" and idx is None:
                return self._list_edit_blocks(sid)
            elif method == "POST" and idx is not None:
                action = body.get("action", "accept")
                if action == "revert":
                    return self._revert_hunk({"session_id": sid, "hunk_index": int(idx)})
                return self._accept_hunk({"session_id": sid, "hunk_index": int(idx)})

        # Legacy: edit-blocks[/<idx>]
        _eb_m = _re.match(r'edit-blocks(?:/(\d+))?$', sub)
        if _eb_m:
            idx = _eb_m.group(1)
            if method == "GET" and idx is None:
                return self._list_edit_blocks(sid)
            elif method == "POST" and idx is not None:
                action = body.get("action", "accept")
                if action == "revert":
                    return self._revert_hunk({"session_id": sid, "hunk_index": int(idx)})
                return self._accept_hunk({"session_id": sid, "hunk_index": int(idx)})

        return {"ok": False, "error": f"Unknown session endpoint: {sub}"}

    # ── API Implementation Methods ───────────────────────────────

    def _api_session_state(self, sid: str) -> dict:
        session = self._mgr.get_session(sid)
        if not session:
            return {"ok": False, "error": f"Session {sid} not found"}
        return {"ok": True, "id": sid, "title": session.title,
                "status": session.status,
                "message_count": len(getattr(session, 'messages', []))}

    def _api_send(self, sid: str, body: dict) -> dict:
        text = (body.get("text") or body.get("prompt") or "").strip()
        if not sid:
            return {"ok": False, "error": "No active session"}
        if not text:
            return {"ok": False, "error": "Empty message"}
        session = self._mgr.get_session(sid)
        if not session:
            return {"ok": False, "error": f"Session {sid} not found"}
        context_feed = body.get("context_feed")
        raw_tl = body.get("turn_limit")
        turn_limit = int(raw_tl) if raw_tl is not None else -1
        self._mgr.send_message(sid, text, blocking=False,
                               context_feed=context_feed,
                               turn_limit=turn_limit)
        return {"ok": True, "session_id": sid}

    def _api_input(self, sid: str, body: dict) -> dict:
        text = body.get("text", "").strip()
        if not sid or not text:
            return {"ok": False, "error": "Missing session_id or text"}
        self._push_sse({"type": "inject_input", "session_id": sid, "text": text})
        return {"ok": True, "session_id": sid}

    def _api_switch_model(self, body: dict) -> dict:
        model = body.get("model", "").strip()
        if not model:
            return {"ok": False, "error": "Missing model"}
        if model != "auto":
            try:
                from tool.LLM.logic.registry import get_provider
                provider = get_provider(model)
                if not provider.is_available():
                    return {"ok": False, "error": f"Model {model} is not available"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        old_model = self._mgr._provider_name
        self._mgr._provider_name = model
        self.provider_name = model
        try:
            from tool.LLM.logic.auto import get_health
            get_health().mark_user_selected(model)
        except Exception:
            pass
        self._push_sse({"type": "model_switched", "from": old_model, "to": model})
        return {"ok": True, "model": model}

    def _api_create_session(self, body: dict) -> dict:
        title = body.get("title", "New Task")
        codebase = body.get("codebase_root")
        mode = body.get("mode", "agent")
        sid = self._mgr.new_session(title=title, codebase_root=codebase, mode=mode)
        self._default_session_id = sid
        pre_events = body.get("events", [])
        if pre_events:
            if sid not in self._event_history:
                self._event_history[sid] = []
            for evt in pre_events:
                evt["session_id"] = sid
                for k, v in list(evt.items()):
                    if v == "__SID__":
                        evt[k] = sid
                self._event_history[sid].append(evt)
                if evt.get("type") == "session_status":
                    s = self._mgr.get_session(sid)
                    if s:
                        s.status = evt.get("status", s.status)
        self_operate = body.get("self_operate", False)
        self._push_sse({"type": "session_created", "id": sid, "title": title,
                        "mode": mode, "self_operate": self_operate})
        for evt in pre_events:
            self._push_sse(evt)
        return {"ok": True, "session_id": sid}

    def _api_rename(self, sid: str, body: dict) -> dict:
        title = body.get("title", "")
        if sid and title:
            self._mgr.rename_session(sid, title)
            return {"ok": True}
        return {"ok": False, "error": "Missing session_id or title"}

    def _api_delete_session(self, sid: str) -> dict:
        if not sid:
            return {"ok": False, "error": "Missing session_id"}
        self._mgr.delete_session(sid)
        if sid in self._event_history:
            del self._event_history[sid]
        remaining = self._mgr.list_sessions()
        self._push_sse({"type": "session_deleted", "id": sid})
        if remaining:
            self._default_session_id = remaining[-1]["id"]
        else:
            new_sid = self._mgr.new_session(title="New Task")
            self._default_session_id = new_sid
            self._push_sse({"type": "session_created", "id": new_sid,
                            "title": "New Task"})
        return {"ok": True}

    def _api_clear_all(self) -> dict:
        sessions = self._mgr.list_sessions()
        deleted = 0
        for s in sessions:
            sid = s["id"]
            self._mgr.delete_session(sid)
            if sid in self._event_history:
                del self._event_history[sid]
            self._push_sse({"type": "session_deleted", "id": sid})
            deleted += 1
        self._default_session_id = None
        new_sid = self._mgr.new_session(title="New Task")
        self._default_session_id = new_sid
        self._push_sse({"type": "session_created", "id": new_sid, "title": "New Task"})
        return {"ok": True, "deleted": deleted, "new_session": new_sid}

    def _api_activate(self, sid: str) -> dict:
        session = self._mgr.get_session(sid)
        if not session:
            return {"ok": False, "error": f"Session {sid} not found"}
        self._mgr.set_active(sid)
        self._default_session_id = sid
        return {"ok": True, "session_id": sid,
                "title": session.title, "status": session.status}

    def _api_cancel(self, sid: str) -> dict:
        self._mgr.cancel_current()
        return {"ok": True}

    def _api_validate_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key = body.get("key", "").strip()
        if not vendor or not key:
            return {"ok": False, "error": "Missing vendor or key"}
        return self._validate_api_key(vendor, key)

    def _api_save_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key = body.get("key", "").strip()
        if not vendor or not key:
            return {"ok": False, "error": "Missing vendor or key"}
        from tool.LLM.logic.config import set_config_value
        set_config_value(f"{vendor}_api_key", key)
        self._push_sse({"type": "settings_changed", "action": "key_saved", "vendor": vendor})
        return {"ok": True}

    def _api_delete_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        if not vendor:
            return {"ok": False, "error": "Missing vendor"}
        from tool.LLM.logic.config import set_config_value
        set_config_value(f"{vendor}_api_key", "")
        self._push_sse({"type": "settings_changed", "action": "key_deleted", "vendor": vendor})
        return {"ok": True}

    def _api_key_states(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        if not vendor:
            return {"ok": False, "error": "Missing vendor"}
        from tool.LLM.logic.key_state import get_selector
        sel = get_selector(vendor)
        return {"ok": True, "states": sel.get_all_states(),
                "has_usable": sel.has_usable_keys(),
                "active_count": sel.get_active_count()}

    def _api_reverify_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key_id = body.get("key_id", "").strip()
        if not vendor or not key_id:
            return {"ok": False, "error": "Missing vendor or key_id"}
        from tool.LLM.logic.key_state import get_selector
        sel = get_selector(vendor)
        result = sel.reverify(key_id)
        if result.get("ok"):
            self._push_sse({"type": "settings_changed",
                            "action": "key_reverified", "vendor": vendor,
                            "key_id": key_id})
        return result

    def _api_provider_status(self, body: dict) -> dict:
        """Return unified provider status from ProviderManager.

        Optional body params:
        - provider: single provider name (returns that provider only)
        - (no params): returns full snapshot of all providers
        """
        provider_name = body.get("provider", "").strip()
        try:
            from tool.LLM.logic.provider_manager import get_manager
            mgr = get_manager()
            if provider_name:
                return {"ok": True, "status": mgr.get_provider_status(provider_name)}
            return {"ok": True, "snapshot": mgr.get_full_snapshot()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_queue(self, sid: str, body: dict) -> dict:
        action = body.get("action", "list")
        if not sid:
            return {"ok": False, "error": "No active session"}
        if action == "list":
            queue = self._mgr.get_task_queue(sid)
            return {"ok": True, "queue": [
                {"text": t.get("text", "")[:100]} for t in queue]}
        elif action == "clear":
            count = self._mgr.clear_task_queue(sid)
            return {"ok": True, "cleared": count}
        return {"ok": False, "error": f"Unknown queue action: {action}"}

    def _api_inject_event(self, sid: str, body: dict) -> dict:
        event = body.get("event")
        if not sid:
            return {"ok": False, "error": "No active session"}
        if not event or not isinstance(event, dict):
            return {"ok": False, "error": "Missing or invalid event"}
        event["session_id"] = sid
        if sid not in self._event_history:
            self._event_history[sid] = []
        self._event_history[sid].append(event)
        if event.get("type") == "session_status":
            s = self._mgr.get_session(sid)
            if s:
                s.status = event.get("status", s.status)
        self._push_sse(event)
        self._maybe_record_injected_round(sid, event)
        return {"ok": True}

    def _api_inject_events(self, sid: str, body: dict) -> dict:
        events = body.get("events", [])
        if not sid:
            return {"ok": False, "error": "No active session"}
        if not isinstance(events, list):
            return {"ok": False, "error": "events must be a list"}
        if sid not in self._event_history:
            self._event_history[sid] = []
        for evt in events:
            if isinstance(evt, dict):
                evt["session_id"] = sid
                self._event_history[sid].append(evt)
                self._push_sse(evt)
                self._maybe_record_injected_round(sid, evt)
        return {"ok": True, "count": len(events)}

    @staticmethod
    def _validate_api_key(vendor: str, key: str) -> dict:
        """Validate an API key by making a minimal test request.

        On success, reactivates the key if it was previously stale.
        On auth failure, marks the key as stale.
        """
        VENDOR_PROVIDERS = {
            "zhipu": "zhipu-glm-4.7-flash",
            "google": "google-gemini-2.0-flash",
            "baidu": "baidu-ernie-speed-8k",
            "tencent": "tencent-hunyuan-lite",
            "siliconflow": "siliconflow-qwen2.5-7b",
            "nvidia": "nvidia-glm-4-7b",
        }
        provider_name = VENDOR_PROVIDERS.get(vendor)
        if not provider_name:
            return {"ok": False, "error": f"Unknown vendor: {vendor}"}
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(provider_name, api_key=key)
            result = provider._send_request(
                [{"role": "user", "content": "hi"}],
                temperature=0.1, max_tokens=5)

            try:
                from tool.LLM.logic.key_state import get_selector
                from tool.LLM.logic.config import get_api_keys
                sel = get_selector(vendor)
                keys = get_api_keys(vendor)
                key_id = next((k["id"] for k in keys if k["key"] == key), None)
                if key_id:
                    sel.report(key_id, result)
                    if result.get("ok") or result.get("error_code") == 429:
                        state = sel._states.get(key_id)
                        if state and state.status == "stale":
                            state.reactivate()
                            sel._save()
            except Exception:
                pass

            if result.get("ok"):
                return {"ok": True, "model": result.get("model", provider_name)}
            if result.get("error_code") == 429:
                return {"ok": True, "model": result.get("model", provider_name),
                        "warning": "Key valid but rate limited (429). Quota may be exhausted."}
            if result.get("error_code") in (401, 403):
                return {"ok": False, "error": "Invalid API key (authentication failed)"}
            return {"ok": False, "error": result.get("error", "Validation failed")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _push_sse(self, evt: dict):
        if self._server:
            self._server.push_event(evt)

    def _maybe_record_injected_round(self, sid: str, evt: dict):
        """Record round data in round_store for injected events (self-operate)."""
        if evt.get("type") != "llm_response_end":
            return
        round_num = evt.get("round", 0)
        if not round_num:
            return
        history = self._event_history.get(sid, [])
        input_parts = []
        output_text = evt.get("_full_text", "")
        for h in history:
            if h.get("type") == "user":
                input_parts.append(h.get("prompt", h.get("text", "")))
            elif h.get("type") == "llm_request" and h.get("round") == round_num:
                feed = h.get("context_feed")
                if feed:
                    input_parts.append(json.dumps(feed, ensure_ascii=False, indent=1))
        if not output_text:
            for h in history:
                if h.get("type") == "text" and not h.get("_recorded"):
                    output_text += h.get("tokens", "")
        self._round_store.record_round(
            sid, round_num,
            input_tokens="\n\n---\n\n".join(input_parts) if input_parts else "",
            output_tokens=output_text,
        )

    def _on_mgr_event(self, evt: dict):
        """Forward ConversationManager events to SSE, track usage, and store history."""
        sid = self._mgr._current_turn_session_id or self._default_session_id
        if sid:
            evt["session_id"] = sid
            if evt.get("type") != "tool_stream_delta":
                if sid not in self._event_history:
                    self._event_history[sid] = []
                self._event_history[sid].append(evt)

        if evt.get("type") == "llm_response_end":
            round_num = evt.get("round", 0)
            if sid and round_num:
                session = self._mgr.get_session(sid)
                ctx_msgs = session.context.messages if session else []
                self._round_store.record_round(
                    sid, round_num,
                    input_tokens=json.dumps(ctx_msgs[-20:], ensure_ascii=False, indent=1) if ctx_msgs else "",
                    output_tokens=evt.get("_full_text", ""),
                    context_messages=ctx_msgs,
                )

            import time
            try:
                from interface.utils import get_rate
                usd_rate = get_rate("CNY")
            except Exception:
                usd_rate = 7.25
            self._usage_calls.append({
                "timestamp": time.time(),
                "model": evt.get("model", self.provider_name),
                "provider": evt.get("provider", self.provider_name),
                "input_tokens": evt.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": evt.get("usage", {}).get("completion_tokens", 0),
                "latency_s": evt.get("latency_s", 0),
                "ok": not evt.get("error"),
                "exchange_rate_cny": usd_rate,
            })
        self._push_sse(evt)

    def _get_configured_models(self) -> dict:
        """Return models that have at least one configured+available provider."""
        try:
            from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers
            available_providers = set()
            for p in list_reg_providers():
                if p.get("available"):
                    available_providers.add(p.get("name", ""))

            configured = [{"value": "auto", "label": "Auto"}]
            for m in list_models():
                mid = m["model"]
                provs = m.get("providers", [])
                if any(p in available_providers for p in provs):
                    configured.append({
                        "value": mid,
                        "label": m.get("display_name", mid),
                    })
            return {"ok": True, "models": configured}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _revert_hunk(self, body: dict) -> dict:
        """Revert a single diff hunk by applying the inverse edit."""
        path = body.get("path", "").strip()
        old_text = body.get("old_text", "")
        new_text = body.get("new_text", "")
        hunk_index = body.get("hunk_index")
        session_id = body.get("session_id") or self._default_session_id

        if hunk_index is not None and session_id:
            return self._revert_hunk_by_index(session_id, hunk_index)

        if not path:
            return {"ok": False, "error": "Missing path"}

        import os
        if not os.path.isabs(path):
            cwd = self._mgr._get_cwd() if hasattr(self._mgr, '_get_cwd') else os.getcwd()
            path = os.path.join(cwd, path)

        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            if old_text and old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self._push_sse({"type": "hunk_reverted", "path": path,
                                "session_id": session_id})
                return {"ok": True, "path": path}
            elif not old_text and new_text:
                return {"ok": False, "error": "Cannot revert: added text not found in file"}
            else:
                return {"ok": False, "error": "Text to revert not found in file"}
        except FileNotFoundError:
            return {"ok": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _accept_hunk(self, body: dict) -> dict:
        """Accept (keep) a diff hunk — marks it decided without changing the file."""
        hunk_index = body.get("hunk_index")
        session_id = body.get("session_id") or self._default_session_id
        if hunk_index is None:
            return {"ok": False, "error": "Missing hunk_index"}

        blocks = self._get_edit_blocks(session_id)
        if hunk_index < 0 or hunk_index >= len(blocks):
            return {"ok": False, "error": f"hunk_index {hunk_index} out of range (0..{len(blocks)-1})"}

        block = blocks[hunk_index]
        if block.get("decided"):
            return {"ok": False, "error": f"Hunk {hunk_index} already decided as {block.get('decision')}"}

        block["decided"] = True
        block["decision"] = "accepted"
        self._push_sse({"type": "hunk_accepted", "hunk_index": hunk_index,
                        "path": block.get("path", ""), "session_id": session_id})
        return {"ok": True, "hunk_index": hunk_index, "path": block.get("path", "")}

    def _revert_hunk_by_index(self, session_id: str, hunk_index: int) -> dict:
        """Revert a hunk identified by its chronological index."""
        import os
        blocks = self._get_edit_blocks(session_id)
        if hunk_index < 0 or hunk_index >= len(blocks):
            return {"ok": False, "error": f"hunk_index {hunk_index} out of range (0..{len(blocks)-1})"}

        block = blocks[hunk_index]
        if block.get("decided"):
            return {"ok": False, "error": f"Hunk {hunk_index} already decided as {block.get('decision')}"}

        path = block.get("path", "")
        old_text = block.get("new_text", "")
        new_text = block.get("old_text", "")

        if not path:
            return {"ok": False, "error": "No path in hunk"}

        if not os.path.isabs(path):
            cwd = self._mgr._get_cwd() if hasattr(self._mgr, '_get_cwd') else os.getcwd()
            path = os.path.join(cwd, path)

        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            if old_text and old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                block["decided"] = True
                block["decision"] = "reverted"
                self._push_sse({"type": "hunk_reverted", "hunk_index": hunk_index,
                                "path": path, "session_id": session_id})
                return {"ok": True, "hunk_index": hunk_index, "path": path}
            else:
                return {"ok": False, "error": "Text to revert not found in file (file may have changed)"}
        except FileNotFoundError:
            return {"ok": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_edit_blocks(self, session_id: str) -> list:
        """Return all edit blocks for a session, rebuilding from history each time."""
        if not hasattr(self, '_edit_blocks'):
            self._edit_blocks = {}
        old_blocks = self._edit_blocks.get(session_id, [])
        self._build_edit_blocks(session_id, old_blocks)
        return self._edit_blocks.get(session_id, [])

    def _build_edit_blocks(self, session_id: str, old_blocks: list = None):
        """Scan event history and build edit block list, preserving decision state."""
        events = self._event_history.get(session_id, [])
        old_decisions = {}
        if old_blocks:
            for b in old_blocks:
                if b.get("decided"):
                    key = (b.get("path", ""), b.get("old_text", "")[:50], b.get("new_text", "")[:50])
                    old_decisions[key] = b.get("decision")

        blocks = []
        for evt in events:
            if evt.get("type") == "tool_result" and evt.get("name") in ("edit_file", "write_file"):
                if not evt.get("ok"):
                    continue
                path = evt.get("_path", evt.get("path", ""))
                old_text = evt.get("_old_text", "")
                new_text = evt.get("_new_text", "")
                key = (path, old_text[:50], new_text[:50])
                decided = key in old_decisions
                decision = old_decisions.get(key)
                block = {
                    "index": len(blocks),
                    "tool": evt.get("name"),
                    "path": path,
                    "old_text": old_text,
                    "new_text": new_text,
                    "decided": decided,
                    "decision": decision,
                }
                blocks.append(block)
        if not hasattr(self, '_edit_blocks'):
            self._edit_blocks = {}
        self._edit_blocks[session_id] = blocks

    def _list_edit_blocks(self, session_id: str) -> dict:
        """Return edit blocks for CLI inspection."""
        if not session_id:
            return {"ok": False, "error": "No active session"}
        blocks = self._get_edit_blocks(session_id)
        summary = []
        for b in blocks:
            summary.append({
                "index": b["index"],
                "tool": b["tool"],
                "path": b.get("path", ""),
                "decided": b["decided"],
                "decision": b.get("decision"),
                "old_text_preview": (b.get("old_text", "") or "")[:80],
                "new_text_preview": (b.get("new_text", "") or "")[:80],
            })
        return {"ok": True, "blocks": summary, "count": len(summary)}

    def _read_file_lines(self, body: dict) -> dict:
        """Read specific lines from a file for streaming edit preview."""
        fpath = body.get("path", "")
        start = int(body.get("start", 1))
        end = int(body.get("end", start))
        if not fpath:
            return {"ok": False, "error": "Missing path"}
        try:
            if not os.path.isabs(fpath):
                fpath = os.path.join(os.getcwd(), fpath)
            with open(fpath, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            s = max(1, min(start, total))
            e = min(end, total)
            lines = [l.rstrip("\n") for l in all_lines[s-1:e]]
            return {"ok": True, "lines": lines, "total": total,
                    "start": s, "end": e}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _save_session_config(self, key, value) -> dict:
        """Save a single session config key from the frontend settings panel."""
        if not key:
            return {"ok": False, "error": "Missing key"}
        try:
            from tool.LLM.logic.config import load_config, save_config
            cfg = load_config()
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except (ValueError, TypeError):
                pass
            cfg[key] = value
            save_config(cfg)
            return {"ok": True, "key": key, "value": value}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_session_config(self) -> dict:
        """Return session configuration defaults from the LLM config store."""
        try:
            from tool.LLM.logic.config import get_config_value
            SESSION_DEFAULTS = {
                "default_turn_limit": 20,
                "max_read_chars": 16384,
                "max_exec_chars": 8192,
                "max_edit_chars": 8192,
                "history_round_limit": 64,
                "debug_tokens_round_limit": 64,
                "compression_ratio": 0.5,
            }
            config = {}
            for key, default in SESSION_DEFAULTS.items():
                val = get_config_value(key, default)
                try:
                    config[key] = int(val)
                except (ValueError, TypeError):
                    config[key] = default
            return {"ok": True, "config": config}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @staticmethod
    def _get_currencies() -> dict:
        try:
            from interface.utils import list_currencies
            currencies = list_currencies()
            top_codes = ["USD", "EUR", "GBP", "CNY", "JPY", "KRW", "INR",
                         "CAD", "AUD", "CHF", "HKD", "SGD", "TWD", "BRL"]
            top = [c for c in currencies if c["code"] in top_codes]
            top.sort(key=lambda c: top_codes.index(c["code"]))
            rest = [c for c in currencies if c["code"] not in top_codes]
            return {"ok": True, "currencies": top + rest, "top_codes": top_codes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_usage_data(self) -> dict:
        """Aggregate usage data for Settings panel."""
        models = {}
        providers = {}
        from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers
        from tool.LLM.logic.config import get_api_keys
        from interface.utils import to_usd, get_rates
        rates = get_rates()

        for m in list_models():
            mid = m["model"]
            cap = m.get("capabilities", {})
            model_json_path = os.path.join(
                str(_root), "tool", "LLM", "logic", "models",
                mid.replace("-", "_").replace(".", "_"), "model.json")
            cost_info = {}
            bench_info = {}
            free_tier = False
            if os.path.exists(model_json_path):
                try:
                    with open(model_json_path) as f:
                        mj = json.load(f)
                    cost_info = mj.get("cost", {})
                    bench_info = mj.get("benchmarks", {})
                    free_tier = cost_info.get("free_tier", False)
                except Exception:
                    pass
            orig_currency = cost_info.get("currency", "USD")
            raw_input = cost_info.get("input_per_1m", cost_info.get("input_per_1k", 0) * 1000)
            raw_output = cost_info.get("output_per_1m", cost_info.get("output_per_1k", 0) * 1000)
            models[mid] = {
                "display_name": m.get("display_name", mid),
                "providers": m.get("providers", []),
                "capabilities": cap,
                "free_tier": free_tier,
                "input_price": to_usd(raw_input, orig_currency, rates),
                "output_price": to_usd(raw_output, orig_currency, rates),
                "currency": "USD",
                "benchmarks": bench_info,
                "total_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
            }

        available_providers = set()
        for p in list_reg_providers():
            pname = p.get("name", "")
            if pname == "auto":
                continue
            vendor = pname.split("-")[0] if pname else "unknown"
            if vendor not in providers:
                providers[vendor] = {
                    "models": [], "total_calls": 0,
                    "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
                    "api_keys": [],
                }
            if pname not in providers[vendor]["models"]:
                providers[vendor]["models"].append(pname)
            try:
                keys = get_api_keys(vendor)
                try:
                    from tool.LLM.logic.key_state import get_selector
                    sel = get_selector(vendor)
                    states = sel.get_all_states()
                    for k in keys:
                        st = states.get(k["id"], {})
                        k["state"] = st.get("status", "active")
                        k["state_reason"] = st.get("reason", "")
                except Exception:
                    pass
                providers[vendor]["api_keys"] = keys
                if keys:
                    available_providers.add(pname)
                    providers[vendor]["configured"] = True
            except Exception:
                pass

        for mid, mdata in models.items():
            mdata["configured"] = any(p in available_providers for p in mdata.get("providers", []))
            mdata["configured_providers"] = [p for p in mdata.get("providers", []) if p in available_providers]

        try:
            from tool.ARTIFICIAL_ANALYSIS.interface import get_rankings
            model_slugs = list(models.keys())
            aa_data = get_rankings(model_slugs)
            for our_slug, aa in aa_data.items():
                for mid in models:
                    if our_slug.lower() in mid.lower() or mid.lower() in our_slug.lower():
                        evals = aa.get("evaluations", {})
                        rankings = aa.get("rankings", {})
                        non_null_evals = {k: v for k, v in evals.items() if v is not None}
                        models[mid]["aa_benchmarks"] = non_null_evals
                        models[mid]["aa_benchmarks"]["_speed_tps"] = aa.get("speed")
                        models[mid]["aa_benchmarks"]["_ttft_s"] = aa.get("ttft")
                        models[mid]["aa_rankings"] = rankings
                        break
        except Exception:
            pass

        sorted_mids = sorted(models.keys(), key=len, reverse=True)
        for call in self._usage_calls:
            model_key = call.get("model", "")
            prov_key = call.get("provider", "")
            vendor = prov_key.split("-")[0] if prov_key else "unknown"
            inp = call.get("input_tokens", 0)
            outp = call.get("output_tokens", 0)

            for mid in sorted_mids:
                mdata = models[mid]
                provs = mdata.get("providers", [])
                if (mid == model_key
                        or model_key in provs
                        or prov_key in provs
                        or any(pr.endswith('-' + mid) for pr in [model_key, prov_key] if pr)):
                    mdata["total_calls"] += 1
                    mdata["input_tokens"] += inp
                    mdata["output_tokens"] += outp
                    break

            if vendor in providers:
                providers[vendor]["total_calls"] += 1
                providers[vendor]["input_tokens"] += inp
                providers[vendor]["output_tokens"] += outp

        from interface.utils import get_precision, get_symbol
        rate_info = {}
        for code in rates:
            rate_info[code] = {"rate": rates[code], "precision": get_precision(code), "symbol": get_symbol(code)}
        return {"models": models, "providers": providers, "calls": self._usage_calls[-100:], "rates": rate_info}

    def _page_handler(self, path: str) -> Optional[str]:
        """Handle /session/<sid>/<type>/<round_id>/... page routes."""
        qs = ""
        if "?" in path:
            path, qs = path.split("?", 1)
        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[0] != "session":
            return _not_found_page("Invalid path")
        sid = parts[1]
        data_type = parts[2]
        try:
            round_num = int(parts[3])
        except (ValueError, IndexError):
            return _not_found_page("Invalid round number")

        if data_type in ("input", "output", "context"):
            content = self._round_store.get_token_data(sid, round_num, data_type)
            token_count = 0
            cost = 0.0
            for param in qs.split("&"):
                if param.startswith("tokens="):
                    try: token_count = int(param.split("=")[1])
                    except ValueError: pass
                elif param.startswith("cost="):
                    try: cost = float(param.split("=")[1])
                    except ValueError: pass
            return render_token_page(sid, round_num, data_type, content,
                                     token_count=token_count, cost=cost)
        elif data_type == "read":
            rel_path = "/".join(parts[4:-1]) if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
            op_id = 0
            if len(parts) > 5:
                try:
                    op_id = int(parts[-1])
                except ValueError:
                    rel_path = "/".join(parts[4:])
            op = self._round_store.get_file_op(sid, round_num, "read", rel_path, op_id)
            if not op:
                return _not_found_page(f"No read data for {rel_path} in round {round_num}")
            return render_read_page(sid, round_num, op)
        elif data_type == "edit":
            rel_path = "/".join(parts[4:-1]) if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
            op_id = 0
            if len(parts) > 5:
                try:
                    op_id = int(parts[-1])
                except ValueError:
                    rel_path = "/".join(parts[4:])
            op = self._round_store.get_file_op(sid, round_num, "edit", rel_path, op_id)
            if not op:
                return _not_found_page(f"No edit data for {rel_path} in round {round_num}")
            return render_edit_page(sid, round_num, op)
        else:
            return _not_found_page(f"Unknown data type: {data_type}")

    _PID_FILE = os.path.join(os.path.dirname(__file__), ".server.pid")

    @classmethod
    def _kill_stale_server(cls):
        """Kill any previously running server in this scope (PID file guard)."""
        pid_path = cls._PID_FILE
        if not os.path.exists(pid_path):
            return
        try:
            with open(pid_path) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            import signal
            os.kill(old_pid, signal.SIGTERM)
            import time
            time.sleep(1)
            try:
                os.kill(old_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except (ProcessLookupError, ValueError, PermissionError):
            pass
        try:
            os.remove(pid_path)
        except OSError:
            pass

    @classmethod
    def _write_pid(cls):
        with open(cls._PID_FILE, "w") as f:
            f.write(str(os.getpid()))

    def start(self, open_browser: bool = True):
        """Start the live agent server (kills any stale server first)."""
        self._kill_stale_server()
        self._write_pid()
        import atexit
        atexit.register(lambda: os.path.exists(self._PID_FILE) and os.remove(self._PID_FILE))

        from interface.gui import LocalHTMLServer

        html_path = str(_root / "logic" / "assistant" / "gui" / "live.html")

        self._server = LocalHTMLServer(
            html_path=html_path,
            port=self.port,
            title="LLM Agent Live",
            api_handler=self._api_handler,
            page_handler=self._page_handler,
            enable_sse=True,
        )

        self._mgr.on_event(self._on_mgr_event)

        existing = self._mgr.list_sessions()
        if existing:
            self._default_session_id = existing[0]["id"]
        else:
            sid = self._mgr.new_session(title="New Task")
            self._default_session_id = sid

        self._server.start()
        self.port = self._server.port

        if open_browser:
            self._server.open_browser()

        return self._server

    def stop(self):
        if self._server:
            self._server.stop()

    @property
    def url(self) -> str:
        return self._server.url if self._server else ""

    @property
    def default_session_id(self) -> Optional[str]:
        return self._default_session_id


def start_server(
    provider_name: str = "zhipu-glm-4.7-flash",
    system_prompt: str = "",
    enable_tools: bool = True,
    port: int = 0,
    open_browser: bool = True,
    lang: str = "en",
    default_codebase: str = None,
    brain=None,
    scope_name: str = "TOOL",
) -> AgentServer:
    """Convenience function to start the live agent server.

    Returns the AgentServer instance (server is already running).
    """
    agent = AgentServer(
        provider_name=provider_name,
        system_prompt=system_prompt,
        enable_tools=enable_tools,
        port=port,
        lang=lang,
        default_codebase=default_codebase,
        brain=brain,
        scope_name=scope_name,
    )
    agent.start(open_browser=open_browser)
    return agent
