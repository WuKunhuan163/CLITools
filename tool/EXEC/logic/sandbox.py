"""Sandbox engine for command execution.

Three sandbox layers (applied in order, most restrictive wins):
1. Mode sandbox: ask/plan modes block all filesystem-modifying commands.
2. System sandbox: global policy (run-everything / ask-every-time).
3. Command sandbox: per-command policy (run-always / run-once / forbidden).

Additionally, workspace boundary protection requires explicit user approval
for any command that accesses files/directories outside the project root.

Provides:
- Policy-based command access control (allow / deny per command)
- Protected path patterns that block filesystem access
- Allowed / blocked command lists with user-friendly hints
- Interactive permission prompting for unknown commands
- Sandboxed path resolution within the project root
- Workspace boundary detection for external file access
"""
import os
import json
import re
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

def _get_project_root() -> Path:
    """Resolve project root by walking up from this file to find bin/TOOL."""
    cur = Path(__file__).resolve().parent
    while cur != cur.parent:
        if (cur / "bin" / "TOOL").exists():
            return cur
        cur = cur.parent
    return Path(__file__).resolve().parent.parent.parent.parent


_PROJECT_ROOT = _get_project_root()

# ---------------------------------------------------------------------------
# Policy storage
# ---------------------------------------------------------------------------

_SANDBOX_FILE = _PROJECT_ROOT / "tool" / "EXEC" / "data" / "sandbox.json"
_POLICIES_CACHE: Dict[str, str] = {}
_POLICIES_LOADED = False


def _load_policies():
    global _POLICIES_CACHE, _POLICIES_LOADED
    if _POLICIES_LOADED:
        return
    _POLICIES_LOADED = True
    if _SANDBOX_FILE.exists():
        try:
            data = json.loads(_SANDBOX_FILE.read_text())
            _POLICIES_CACHE = data.get("policies", {})
        except Exception:
            _POLICIES_CACHE = {}


def _save_policies():
    _SANDBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if _SANDBOX_FILE.exists():
        try:
            existing = json.loads(_SANDBOX_FILE.read_text())
        except Exception:
            pass
    existing["policies"] = _POLICIES_CACHE
    _SANDBOX_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))


def reload_policies():
    """Force-reload policies from disk (useful after external edits)."""
    global _POLICIES_LOADED
    _POLICIES_LOADED = False
    _load_policies()


def get_command_policy(cmd: str) -> Optional[str]:
    """Return stored policy for *cmd*: ``'allow'``, ``'deny'``, or ``None``."""
    _load_policies()
    return _POLICIES_CACHE.get(cmd)


def set_command_policy(cmd: str, policy: str):
    """Persist a policy (``'allow'`` or ``'deny'``) for *cmd*."""
    _load_policies()
    _POLICIES_CACHE[cmd] = policy
    _save_policies()


def remove_command_policy(cmd: str) -> bool:
    """Remove the stored policy for *cmd*. Returns ``True`` if it existed."""
    _load_policies()
    if cmd in _POLICIES_CACHE:
        del _POLICIES_CACHE[cmd]
        _save_policies()
        return True
    return False


def list_policies() -> Dict[str, str]:
    """Return all stored ``{command: policy}`` pairs."""
    _load_policies()
    return dict(_POLICIES_CACHE)

# ---------------------------------------------------------------------------
# Protected paths
# ---------------------------------------------------------------------------

PROTECTED_PATTERNS: List[str] = [
    "tool/OPENCLAW",
    "tool/GOOGLE.CDMCP",
    "tool/GOOGLE/logic/chrome",
    "logic/chrome",
    "logic/cdmcp_loader.py",
    ".cursor",
    ".git",
    "data/run",
    "data/input",
    "bin/TOOL",
]


def is_path_protected(path: str) -> bool:
    """Return ``True`` if *path* falls within a protected area."""
    norm = os.path.normpath(path).replace("\\", "/")
    root = str(_PROJECT_ROOT)
    if norm.startswith(root):
        norm = norm[len(root):].lstrip("/")
    for pattern in PROTECTED_PATTERNS:
        if norm.startswith(pattern) or f"/{pattern}" in norm:
            return True
    return False


def filter_listing(entries: List[str], base_dir: str) -> List[str]:
    """Remove protected entries from a directory listing."""
    return [e for e in entries if not is_path_protected(os.path.join(base_dir, e))]

# ---------------------------------------------------------------------------
# Command allow / block
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find",
    "echo", "pwd", "tree", "file", "stat",
    "python3", "pip", "pip3",
    "npm", "npx", "node",
    "mkdir", "touch",
    "curl",
    "git",
}

BLOCKED_COMMANDS = {
    "chmod", "chown", "chgrp",
    "kill", "pkill", "killall", "shutdown", "reboot",
    "ssh", "scp", "rsync",
    "sudo", "su", "doas",
    "open", "osascript",
}

