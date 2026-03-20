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
    POST /api/session/<sid>/scroll-to             Scroll frontend to block by event_idx

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
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

_log = logging.getLogger(__name__)

_dir = Path(__file__).resolve().parent
_root = _dir.parent.parent.parent
sys.path.insert(0, str(_root))

from logic.assistant.gui.backend.store import (
    RoundStore, render_token_page, render_read_page,
    render_edit_page, _not_found_page
)

from tool.LLM.logic.task.agent.conversation import ConversationManager

from logic.assistant.gui.api.keys import KeysMixin
from logic.assistant.gui.api.models import ModelsMixin
from logic.assistant.gui.api.sandbox import SandboxMixin
from logic.assistant.gui.api.sessions import SessionsMixin
from logic.assistant.gui.api.workspace import WorkspaceMixin
from logic.assistant.gui.api.brain import BrainMixin
from logic.assistant.gui.api.edits import EditsMixin
from logic.assistant.gui.api.usage import UsageMixin
from logic.assistant.gui.backend.config import ConfigMixin


def _load_system_prompt() -> str:
    """Load the agent system prompt from logic/assistant/prompt/system/prompt.json."""
    prompt_file = _root / "logic" / "assistant" / "prompt" / "system" / "prompt.json"
    try:
        import json as _json
        data = _json.loads(prompt_file.read_text())
        return data.get("prompt", "")
    except Exception:
        return "You are an autonomous AI Agent."

_SYSTEM_PROMPT = _load_system_prompt()


def get_system_prompt(lang: str = "en") -> str:
    """Return the agent system prompt."""
    return _SYSTEM_PROMPT


AGENT_SYSTEM_PROMPT = _SYSTEM_PROMPT


