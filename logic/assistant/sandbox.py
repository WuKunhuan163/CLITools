"""Sandbox permission system for EXEC tool calls.

Three layers:
1. System Sandbox — global execution policy
   - "run_all": run everything without asking
   - "ask_always": ask user for every command
   Default: "ask_always"

2. Command Sandbox — per-command permissions
   - "always": run this command without asking
   - "forbidden": never run this command
   - None (not set): follow system sandbox policy
   Stored in data/sandbox_permissions.json

3. Mode Sandbox — assistant mode restrictions
   - "agent": default sandbox (inherits system + command)
   - "ask"/"plan": block all write operations (filesystem, network)
"""
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_PERM_FILE = _DATA_DIR / "sandbox_permissions.json"
_lock = threading.Lock()

SYSTEM_POLICIES = ["run_all", "ask_always"]
COMMAND_POLICIES = ["always", "once", "forbidden"]

WRITE_COMMANDS = {
    "rm", "rmdir", "mv", "cp", "mkdir", "touch", "chmod", "chown",
    "ln", "dd", "mkfs", "mount", "umount",
    "apt", "apt-get", "brew", "pip", "npm", "yarn",
    "git push", "git commit", "git reset", "git checkout",
    "docker rm", "docker rmi", "docker stop",
    "kill", "killall", "pkill",
    "curl -X POST", "curl -X PUT", "curl -X DELETE", "curl -X PATCH",
    "wget",
}

SAFE_READ_PREFIXES = {
    "cat", "ls", "find", "grep", "rg", "head", "tail", "wc",
    "echo", "pwd", "whoami", "uname", "date", "env", "printenv",
    "which", "type", "file", "stat", "du", "df",
    "python3 -c", "python -c", "node -e",
    "git status", "git log", "git diff", "git branch", "git show",
}


