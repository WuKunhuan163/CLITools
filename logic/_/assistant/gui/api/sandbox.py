"""Sandbox policy and permission endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class SandboxMixin:
    """Sandbox policy and permission endpoints."""

    def _api_sandbox_state(self) -> dict:
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        return {"ok": True, **sb.get_state()}

    def _api_sandbox_set_system_policy(self, body: dict) -> dict:
        policy = body.get("policy", "")
        from logic._.assistant.sandbox import get_sandbox, SYSTEM_POLICIES
        if policy not in SYSTEM_POLICIES:
            return {"ok": False, "error": f"Invalid policy. Use: {SYSTEM_POLICIES}"}
        sb = get_sandbox()
        sb.system_policy = policy
        self._push_sse({"type": "sandbox_policy_changed", "policy": policy})
        return {"ok": True, "policy": policy}

    def _api_sandbox_set_command(self, body: dict) -> dict:
        cmd = body.get("command", "").strip()
        policy = body.get("policy", "").strip()
        from logic._.assistant.sandbox import get_sandbox, COMMAND_POLICIES
        if not cmd:
            return {"ok": False, "error": "Command is required"}
        if policy not in COMMAND_POLICIES:
            return {"ok": False, "error": f"Invalid policy. Use: {COMMAND_POLICIES}"}
        sb = get_sandbox()
        sb.set_command_permission(cmd, policy)
        return {"ok": True, "command": cmd, "policy": policy}

    def _api_sandbox_remove_command(self, body: dict) -> dict:
        cmd = body.get("command", "").strip()
        if not cmd:
            return {"ok": False, "error": "Command is required"}
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        sb.remove_command_permission(cmd)
        return {"ok": True, "removed": cmd}

    def _api_sandbox_check(self, body: dict) -> dict:
        """Check permission for a command. Returns decision + creates pending if needed."""
        cmd = body.get("command", "").strip()
        request_id = body.get("request_id", "")
        session_id = body.get("session_id", "")
        if not cmd:
            return {"ok": False, "error": "Command is required"}
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())[:8]
        result = sb.create_pending(request_id, cmd, session_id)
        if result["decision"] == "ask":
            self._push_sse({
                "type": "sandbox_prompt",
                "request_id": request_id,
                "cmd": cmd,
                "normalized": result.get("normalized", ""),
                "created_at": time.time(),
            })
        return {"ok": True, **result}

    def _api_sandbox_resolve(self, body: dict) -> dict:
        """Resolve a pending sandbox permission request."""
        request_id = body.get("request_id", "")
        decision = body.get("decision", "")
        persist = body.get("persist", False)
        if not request_id or not decision:
            return {"ok": False, "error": "request_id and decision required"}
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        result = sb.resolve_pending(request_id, decision, persist)
        if result.get("ok"):
            resolved_evt = {
                "type": "sandbox_resolved",
                "request_id": request_id,
                "decision": decision,
            }
            session_id = body.get("session_id", "")
            if not session_id:
                for sid, events in self._event_history.items():
                    for e in reversed(events):
                        if e.get("type") == "sandbox_prompt" and e.get("request_id") == request_id:
                            session_id = sid
                            break
                    if session_id:
                        break
            if session_id:
                resolved_evt["session_id"] = session_id
                if session_id not in self._event_history:
                    self._event_history[session_id] = []
                self._event_history[session_id].append(resolved_evt)
            self._push_sse(resolved_evt)
        return result

    def _api_sandbox_pending(self) -> dict:
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        return {"ok": True, "pending": sb.get_all_pending()}

    def _api_sandbox_set_timeout(self, body: dict) -> dict:
        timeout = body.get("timeout", 20)
        from logic._.assistant.sandbox import get_sandbox
        sb = get_sandbox()
        if timeout not in (5, 10, 20, 60, 180):
            return {"ok": False, "error": "Invalid timeout. Use: 5, 10, 20, 60, 180"}
        sb.popup_timeout = timeout
        return {"ok": True, "timeout": timeout}

    def _api_sandbox_set_boundary_policy(self, body: dict) -> dict:
        policy = body.get("policy", "")
        from logic._.assistant.sandbox import get_sandbox, BOUNDARY_POLICIES
        if policy not in BOUNDARY_POLICIES:
            return {"ok": False, "error": f"Invalid policy. Use: {BOUNDARY_POLICIES}"}
        sb = get_sandbox()
        sb.boundary_policy = policy
        return {"ok": True, "policy": policy}

    def _api_sandbox_set_mode_switch_policy(self, body: dict) -> dict:
        policy = body.get("policy", "")
        from logic._.assistant.sandbox import get_sandbox, MODE_SWITCH_POLICIES
        if policy not in MODE_SWITCH_POLICIES:
            return {"ok": False, "error": f"Invalid policy. Use: {MODE_SWITCH_POLICIES}"}
        sb = get_sandbox()
        sb.mode_switch_policy = policy
        self._push_sse({"type": "settings_changed"})
        return {"ok": True, "policy": policy}

    def _api_sandbox_set_mode_switch_timeout(self, body: dict) -> dict:
        timeout = body.get("timeout", 20)
        from logic._.assistant.sandbox import get_sandbox, MODE_SWITCH_TIMEOUT_STEPS
        if timeout not in MODE_SWITCH_TIMEOUT_STEPS:
            return {"ok": False, "error": f"Invalid timeout. Use: {MODE_SWITCH_TIMEOUT_STEPS}"}
        sb = get_sandbox()
        sb.mode_switch_timeout = timeout
        return {"ok": True, "timeout": timeout}

    # ── Workspace endpoints ──

