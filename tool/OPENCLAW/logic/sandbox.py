"""Sandboxed command execution for OPENCLAW.

Core sandbox engine (policies, path protection, command classification)
is provided by the EXEC tool. This module adds OPENCLAW-specific
command handlers (--openclaw-*) and the high-level execute_command()
dispatcher.
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from tool.EXEC.interface.main import (  # noqa: F401 — re-exports for cli.py
    set_command_policy,
    list_policies,
    is_path_protected,
    filter_listing,
    resolve_path,
    classify_command,
    get_blocked_hint,
    is_project_tool,
    prompt_permission,
    get_project_root,
    ALLOWED_COMMANDS,
    BLOCKED_COMMANDS,
    MAX_OUTPUT_LENGTH,
)


def execute_command(command: str) -> Dict[str, Any]:
    """Execute a sandboxed command and return the result.

    Special ``--openclaw-*`` commands are handled internally.
    All others go through the EXEC sandbox policy engine.
    """
    command = command.strip()
    if not command:
        return {"ok": False, "error": "Empty command"}

    parts = command.split()
    base_cmd = parts[0]

    # OPENCLAW-specific intrinsics
    if base_cmd == "--openclaw-experience":
        return _handle_openclaw_experience(parts)
    if base_cmd == "--openclaw-status":
        return _handle_openclaw_status(parts)
    if base_cmd == "--openclaw-memory-search":
        return _handle_openclaw_memory_search(parts)
    if base_cmd == "--openclaw-tool-help":
        return _handle_openclaw_tool_help(parts)
    if base_cmd == "--openclaw-write-file":
        return _handle_openclaw_write_file(command)
    if base_cmd == "--openclaw-web-search":
        return _handle_openclaw_web_search(parts)

    # Delegate to sandbox engine
    cls = classify_command(base_cmd)

    if cls == "blocked":
        hint = get_blocked_hint(base_cmd)
        msg = f"Command '{base_cmd}' is not permitted."
        if hint:
            msg += f" {hint}"
        return {"ok": False, "error": msg, "error_type": "sandbox_blocked"}

    if cls == "policy_deny":
        return {"ok": False,
                "error": f"Command '{base_cmd}' is denied by policy.",
                "error_type": "sandbox_denied"}

    if cls == "unknown":
        if is_project_tool(base_cmd):
            return _execute_project_tool(command)
        decision = prompt_permission(base_cmd)
        if decision == "deny":
            set_command_policy(base_cmd, "deny")
            return {"ok": False,
                    "error": f"Command '{base_cmd}' rejected by user.",
                    "error_type": "sandbox_rejected"}

    # Check path arguments for protected areas
    for arg in parts[1:]:
        if arg.startswith("-"):
            continue
        resolved = resolve_path(arg)
        if resolved and is_path_protected(resolved):
            return {"ok": False, "error": f"Access denied: '{arg}' is in a protected area.",
                    "error_type": "sandbox_protected"}

    if base_cmd == "ls":
        return _sandboxed_ls(parts)
    if base_cmd == "cat":
        return _sandboxed_cat(parts)

    root = str(get_project_root())
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=root,
            env={**os.environ, "HOME": root}
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr] " + result.stderr
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
        return {
            "ok": result.returncode == 0,
            "output": output.strip(),
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out (30s limit)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Sandboxed built-ins
# ---------------------------------------------------------------------------

def _sandboxed_ls(parts: list) -> Dict[str, Any]:
    root = get_project_root()
    target = str(root)
    flags = []
    for p in parts[1:]:
        if p.startswith("-"):
            flags.append(p)
        else:
            resolved = resolve_path(p)
            if not resolved:
                return {"ok": False, "error": f"Invalid path: {p}"}
            if is_path_protected(resolved):
                return {"ok": False, "error": f"Access denied: '{p}'"}
            target = resolved
    try:
        entries = sorted(os.listdir(target))
        entries = filter_listing(entries, target)
        if "-l" in flags or "-la" in flags or "-al" in flags:
            lines = []
            for e in entries:
                full = os.path.join(target, e)
                try:
                    st = os.stat(full)
                    is_dir = os.path.isdir(full)
                    prefix = "d" if is_dir else "-"
                    lines.append(f"{prefix}  {st.st_size:>8}  {e}")
                except Exception:
                    lines.append(f"?         ?  {e}")
            return {"ok": True, "output": "\n".join(lines)}
        return {"ok": True, "output": "\n".join(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _sandboxed_cat(parts: list) -> Dict[str, Any]:
    if len(parts) < 2:
        return {"ok": False, "error": "Usage: cat <file>"}
    target = parts[1]
    resolved = resolve_path(target)
    if not resolved:
        return {"ok": False, "error": f"Invalid path: {target}"}
    if is_path_protected(resolved):
        return {"ok": False, "error": f"Access denied: '{target}'"}
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
        return {"ok": True, "output": content}
    except FileNotFoundError:
        return {"ok": False, "error": f"File not found: {target}"}
    except IsADirectoryError:
        return {"ok": False, "error": f"Is a directory: {target}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _execute_project_tool(command: str) -> Dict[str, Any]:
    root = get_project_root()
    parts = command.split()
    tool_name = parts[0]
    tool_args = parts[1:] if len(parts) > 1 else []
    tool_main = root / "tool" / tool_name / "main.py"
    if not tool_main.exists():
        return {"ok": False, "error": f"Tool '{tool_name}' main.py not found"}
    try:
        result = subprocess.run(
            ["python3", str(tool_main)] + tool_args,
            capture_output=True, text=True, timeout=60,
            cwd=str(root),
            env={**os.environ, "PYTHONPATH": str(root)},
        )
        output = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
        if result.returncode != 0:
            return {"ok": False, "error": output or f"Exit code {result.returncode}"}
        return {"ok": True, "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Tool '{tool_name}' timed out after 60s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# OPENCLAW intrinsic commands
# ---------------------------------------------------------------------------

def _handle_openclaw_experience(parts: list) -> Dict[str, Any]:
    lesson = " ".join(parts[1:]).strip().strip('"').strip("'")
    if not lesson:
        return {"ok": False, "error": 'Usage: --openclaw-experience "lesson text"'}
    import time as _time
    learnings_dir = get_project_root() / "runtime" / "_" / "eco" / "experience"
    learnings_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "lesson": lesson,
        "source": "openclaw-agent",
        "severity": "info",
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        with open(learnings_dir / "lessons.jsonl", "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"ok": True, "output": f"Experience recorded: {lesson}"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to record: {e}"}


def _handle_openclaw_status(_parts: list) -> Dict[str, Any]:
    root = get_project_root()
    lines = ["=== OPENCLAW Status ==="]
    tool_dir = root / "tool"
    if tool_dir.exists():
        tools = [t for t in os.listdir(tool_dir) if (tool_dir / t / "tool.json").exists()]
        lines.append(f"Tools installed: {len(tools)}")
    skills_dir = root / "skills"
    if skills_dir.exists():
        count = sum(1 for _ in skills_dir.rglob("SKILL.md"))
        lines.append(f"Skills: {count}")
    learnings_file = root / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
    if learnings_file.exists():
        try:
            count = sum(1 for _ in open(learnings_file))
            lines.append(f"Recorded lessons: {count}")
        except Exception:
            pass
    return {"ok": True, "output": "\n".join(lines)}


def _handle_openclaw_memory_search(parts: list) -> Dict[str, Any]:
    query = " ".join(parts[1:]).strip().strip('"').strip("'").lower()
    if not query:
        return {"ok": False, "error": 'Usage: --openclaw-memory-search "query"'}
    learnings_file = get_project_root() / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl"
    if not learnings_file.exists():
        return {"ok": True, "output": "No lessons recorded yet."}
    results = []
    query_words = set(query.split())
    try:
        with open(learnings_file) as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line.strip())
                    searchable = f"{entry.get('lesson','')} {entry.get('tool','')} {entry.get('context','')}".lower()
                    score = sum(1 for w in query_words if w in searchable)
                    if score > 0:
                        results.append((score, i, entry.get("severity", "info"),
                                        entry.get("tool", ""), entry.get("lesson", "")))
                except Exception:
                    pass
    except Exception as e:
        return {"ok": False, "error": f"Failed to search: {e}"}
    if not results:
        return {"ok": True, "output": f"No lessons found matching '{query}'."}
    results.sort(key=lambda x: (-x[0], -x[1]))
    top = results[:10]
    lines = [f"Found {len(results)} matching lessons (showing top {len(top)}):"]
    for _, _, severity, tool, lesson in top:
        tag = f" [{tool}]" if tool else ""
        lines.append(f"  [{severity}]{tag} {lesson}")
    return {"ok": True, "output": "\n".join(lines)}


def _handle_openclaw_tool_help(parts: list) -> Dict[str, Any]:
    root = get_project_root()
    if len(parts) < 2:
        tool_dir = root / "tool"
        tools = []
        if tool_dir.exists():
            for t in sorted(os.listdir(tool_dir)):
                if is_path_protected(str(tool_dir / t)):
                    continue
                fa = tool_dir / t / "AGENT.md"
                tj = tool_dir / t / "tool.json"
                desc = ""
                if tj.exists():
                    try:
                        desc = json.load(open(tj)).get("description", "")
                    except Exception:
                        pass
                tools.append(f"  {t} {'[doc]' if fa.exists() else '[no doc]'} {desc}")
        return {"ok": True, "output": "Usage: --openclaw-tool-help <TOOL>\n\nAvailable tools:\n" + "\n".join(tools)}

    tool_name = parts[1].upper()
    if is_path_protected(str(root / "tool" / tool_name)):
        return {"ok": False, "error": f"Access denied: tool '{tool_name}' is protected"}
    for fname in ("AGENT.md", "README.md"):
        fpath = root / "tool" / tool_name / fname
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                if len(content) > MAX_OUTPUT_LENGTH:
                    content = content[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
                return {"ok": True, "output": f"[{fname} for {tool_name}]\n{content}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
    return {"ok": False, "error": f"No documentation found for tool '{tool_name}'"}


def _handle_openclaw_write_file(command: str) -> Dict[str, Any]:
    parts = command.split(None, 2)
    if len(parts) < 3:
        return {"ok": False, "error": "Usage: --openclaw-write-file <path> <content>"}
    target, content = parts[1], parts[2]
    resolved = resolve_path(target)
    if not resolved:
        return {"ok": False, "error": f"Invalid path: {target}"}
    if is_path_protected(resolved):
        return {"ok": False, "error": f"Access denied: '{target}' is protected"}
    try:
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        Path(resolved).write_text(content, encoding="utf-8")
        return {"ok": True, "output": f"Written {len(content)} bytes to {target}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _handle_openclaw_web_search(parts: list) -> Dict[str, Any]:
    if len(parts) < 2:
        return {"ok": False, "error": "Usage: --openclaw-web-search <query>"}
    query = " ".join(parts[1:]).strip('"').strip("'")
    root = get_project_root()
    tavily_main = root / "tool" / "TAVILY" / "main.py"
    if not tavily_main.exists():
        return {"ok": False, "error": "TAVILY tool not installed."}
    try:
        result = subprocess.run(
            ["python3", str(tavily_main), "search", query, "--limit", "5"],
            capture_output=True, text=True, timeout=30, cwd=str(root),
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout}
        return {"ok": False, "error": result.stderr or "Search failed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Search timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_SUMMARY_HIDDEN = frozenset({
    ".DS_Store", "__init__.py", "__pycache__", ".git", ".cursor",
    "node_modules", ".mypy_cache", ".pytest_cache",
})


def get_project_summary() -> str:
    """Generate a brief summary of the project structure for the remote agent."""
    root = get_project_root()
    lines = [f"Root: {root}", ""]
    lines.append("Top-level directories:")
    try:
        entries = sorted(os.listdir(root))
        entries = filter_listing(entries, str(root))
        for e in entries:
            if e in _SUMMARY_HIDDEN:
                continue
            full = root / e
            lines.append(f"  {e}/" if full.is_dir() else f"  {e}")
    except Exception:
        lines.append("  [error reading root]")
    return "\n".join(lines)