_BLOCKED_HINTS: Dict[str, str] = {
    "open": "Use project tools instead.",
    "osascript": "Use project tools instead.",
    "ssh": "Use curl for HTTP requests. Direct SSH is not allowed.",
    "sudo": "Elevated privileges are not available. Try the command without sudo.",
}


def get_blocked_hint(cmd: str) -> str:
    """Return a hint explaining why *cmd* is blocked."""
    return _BLOCKED_HINTS.get(cmd, "This command is not permitted in the sandbox.")


def classify_command(cmd: str) -> str:
    """Classify *cmd* as ``'allowed'``, ``'blocked'``, ``'policy_allow'``,
    ``'policy_deny'``, or ``'unknown'``."""
    if cmd in BLOCKED_COMMANDS:
        return "blocked"
    if cmd in ALLOWED_COMMANDS:
        return "allowed"
    policy = get_command_policy(cmd)
    if policy == "allow":
        return "policy_allow"
    if policy == "deny":
        return "policy_deny"
    return "unknown"


def is_project_tool(cmd: str) -> bool:
    """Return ``True`` if *cmd* maps to an installed project tool."""
    tool_dir = _PROJECT_ROOT / "tool" / cmd
    if not tool_dir.exists() or is_path_protected(str(tool_dir)):
        return False
    return (tool_dir / "main.py").exists()

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_path(path_arg: str) -> str:
    """Resolve *path_arg* against the project root.

    Returns the absolute path string, or ``""`` if the path escapes the
    project root or cannot be resolved.
    """
    if path_arg.startswith("/"):
        p = Path(path_arg)
    else:
        p = _PROJECT_ROOT / path_arg

    try:
        resolved = p.resolve()
        root_resolved = _PROJECT_ROOT.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            return ""
    except Exception:
        return ""
    return str(resolved)

# ---------------------------------------------------------------------------
# Interactive permission prompt
# ---------------------------------------------------------------------------

def prompt_permission(cmd: str, default_idx: int = 2) -> str:
    """Interactively ask the user to allow or deny *cmd*.

    Returns ``'allow_always'``, ``'allow_once'``, or ``'deny'``.
    """
    try:
        from interface.turing import select_horizontal
        from interface.config import get_color
        BOLD = get_color("BOLD")
        RESET = get_color("RESET")

        print(f"    {BOLD}Unknown command:{RESET} {cmd}")
        choice = select_horizontal(
            "Allow?",
            ["Run Always", "Run Once", "Reject"],
            default_index=default_idx,
            timeout=30,
        )
        if choice is None or choice == 2:
            return "deny"
        elif choice == 0:
            set_command_policy(cmd, "allow")
            return "allow_always"
        else:
            return "allow_once"
    except Exception:
        return "deny"

# ---------------------------------------------------------------------------
# System sandbox policy
# ---------------------------------------------------------------------------

SYSTEM_POLICIES = ["run_everything", "ask_every_time"]
_system_policy: str = "ask_every_time"


def get_system_policy() -> str:
    """Current system-level sandbox policy."""
    _load_policies()
    data = {}
    if _SANDBOX_FILE.exists():
        try:
            data = json.loads(_SANDBOX_FILE.read_text())
        except Exception:
            pass
    return data.get("system_policy", "ask_every_time")


def set_system_policy(policy: str):
    """Set the system-level sandbox policy."""
    if policy not in SYSTEM_POLICIES:
        raise ValueError(f"Invalid policy: {policy}. Must be one of {SYSTEM_POLICIES}")
    _SANDBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if _SANDBOX_FILE.exists():
        try:
            data = json.loads(_SANDBOX_FILE.read_text())
        except Exception:
            pass
    data["system_policy"] = policy
    _SANDBOX_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Mode sandbox
# ---------------------------------------------------------------------------

FS_MODIFYING_COMMANDS = {
    "rm", "rmdir", "mv", "cp", "mkdir", "touch", "chmod", "chown",
    "ln", "unlink", "tee", "truncate", "dd",
    "git commit", "git push", "git reset", "git checkout",
    "pip install", "pip uninstall", "npm install", "npm uninstall",
}

_WRITE_INDICATORS = {
    ">", ">>", "tee", "sed -i", "mv ", "cp ", "rm ", "mkdir ", "touch ",
}


def is_fs_modifying(cmd_line: str) -> bool:
    """Heuristic check if a command line modifies the filesystem."""
    stripped = cmd_line.strip()
    for pattern in _WRITE_INDICATORS:
        if pattern in stripped:
            return True
    base = stripped.split()[0] if stripped else ""
    return base in FS_MODIFYING_COMMANDS


def mode_allows_command(mode: str, cmd_line: str) -> Tuple[bool, str]:
    """Check if current mode permits the command.

    Returns (allowed, reason).
    ask/plan modes block filesystem-modifying commands.
    agent mode allows everything (defers to system/command sandbox).
    """
    if mode in ("ask", "plan"):
        if is_fs_modifying(cmd_line):
            return False, f"Mode '{mode}' blocks filesystem-modifying commands."
    return True, ""