class SandboxManager:
    """Manages sandbox state across all three layers."""

    def __init__(self):
        self._system_policy = "ask_always"
        self._command_perms: Dict[str, str] = {}
        self._mode = "agent"
        self._pending: Dict[str, dict] = {}
        self._resolved: Dict[str, str] = {}
        self._pending_lock = threading.Lock()
        self._load()

    def _load(self):
        if _PERM_FILE.exists():
            try:
                data = json.loads(_PERM_FILE.read_text())
                self._system_policy = data.get("system_policy", "ask_always")
                self._command_perms = data.get("command_permissions", {})
            except Exception:
                pass

    def _save(self):
        with _lock:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _PERM_FILE.write_text(json.dumps({
                "system_policy": self._system_policy,
                "command_permissions": self._command_perms,
            }, indent=2))

    @property
    def system_policy(self) -> str:
        return self._system_policy

    @system_policy.setter
    def system_policy(self, value: str):
        if value in SYSTEM_POLICIES:
            self._system_policy = value
            self._save()

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        self._mode = value

    def get_command_permission(self, cmd: str) -> Optional[str]:
        """Get stored permission for a command. None = not set."""
        normalized = self._normalize_cmd(cmd)
        return self._command_perms.get(normalized)

    def set_command_permission(self, cmd: str, policy: str):
        """Set per-command permission policy."""
        if policy not in COMMAND_POLICIES:
            return
        normalized = self._normalize_cmd(cmd)
        self._command_perms[normalized] = policy
        self._save()

    def remove_command_permission(self, cmd: str):
        normalized = self._normalize_cmd(cmd)
        self._command_perms.pop(normalized, None)
        self._save()

    def list_command_permissions(self) -> Dict[str, str]:
        return dict(self._command_perms)

    def check_permission(self, cmd: str) -> Tuple[str, Optional[str]]:
        """Check if a command is allowed.

        Returns (decision, reason):
        - ("allow", None) — execute immediately
        - ("ask", reason) — need user approval
        - ("deny", reason) — blocked
        """
        if self._mode in ("ask", "plan"):
            if self._is_write_command(cmd):
                return ("deny", f"Write operations blocked in {self._mode} mode")

        cmd_perm = self.get_command_permission(cmd)
        if cmd_perm == "always":
            return ("allow", None)
        if cmd_perm == "forbidden":
            return ("deny", f"Command '{self._normalize_cmd(cmd)}' is forbidden")

        if self._system_policy == "run_all":
            return ("allow", None)

        if self._is_safe_read(cmd):
            return ("allow", None)

        return ("ask", f"New command needs approval: {self._normalize_cmd(cmd)}")

    def create_pending(self, request_id: str, cmd: str, session_id: str = "") -> dict:
        """Create a pending permission request for the frontend."""
        decision, reason = self.check_permission(cmd)
        if decision != "ask":
            return {"decision": decision, "reason": reason, "request_id": request_id}

        pending = {
            "request_id": request_id,
            "cmd": cmd,
            "normalized": self._normalize_cmd(cmd),
            "session_id": session_id,
            "created_at": time.time(),
            "status": "pending",
            "decision": None,
            "persist": None,
        }
        with self._pending_lock:
            self._pending[request_id] = pending
        return {"decision": "ask", "reason": reason, "request_id": request_id,
                "cmd": cmd, "normalized": self._normalize_cmd(cmd)}

    def resolve_pending(self, request_id: str, decision: str, persist: bool = False) -> dict:
        """Resolve a pending permission request.

        decision: "allow" or "deny"
        persist: if True, save as "always"/"forbidden" for this command
        """
        with self._pending_lock:
            pending = self._pending.pop(request_id, None)
            self._resolved[request_id] = decision
        if not pending:
            return {"ok": False, "error": "Request not found or expired"}

        if persist and pending.get("normalized"):
            policy = "always" if decision == "allow" else "forbidden"
            self.set_command_permission(pending["normalized"], policy)

        return {"ok": True, "decision": decision, "request_id": request_id}

    def get_pending(self, request_id: str) -> Optional[dict]:
        with self._pending_lock:
            return self._pending.get(request_id)

    def get_resolved(self, request_id: str) -> Optional[str]:
        """Get and consume a resolved decision. Returns 'allow' or 'deny', or None."""
        with self._pending_lock:
            return self._resolved.pop(request_id, None)

    def get_all_pending(self) -> List[dict]:
        with self._pending_lock:
            return list(self._pending.values())

    def get_state(self) -> dict:
        return {
            "system_policy": self._system_policy,
            "mode": self._mode,
            "command_permissions": self._command_perms,
            "pending_count": len(self._pending),
        }

    @staticmethod
    def _normalize_cmd(cmd: str) -> str:
        """Normalize a command to its key form (first word or known compound)."""
        parts = cmd.strip().split()
        if not parts:
            return ""
        first = parts[0]
        if first in ("git", "docker", "kubectl", "npm", "pip", "python3", "curl") and len(parts) > 1:
            return f"{first} {parts[1]}"
        return first

    @staticmethod
    def _is_write_command(cmd: str) -> bool:
        """Check if a command modifies the filesystem or has side effects."""
        stripped = cmd.strip()
        for wc in WRITE_COMMANDS:
            if stripped.startswith(wc):
                return True
        if ">" in stripped or ">>" in stripped:
            return True
        if "| tee " in stripped:
            return True
        return False

    @staticmethod
    def _is_safe_read(cmd: str) -> bool:
        """Check if a command is a known safe read-only command."""
        stripped = cmd.strip()
        if ">" in stripped or ">>" in stripped or "| tee " in stripped:
            return False
        for prefix in SAFE_READ_PREFIXES:
            if stripped.startswith(prefix):
                if "&&" not in stripped and ";" not in stripped and "|" not in stripped:
                    return True
                parts = [p.strip() for p in stripped.replace("&&", ";").replace("|", ";").split(";")]
                return all(
                    any(p.startswith(pf) for pf in SAFE_READ_PREFIXES)
                    for p in parts if p
                )
        return False


_instance: Optional[SandboxManager] = None
_instance_lock = threading.Lock()


def get_sandbox() -> SandboxManager:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SandboxManager()
    return _instance
