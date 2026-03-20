"""Sandbox permission system for EXEC and edit_file tool calls.

Five layers (evaluated in order):
1. Base Sandbox — absolute protection against catastrophic commands
   - Always active, cannot be disabled
   - Blocks: rm -rf /, rm -rf ~, mkfs on system disks, etc.

2. Mode Sandbox — assistant mode restrictions
   - "agent": full sandbox (inherits system + command)
   - "ask"/"plan": block all write operations

3. Workspace-boundary Sandbox — out-of-workspace protection
   - exec: commands with paths outside workspace require one-time approval
   - edit_file: edits to files outside workspace require one-time approval
   - Single-use approval (never persisted), always mandatory

4. System Sandbox — global execution policy
   - "run_all": run everything without asking
   - "ask_always": ask user for every command
   Default: "ask_always"

5. Command Sandbox — per-command permissions
   - "always": run this command without asking
   - "forbidden": never run this command
   - None (not set): follow system sandbox policy
   Stored in data/sandbox_permissions.json
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
BOUNDARY_POLICIES = ["ask_always", "allow_all", "deny_all"]
MODE_SWITCH_POLICIES = ["ask_always", "allow", "deny"]
MODE_SWITCH_TIMEOUT_STEPS = [5, 10, 20, 60, 180]

CATASTROPHIC_PATTERNS = [
    "rm -rf /", "rm -rf /*", "rm -rf ~", "rm -rf ~/",
    "rm -rf $HOME", "rm -rf ${HOME}",
    "mkfs /dev/sd", "mkfs /dev/disk",
    "dd if=/dev/zero of=/dev/sd", "dd if=/dev/zero of=/dev/disk",
    ":(){:|:&};:", "chmod -R 777 /", "chown -R",
    "shutdown", "reboot", "halt", "init 0", "init 6",
    "fork bomb", "> /dev/sda",
]

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
    """Manages sandbox state across all five layers."""

    def __init__(self):
        self._system_policy = "ask_always"
        self._command_perms: Dict[str, str] = {}
        self._mode = "agent"
        self._workspace_root: Optional[str] = None
        self._popup_timeout = 20
        self._boundary_policy = "ask_always"
        self._mode_switch_policy = "deny"
        self._mode_switch_timeout = 20
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
                self._popup_timeout = data.get("popup_timeout", 20)
                self._boundary_policy = data.get("boundary_policy", "ask_always")
                self._mode_switch_policy = data.get("mode_switch_policy", "deny")
                self._mode_switch_timeout = data.get("mode_switch_timeout", 20)
            except Exception:
                pass

    def _save(self):
        with _lock:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            _PERM_FILE.write_text(json.dumps({
                "system_policy": self._system_policy,
                "command_permissions": self._command_perms,
                "popup_timeout": self._popup_timeout,
                "boundary_policy": self._boundary_policy,
                "mode_switch_policy": self._mode_switch_policy,
                "mode_switch_timeout": self._mode_switch_timeout,
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

    @property
    def workspace_root(self) -> Optional[str]:
        return self._workspace_root

    @workspace_root.setter
    def workspace_root(self, value: Optional[str]):
        self._workspace_root = value

    @property
    def popup_timeout(self) -> int:
        return self._popup_timeout

    @popup_timeout.setter
    def popup_timeout(self, value: int):
        if value in (5, 10, 20, 60, 180):
            self._popup_timeout = value
            self._save()

    @property
    def boundary_policy(self) -> str:
        return self._boundary_policy

    @boundary_policy.setter
    def boundary_policy(self, value: str):
        if value in BOUNDARY_POLICIES:
            self._boundary_policy = value
            self._save()

    @property
    def mode_switch_policy(self) -> str:
        return self._mode_switch_policy

    @mode_switch_policy.setter
    def mode_switch_policy(self, value: str):
        if value in MODE_SWITCH_POLICIES:
            self._mode_switch_policy = value
            self._save()

    @property
    def mode_switch_timeout(self) -> int:
        return self._mode_switch_timeout

    @mode_switch_timeout.setter
    def mode_switch_timeout(self, value: int):
        if value in MODE_SWITCH_TIMEOUT_STEPS:
            self._mode_switch_timeout = value
            self._save()

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

    def check_permission(self, cmd: str, cwd: str = "") -> Tuple[str, Optional[str]]:
        """Check if a command is allowed.

        Returns (decision, reason):
        - ("allow", None) — execute immediately
        - ("ask", reason) — need user approval
        - ("deny", reason) — blocked
        - ("ask_mandatory", reason) — must ask, no timeout (workspace boundary)
        """
        if self._is_catastrophic(cmd):
            return ("deny", "Blocked by base sandbox: potentially destructive command")

        if self._mode in ("ask", "plan"):
            if self._is_write_command(cmd):
                return ("deny", f"Write operations blocked in {self._mode} mode")

        if self._workspace_root and cwd:
            boundary_check = self._check_workspace_boundary(cmd, cwd)
            if boundary_check:
                if self._boundary_policy == "allow_all":
                    pass
                elif self._boundary_policy == "deny_all":
                    return ("deny", boundary_check)
                else:
                    return ("ask_mandatory", boundary_check)

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

    def check_edit_permission(self, path: str) -> Tuple[str, Optional[str]]:
        """Check if editing a file path is allowed (workspace boundary only).

        Returns ("allow", None) or ("ask_mandatory", reason) or ("deny", reason).
        """
        if not self._workspace_root:
            return ("allow", None)
        try:
            abs_path = os.path.realpath(path)
            ws_root = os.path.realpath(self._workspace_root)
            if not abs_path.startswith(ws_root + os.sep) and abs_path != ws_root:
                reason = f"Edit outside workspace: {os.path.basename(path)}"
                if self._boundary_policy == "allow_all":
                    return ("allow", None)
                elif self._boundary_policy == "deny_all":
                    return ("deny", reason)
                else:
                    return ("ask_mandatory", reason)
        except Exception:
            pass
        return ("allow", None)

    def create_pending(self, request_id: str, cmd: str, session_id: str = "",
                       mandatory: bool = False, kind: str = "exec") -> dict:
        """Create a pending permission request for the frontend."""
        pending = {
            "request_id": request_id,
            "cmd": cmd,
            "normalized": self._normalize_cmd(cmd),
            "session_id": session_id,
            "created_at": time.time(),
            "status": "pending",
            "decision": None,
            "persist": None,
            "mandatory": mandatory,
            "kind": kind,
        }
        with self._pending_lock:
            self._pending[request_id] = pending
        return {"decision": "ask", "request_id": request_id,
                "cmd": cmd, "normalized": self._normalize_cmd(cmd),
                "mandatory": mandatory, "kind": kind}

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

        if persist and pending.get("normalized") and not pending.get("mandatory"):
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
            "popup_timeout": self._popup_timeout,
            "boundary_policy": self._boundary_policy,
            "workspace_root": self._workspace_root,
            "mode_switch_policy": self._mode_switch_policy,
            "mode_switch_timeout": self._mode_switch_timeout,
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
    def _is_catastrophic(cmd: str) -> bool:
        """Layer 1: absolute protection against catastrophic commands."""
        stripped = cmd.strip().lower()
        for pat in CATASTROPHIC_PATTERNS:
            if pat.lower() in stripped:
                return True
        return False

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

    def _check_workspace_boundary(self, cmd: str, cwd: str) -> Optional[str]:
        """Layer 3: check if command operates outside workspace.

        Returns a reason string if outside, None if within.
        """
        if not self._workspace_root:
            return None
        ws_root = os.path.realpath(self._workspace_root)
        cwd_real = os.path.realpath(cwd)
        if not cwd_real.startswith(ws_root + os.sep) and cwd_real != ws_root:
            return f"Execution outside workspace boundary ({os.path.basename(cwd_real)})"
        return None


_instance: Optional[SandboxManager] = None
_instance_lock = threading.Lock()


def get_sandbox() -> SandboxManager:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = SandboxManager()
    return _instance