class AgentServer(
    KeysMixin, ModelsMixin, SandboxMixin, SessionsMixin,
    WorkspaceMixin, BrainMixin, EditsMixin, UsageMixin, ConfigMixin,
):
    """Manages the live agent server lifecycle."""

    def __init__(
        self,
        selected_model: str = "auto",
        system_prompt: str = "",
        enable_tools: bool = True,
        port: int = 0,
        lang: str = "en",
        default_codebase: str = None,
        brain=None,
        scope_name: str = "TOOL",
    ):
        self.selected_model = selected_model
        self.system_prompt = system_prompt or get_system_prompt(lang)
        self.enable_tools = enable_tools
        self.port = port
        self.lang = lang
        self.default_codebase = default_codebase
        self.scope_name = scope_name

        from logic.assistant.sandbox import set_tool_sandbox_dir
        set_tool_sandbox_dir(default_codebase)

        self._mgr = ConversationManager(
            selected_model=selected_model,
            system_prompt=self.system_prompt,
            enable_tools=enable_tools,
            default_codebase=default_codebase,
            brain=brain,
        )
        self._server = None
        self._default_session_id = None
        self._usage_calls = []
        self._event_history: Dict[str, list] = {}  # session_id -> [events]
        self._MAX_EVENTS_PER_SESSION = 5000
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
                usage = evt.get("usage", {})
                if usage.get("prompt_tokens") or usage.get("completion_tokens"):
                    self._usage_calls.append({
                        "timestamp": evt.get("timestamp", 0),
                        "model": evt.get("model", ""),
                        "provider": evt.get("provider", ""),
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                        "latency_s": evt.get("latency_s", 0),
                        "ok": not evt.get("error"),
                        "exchange_rate_cny": 7.25,
                    })
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

        # ── /api/i18n + /api/palette ──────────────────────────────
        if path == "/api/i18n":
            return self._api_i18n(body)
        if path == "/api/palette":
            return self._api_palette()

        # ── /api/model/... ─────────────────────────────────────
        if path == "/api/model/list" or path == "/api/configured_models":
            return self._get_configured_models()
        if path == "/api/models/metadata":
            return self._api_models_metadata()
        if path in ("/api/model/switch", "/api/model"):
            return self._api_switch_model(body)
        if path == "/api/model/state":
            return self._api_model_state()

        # ── /api/key/... ───────────────────────────────────────
        if path == "/api/provider/guide":
            return self._api_provider_guide(body)

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
        if path == "/api/model/resolve":
            return self._api_model_resolve(body)

        # ── Health check ──────────────────────────────────────
        if path == "/api/health":
            import time as _t
            return {"ok": True, "ts": _t.time()}

        # ── System ─────────────────────────────────────────────
        if path == "/api/state":
            state = self._mgr.get_state()
            state["scope_name"] = self.scope_name
            return {"ok": True, "state": state}
        if path == "/api/scope":
            if method == "POST" and body:
                new_scope = body.get("scope_name", "")
                new_codebase = body.get("default_codebase", "")
                if new_scope:
                    self.scope_name = new_scope
                if new_codebase:
                    self.default_codebase = new_codebase
                    self._mgr._default_codebase = new_codebase
                    from logic.assistant.sandbox import set_tool_sandbox_dir
                    set_tool_sandbox_dir(new_codebase)
                self._push_sse({"type": "settings_changed"})
                resp = {"ok": True, "scope_name": self.scope_name}
                if new_codebase:
                    resp["workspace_path"] = new_codebase
                return resp
            result = {"ok": True, "scope_name": self.scope_name}
            try:
                wm = self._get_wm()
                ws_info = wm.active_workspace_info()
                if ws_info:
                    result["workspace_path"] = ws_info.get("path", "")
                    result["workspace_name"] = ws_info.get("name", "")
                elif self.default_codebase:
                    result["workspace_path"] = self.default_codebase
            except Exception:
                if self.default_codebase:
                    result["workspace_path"] = self.default_codebase
            return result
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
        if path == "/api/debug-mode" and method == "POST":
            enabled = bool(body.get("enabled", False))
            self._push_sse({"type": "debug_mode", "enabled": enabled})
            return {"ok": True, "enabled": enabled}

        # ── Brain endpoints ──
        if path == "/api/brain/blueprints" and method == "GET":
            return self._api_brain_blueprints()
        if path == "/api/brain/instances" and method == "GET":
            return self._api_brain_instances()
        if path == "/api/brain/active" and method == "GET":
            return self._api_brain_active()
        if path == "/api/brain/instance" and method == "POST":
            return self._api_brain_create_instance(body)
        if path == "/api/brain/switch" and method == "POST":
            return self._api_brain_switch(body)
        if path == "/api/brain/audit" and method == "POST":
            return self._api_brain_audit(body)

        # ── Sandbox endpoints ──
        if path == "/api/sandbox/state" and method == "GET":
            return self._api_sandbox_state()
        if path == "/api/sandbox/system-policy" and method == "POST":
            return self._api_sandbox_set_system_policy(body)
        if path == "/api/sandbox/command" and method == "POST":
            return self._api_sandbox_set_command(body)
        if path == "/api/sandbox/command" and method == "DELETE":
            return self._api_sandbox_remove_command(body)
        if path == "/api/sandbox/check" and method == "POST":
            return self._api_sandbox_check(body)
        if path == "/api/sandbox/resolve" and method == "POST":
            return self._api_sandbox_resolve(body)
        if path == "/api/sandbox/pending" and method == "GET":
            return self._api_sandbox_pending()
        if path == "/api/sandbox/timeout" and method == "POST":
            return self._api_sandbox_set_timeout(body)
        if path == "/api/sandbox/boundary-policy" and method == "POST":
            return self._api_sandbox_set_boundary_policy(body)
        if path == "/api/sandbox/mode-switch-policy" and method == "POST":
            return self._api_sandbox_set_mode_switch_policy(body)
        if path == "/api/sandbox/mode-switch-timeout" and method == "POST":
            return self._api_sandbox_set_mode_switch_timeout(body)

        # ── Workspace endpoints ──
        if path == "/api/workspace/list" and method == "GET":
            return self._api_workspace_list()
        if path == "/api/workspace/active" and method == "GET":
            return self._api_workspace_active()
        if path == "/api/workspace/create" and method == "POST":
            return self._api_workspace_create(body)
        if path == "/api/workspace/open" and method == "POST":
            return self._api_workspace_open(body)
        if path == "/api/workspace/close" and method == "POST":
            return self._api_workspace_close()
        if path == "/api/workspace/delete" and method == "POST":
            return self._api_workspace_delete(body)
        if path == "/api/workspace/state" and method == "GET":
            return self._api_workspace_state()
        if path == "/api/workspace/browse" and method == "POST":
            return self._api_workspace_browse(body)

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
        if sub == "turn-limit" and method == "POST":
            tl = int(body.get("turn_limit", 0))
            self._mgr._selected_turn_limit = tl if tl > 0 else 20
            self._push_sse({"type": "turn_limit_set", "session_id": sid,
                            "turn_limit": tl})
            return {"ok": True, "turn_limit": tl}
        if sub == "data":
            return self._api_session_data(sid)
        if sub == "purge" and method == "POST":
            return self._api_purge_data(sid, body)

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

        if sub == "scroll-to" and method == "POST":
            return self._api_scroll_to(sid, body)

        return {"ok": False, "error": f"Unknown session endpoint: {sub}"}

    def _push_sse(self, evt: dict):
        if self._server:
            self._server.push_event(evt)

    def _drain_injected_queue(self, sid: str):
        """After an injected complete event, start the next queued task.

        If the session was in self-operate mode (events were injected, not
        provider-driven), the next task also stays in self-operate mode.
        """
        queue = self._mgr._task_queues.get(sid, [])
        if not queue:
            return
        task = queue.pop(0)
        text = task.get("text", "")
        turn_limit = task.get("turn_limit", 0)
        mode = task.get("mode", "")
        session = self._mgr.get_session(sid)
        if mode and session:
            session.mode = mode

        self._push_sse({"type": "queue_task_started",
                        "task_id": task.get("id", ""),
                        "text": text[:80],
                        "mode": mode,
                        "remaining": len(queue)})
        self._push_sse({"type": "queue_updated",
                        "queue": self._mgr._serialize_queue(sid)})

        is_self_operate = bool(
            self._event_history.get(sid)
            and any(e.get("type") == "llm_request" and e.get("self_operate")
                    for e in reversed(self._event_history[sid][-20:]))
        )

        if is_self_operate:
            if session:
                session.status = "running"
                session.done_reason = None
            events = [
                {"type": "user", "prompt": text, "session_id": sid},
                {"type": "session_status", "id": sid, "status": "running"},
                {"type": "llm_request", "provider": "Self", "round": 1,
                 "model": "self", "self_operate": True, "session_id": sid},
            ]
            if sid not in self._event_history:
                self._event_history[sid] = []
            for evt in events:
                self._event_history[sid].append(evt)
                self._push_sse(evt)
        else:
            context_feed = task.get("context_feed")
            import threading
            def _start():
                try:
                    self._mgr._start_turn(sid, text, False, context_feed,
                                          turn_limit)
                except Exception:
                    import traceback, sys as _sys
                    traceback.print_exc(file=_sys.stderr)
            threading.Thread(target=_start, daemon=True).start()

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

    def _lookup_session_title(self, sid: str) -> str:
        if sid and hasattr(self, '_mgr') and self._mgr:
            try:
                s = self._mgr.get_session(sid)
                if s:
                    return s.get("title", "")
            except Exception:
                pass
        return ""

    def _on_mgr_event(self, evt: dict):
        """Forward ConversationManager events to SSE, track usage, and store history."""
        import time as _t
        if "ts" not in evt:
            evt["ts"] = _t.time()
        sid = evt.get("session_id") or self._mgr._current_turn_session_id or self._default_session_id
        if sid:
            evt["session_id"] = sid
            if evt.get("type") == "tool_stream_delta":
                idx = evt.get("index", 0)
                key = f"_stream_chars_{idx}"
                prev = getattr(self, key, 0)
                cur = prev + len(evt.get("content", ""))
                setattr(self, key, cur)
                if prev == 0 or cur - prev >= 200 or cur < prev:
                    if sid not in self._event_history:
                        self._event_history[sid] = []
                    self._event_history[sid].append({
                        "type": "tool_stream_progress", "ts": evt["ts"],
                        "session_id": sid, "index": idx,
                        "chars": cur,
                    })
            else:
                if evt.get("type") == "tool_stream_start":
                    idx = evt.get("index", 0)
                    setattr(self, f"_stream_chars_{idx}", 0)
                if sid not in self._event_history:
                    self._event_history[sid] = []
                self._event_history[sid].append(evt)
                if len(self._event_history[sid]) > self._MAX_EVENTS_PER_SESSION:
                    trim = len(self._event_history[sid]) - self._MAX_EVENTS_PER_SESSION
                    self._event_history[sid] = self._event_history[sid][trim:]

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
                "model": evt.get("model", self.selected_model),
                "provider": evt.get("provider", self.selected_model),
                "input_tokens": evt.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": evt.get("usage", {}).get("completion_tokens", 0),
                "latency_s": evt.get("latency_s", 0),
                "ok": not evt.get("error"),
                "exchange_rate_cny": usd_rate,
            })
        try:
            if evt.get("type") == "sandbox_prompt":
                req_id = evt.get("request_id", "?")
                cmd = evt.get("cmd", "")
                sid = evt.get("session_id", "")
                mandatory = evt.get("mandatory", False)
                m_tag = " \033[1;31m[mandatory]\033[0m" if mandatory else ""
                session_title = self._lookup_session_title(sid)
                label = f" {session_title}" if session_title else ""
                print(f"\n \033[1;33m>\033[0m \033[1mSandbox\033[0m Waiting for approval{m_tag}", flush=True)
                print(f"   \033[2m{sid[:8] if sid else ''}·{label}\033[0m", flush=True)
                print(f"   Command: {cmd}  [{req_id}]", flush=True)
            if evt.get("type") == "task_exit":
                sid = evt.get("session_id", "")
                reason = evt.get("reason", "completed")
                session_title = self._lookup_session_title(sid)
                color = "\033[32m" if reason == "completed" else "\033[31m"
                print(f"\n {color}>\033[0m \033[1mTask {reason}\033[0m", flush=True)
                print(f"   \033[2m{sid[:8] if sid else ''}· {session_title}\033[0m", flush=True)
        except (BrokenPipeError, OSError):
            pass

        self._push_sse(evt)

    def _page_handler(self, path: str):
        """Serve /session/<sid>/<type>/<round> detail pages."""
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

        asset_image_dir = str(_root / "logic" / "asset" / "image")
        llm_logic_dir = str(_root / "tool" / "LLM" / "logic")
        self._server = LocalHTMLServer(
            html_path=html_path,
            port=self.port,
            title="LLM Agent Live",
            api_handler=self._api_handler,
            page_handler=self._page_handler,
            enable_sse=True,
            asset_dirs={
                "/asset/icon/": asset_image_dir + "/",
                "/llm/models/": llm_logic_dir + "/models/",
                "/llm/providers/": llm_logic_dir + "/providers/",
            },
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

        base = f"http://localhost:{self.port}"
        print(f"\n\033[1mAssistant Server\033[0m  {base}")
        print(f"  \033[2mQuick reference:\033[0m")
        print(f"  New session:   curl -X POST {base}/api/sessions -H 'Content-Type: application/json' -d '{{\"title\":\"My Task\"}}'")
        print(f"  Send task:     curl -X POST {base}/api/session/<sid>/send -H 'Content-Type: application/json' -d '{{\"text\":\"hello\"}}'")
        print(f"  List sessions: curl {base}/api/sessions")
        print(f"  Clear all:     curl -X DELETE {base}/api/sessions")
        print(f"  Sandbox:       curl -X POST {base}/api/sandbox/resolve -H ... '{{\"request_id\":\"<id>\",\"decision\":\"allow\"}}'")
        print(f"  Sandbox state: curl {base}/api/sandbox/state")
        print()

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
    selected_model: str = "auto",
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
        selected_model=selected_model,
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
