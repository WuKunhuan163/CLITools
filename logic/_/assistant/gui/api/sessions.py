"""Session lifecycle, data, communication, queue, and injection endpoints."""
from __future__ import annotations

import json
import sys
from typing import Optional


class SessionsMixin:
    """Session management API methods extracted from AgentServer."""

    def _api_session_state(self, sid: str) -> dict:
        session = self._mgr.get_session(sid)
        if not session:
            return {"ok": False, "error": f"Session {sid} not found"}
        mc = getattr(session, "message_count", 0)
        if not mc:
            mc = len(getattr(session, "messages", []))
        return {"ok": True, "id": sid, "title": session.title,
                "status": session.status,
                "message_count": mc}

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
        mode = body.get("mode", "")
        model = body.get("model", "")
        if mode:
            self._mgr._selected_mode = mode
        if model and model != self._mgr._selected_model:
            self._mgr._selected_model = model
            self.selected_model = model
        self._mgr.send_message(sid, text, blocking=False,
                               context_feed=context_feed,
                               turn_limit=turn_limit,
                               mode=mode, model=model)
        return {"ok": True, "session_id": sid}

    def _api_input(self, sid: str, body: dict) -> dict:
        text = body.get("text", "").strip()
        if not sid or not text:
            return {"ok": False, "error": "Missing session_id or text"}
        self._push_sse({"type": "inject_input", "session_id": sid, "text": text})
        return {"ok": True, "session_id": sid}

    def _api_session_data(self, sid: str) -> dict:
        """Return per-type record counts and memory usage for a session's round store data."""
        rounds = self._round_store._data.get(sid, {})
        events = self._event_history.get(sid, [])

        types_info = {}
        for dtype in ("input", "output", "context"):
            count = 0
            mem = 0
            for rnum, entry in rounds.items():
                val = entry.get(dtype)
                if val:
                    count += 1
                    mem += sys.getsizeof(val)
            types_info[dtype] = {"count": count, "memory_bytes": mem}

        read_count = 0
        read_mem = 0
        edit_count = 0
        edit_mem = 0
        for rnum, entry in rounds.items():
            for op in entry.get("file_ops", []):
                size = sys.getsizeof(op.get("content", ""))
                if op["type"] == "read":
                    read_count += 1
                    read_mem += size
                elif op["type"] == "edit":
                    edit_count += 1
                    edit_mem += size + sys.getsizeof(op.get("old_content", "")) + sys.getsizeof(op.get("new_content", ""))
        types_info["read"] = {"count": read_count, "memory_bytes": read_mem}
        types_info["edit"] = {"count": edit_count, "memory_bytes": edit_mem}

        exec_count = sum(1 for e in events if e.get("type") == "tool_result" and e.get("name") == "exec")
        exec_mem = sum(sys.getsizeof(e.get("output", "")) for e in events
                       if e.get("type") == "tool_result" and e.get("name") == "exec")
        types_info["exec"] = {"count": exec_count, "memory_bytes": exec_mem}

        total_rounds = len(rounds)
        total_events = len(events)
        events_mem = sum(sys.getsizeof(json.dumps(e, ensure_ascii=False)) for e in events[:100])
        if total_events > 100:
            events_mem = int(events_mem * total_events / 100)

        protected_rounds = 8
        try:
            from tool.LLM.logic.config import get_config_value
            protected_rounds = int(get_config_value("history_context_rounds", 8))
        except Exception:
            pass

        return {
            "ok": True,
            "session_id": sid,
            "types": types_info,
            "total_rounds": total_rounds,
            "total_events": total_events,
            "events_memory_bytes": events_mem,
            "protected_rounds": protected_rounds,
        }

    def _api_purge_data(self, sid: str, body: dict) -> dict:
        """Purge data from a session by type and count/memory threshold."""
        _VALID_PURGE_TYPES = {"input", "output", "context", "read", "edit", "exec", "rounds"}
        dtype = body.get("type", "")
        count = int(body.get("count", 0))
        if dtype not in _VALID_PURGE_TYPES:
            return {"ok": False, "error": f"Invalid type '{dtype}'. Must be one of: {', '.join(sorted(_VALID_PURGE_TYPES))}"}
        if count <= 0:
            return {"ok": False, "error": "Count must be positive"}

        protected = 8
        try:
            from tool.LLM.logic.config import get_config_value
            protected = int(get_config_value("history_context_rounds", 8))
        except Exception:
            pass

        rounds = self._round_store._data.get(sid, {})
        if not rounds:
            return {"ok": True, "purged": 0}

        if dtype == "rounds":
            sorted_rounds = sorted(rounds.keys())
            max_purgeable = len(sorted_rounds) - protected
            if max_purgeable <= 0:
                return {"ok": False, "error": "All rounds are protected by history_context_rounds setting"}
            actual_count = min(count, max_purgeable)
            purged = 0
            for rnum in sorted_rounds[:actual_count]:
                del rounds[rnum]
                purged += 1
            events = self._event_history.get(sid, [])
            purged_rnums = set(sorted_rounds[:actual_count])
            self._event_history[sid] = [
                e for e in events
                if e.get("round", 0) not in purged_rnums or e.get("round", 0) == 0
            ]
            return {"ok": True, "purged": purged, "remaining": len(rounds)}

        if dtype in ("input", "output", "context"):
            sorted_rounds = sorted(rounds.keys())
            purged = 0
            for rnum in sorted_rounds:
                if purged >= count:
                    break
                if rnum in sorted_rounds[-protected:]:
                    continue
                entry = rounds.get(rnum, {})
                if dtype in entry:
                    del entry[dtype]
                    purged += 1
            return {"ok": True, "purged": purged}

        if dtype in ("read", "edit"):
            sorted_rounds = sorted(rounds.keys())
            purged = 0
            for rnum in sorted_rounds:
                if purged >= count:
                    break
                entry = rounds.get(rnum, {})
                ops = entry.get("file_ops", [])
                new_ops = []
                for op in ops:
                    if purged < count and op["type"] == dtype and rnum not in sorted_rounds[-protected:]:
                        purged += 1
                    else:
                        new_ops.append(op)
                entry["file_ops"] = new_ops
            return {"ok": True, "purged": purged}

        return {"ok": False, "error": f"Unknown type: {dtype}"}

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
        session = self._mgr.get_session(sid)
        if session and session.status == "running":
            session.status = "done"
            session.done_reason = "cancelled"
            self._push_sse({"type": "complete", "reason": "cancelled",
                            "session_id": sid})
            self._push_sse({"type": "session_status", "id": sid,
                            "status": "done", "reason": "cancelled"})
            self._mgr._persist_session(sid)
        self._push_sse({"type": "cancel_requested", "session_id": sid})
        return {"ok": True}

    def _api_queue(self, sid: str, body: dict) -> dict:
        action = body.get("action", "list")
        if not sid:
            return {"ok": False, "error": "No active session"}
        if action == "list":
            return {"ok": True, "queue": self._mgr.get_task_queue(sid)}
        elif action == "clear":
            count = self._mgr.clear_task_queue(sid)
            return {"ok": True, "cleared": count}
        elif action == "update":
            task_id = body.get("task_id", "")
            updates = {}
            for k in ("text", "mode", "model", "turn_limit"):
                if k in body:
                    updates[k] = body[k]
            if self._mgr.update_queued_task(sid, task_id, updates):
                return {"ok": True}
            return {"ok": False, "error": "Task not found"}
        elif action == "remove":
            task_id = body.get("task_id", "")
            if self._mgr.remove_queued_task(sid, task_id):
                return {"ok": True}
            return {"ok": False, "error": "Task not found"}
        elif action == "reorder":
            task_id = body.get("task_id", "")
            new_index = int(body.get("index", 0))
            if self._mgr.reorder_queued_task(sid, task_id, new_index):
                return {"ok": True}
            return {"ok": False, "error": "Task not found"}
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
        s = self._mgr.get_session(sid)
        if s:
            etype = event.get("type", "")
            if etype == "session_status":
                s.status = event.get("status", s.status)
            elif etype == "user":
                s.message_count = getattr(s, "message_count", 0) + 1
            elif etype == "complete":
                s.status = "done"
                s.done_reason = event.get("reason", "done")
                self._mgr._persist_session(sid)
        self._push_sse(event)
        self._maybe_record_injected_round(sid, event)
        if s and event.get("type") == "complete":
            self._drain_injected_queue(sid)
        return {"ok": True}

    def _api_inject_events(self, sid: str, body: dict) -> dict:
        events = body.get("events", [])
        if not sid:
            return {"ok": False, "error": "No active session"}
        if not isinstance(events, list):
            return {"ok": False, "error": "events must be a list"}
        if sid not in self._event_history:
            self._event_history[sid] = []
        s = self._mgr.get_session(sid)
        for evt in events:
            if isinstance(evt, dict):
                evt["session_id"] = sid
                self._event_history[sid].append(evt)
                if s:
                    etype = evt.get("type", "")
                    if etype == "session_status":
                        s.status = evt.get("status", s.status)
                    elif etype == "user":
                        s.message_count = getattr(s, "message_count", 0) + 1
                    elif etype == "complete":
                        s.status = "done"
                        s.done_reason = evt.get("reason", "done")
                self._push_sse(evt)
                self._maybe_record_injected_round(sid, evt)
        if s and s.status == "done":
            self._mgr._persist_session(sid)
            self._drain_injected_queue(sid)
        return {"ok": True, "count": len(events)}

    def _api_scroll_to(self, sid: str, body: dict) -> dict:
        """Emit a scroll_to_block SSE event to scroll the frontend to a specific block."""
        event_idx = body.get("event_idx")
        if event_idx is None:
            return {"ok": False, "error": "Missing event_idx"}
        self._push_sse({
            "type": "scroll_to_block",
            "event_idx": int(event_idx),
            "session_id": sid,
        })
        return {"ok": True, "event_idx": int(event_idx)}
