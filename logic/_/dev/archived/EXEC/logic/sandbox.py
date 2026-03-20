"""Sandbox engine for command execution.

Provides:
- Policy-based command access control (allow / deny per command)
- Protected path patterns that block filesystem access
- Allowed / blocked command lists with user-friendly hints
- Interactive permission prompting for unknown commands
- Sandboxed path resolution within the project root
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

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
    return Path("/Applications/AITerminalTools")


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
        from logic.turing.select import select_horizontal
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
# Convenience: project root accessor
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    return _PROJECT_ROOT


MAX_OUTPUT_LENGTH = 8000