# ---------------------------------------------------------------------------
# Workspace boundary detection
# ---------------------------------------------------------------------------

_PATH_ARG_PATTERNS = [
    re.compile(r'(?:cat|head|tail|less|more|vi|vim|nano|code|open)\s+(.+)'),
    re.compile(r'(?:cd)\s+(.+)'),
    re.compile(r'(?:rm|rmdir|mkdir|touch|mv|cp|ln)\s+(?:-[a-zA-Z]*\s+)*(.+)'),
    re.compile(r'>+\s*(.+)'),
]


def extract_paths_from_command(cmd_line: str) -> List[str]:
    """Extract file/directory path arguments from a command line."""
    paths = []
    try:
        parts = shlex.split(cmd_line)
    except ValueError:
        parts = cmd_line.split()

    for part in parts:
        if part.startswith("/") or part.startswith("~") or part.startswith(".."):
            paths.append(part)
        elif "/" in part and not part.startswith("-") and not part.startswith("http"):
            if os.path.isabs(part):
                paths.append(part)
    return paths


def is_outside_workspace(path: str) -> bool:
    """Check if a resolved path is outside the project workspace."""
    try:
        p = Path(path).expanduser().resolve()
        root = _PROJECT_ROOT.resolve()
        return not str(p).startswith(str(root))
    except Exception:
        return True


def check_workspace_boundary(cmd_line: str) -> Tuple[bool, List[str]]:
    """Check if a command accesses paths outside the workspace.

    Returns (has_external, list_of_external_paths).
    """
    paths = extract_paths_from_command(cmd_line)
    external = []
    for p in paths:
        expanded = os.path.expanduser(p)
        if os.path.isabs(expanded):
            if is_outside_workspace(expanded):
                external.append(expanded)
        elif p.startswith(".."):
            try:
                resolved = str(Path(p).resolve())
                if is_outside_workspace(resolved):
                    external.append(resolved)
            except Exception:
                external.append(p)
    return bool(external), external


# ---------------------------------------------------------------------------
# Unified sandbox decision
# ---------------------------------------------------------------------------

class SandboxDecision:
    """Result of sandbox evaluation."""
    __slots__ = ("allowed", "reason", "requires_prompt", "prompt_type",
                 "external_paths", "command")

    def __init__(self, allowed: bool = True, reason: str = "",
                 requires_prompt: bool = False, prompt_type: str = "",
                 external_paths: Optional[List[str]] = None,
                 command: str = ""):
        self.allowed = allowed
        self.reason = reason
        self.requires_prompt = requires_prompt
        self.prompt_type = prompt_type
        self.external_paths = external_paths or []
        self.command = command


def evaluate_sandbox(cmd_line: str, mode: str = "agent") -> SandboxDecision:
    """Evaluate all sandbox layers for a command.

    Applies layers in order:
    1. Mode sandbox (ask/plan blocks FS writes)
    2. Blocked command list (always denied)
    3. Workspace boundary check (external paths need approval)
    4. System sandbox policy
    5. Command-level policy

    Returns a SandboxDecision indicating whether to proceed, block, or prompt.
    """
    base_cmd = cmd_line.strip().split()[0] if cmd_line.strip() else ""

    allowed, reason = mode_allows_command(mode, cmd_line)
    if not allowed:
        return SandboxDecision(allowed=False, reason=reason, command=base_cmd)

    cls = classify_command(base_cmd)
    if cls == "blocked":
        return SandboxDecision(
            allowed=False,
            reason=get_blocked_hint(base_cmd),
            command=base_cmd,
        )
    if cls == "policy_deny":
        return SandboxDecision(
            allowed=False,
            reason=f"Command '{base_cmd}' is forbidden by policy.",
            command=base_cmd,
        )

    has_external, ext_paths = check_workspace_boundary(cmd_line)
    if has_external:
        return SandboxDecision(
            allowed=False,
            requires_prompt=True,
            prompt_type="workspace_boundary",
            external_paths=ext_paths,
            reason=f"Accesses paths outside workspace: {', '.join(ext_paths)}",
            command=base_cmd,
        )

    sys_policy = get_system_policy()
    if sys_policy == "run_everything":
        if cls in ("allowed", "policy_allow"):
            return SandboxDecision(allowed=True, command=base_cmd)
        return SandboxDecision(allowed=True, command=base_cmd)

    if cls == "allowed" or cls == "policy_allow":
        return SandboxDecision(allowed=True, command=base_cmd)

    if cls == "unknown":
        return SandboxDecision(
            allowed=False,
            requires_prompt=True,
            prompt_type="unknown_command",
            reason=f"Unknown command: {base_cmd}",
            command=base_cmd,
        )

    return SandboxDecision(allowed=True, command=base_cmd)


# ---------------------------------------------------------------------------
# Convenience: project root accessor
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    return _PROJECT_ROOT


MAX_OUTPUT_LENGTH = 8000
