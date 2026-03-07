"""Sandboxed command execution for OPENCLAW.

Provides a restricted filesystem view and command execution environment
for the remote agent. Protects critical system code (OPENCLAW itself,
CDMCP dependencies) from being accessed or modified.

Inspired by OpenClaw's sandboxed execution model:
- Boundary-safe file reads with path validation
- Protected workspace areas inaccessible to the agent
- Special --openclaw-* commands for self-improvement
"""
import os
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


PROTECTED_PATTERNS = [
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

ALLOWED_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find",
    "echo", "pwd", "tree", "file", "stat",
    "python3", "pip", "pip3",
    "npm", "npx", "node",
    "mkdir", "touch",
    "curl",
    "git",
    "--openclaw-experience", "--openclaw-status", "--openclaw-memory-search",
    "--openclaw-tool-help", "--openclaw-write-file", "--openclaw-web-search",
}

BLOCKED_COMMANDS = {
    "chmod", "chown", "chgrp",
    "kill", "pkill", "killall", "shutdown", "reboot",
    "ssh", "scp", "rsync",
    "sudo", "su", "doas",
    "open", "osascript",
}

def _is_project_tool(cmd: str) -> bool:
    """Check if a command corresponds to an installed project tool."""
    root = _get_project_root()
    tool_dir = root / "tool" / cmd
    if not tool_dir.exists():
        return False
    if is_path_protected(str(tool_dir)):
        return False
    return (tool_dir / "main.py").exists()

MAX_OUTPUT_LENGTH = 8000


def _get_project_root() -> Path:
    """Resolve project root."""
    return Path("/Applications/AITerminalTools")


def is_path_protected(path: str) -> bool:
    """Check if a path falls within protected areas."""
    norm = os.path.normpath(path).replace("\\", "/")
    # Remove leading project root if present
    root = str(_get_project_root())
    if norm.startswith(root):
        norm = norm[len(root):].lstrip("/")

    for pattern in PROTECTED_PATTERNS:
        if norm.startswith(pattern) or f"/{pattern}" in norm:
            return True
    return False


def filter_listing(entries: List[str], base_dir: str) -> List[str]:
    """Remove protected entries from a directory listing."""
    result = []
    for entry in entries:
        full = os.path.join(base_dir, entry)
        if not is_path_protected(full):
            result.append(entry)
    return result


def _resolve_path(path_arg: str) -> str:
    """Resolve a relative path against the project root."""
    root = _get_project_root()
    if path_arg.startswith("/"):
        p = Path(path_arg)
    else:
        p = root / path_arg

    try:
        resolved = p.resolve()
        root_resolved = root.resolve()
        if not str(resolved).startswith(str(root_resolved)):
            return ""
    except Exception:
        return ""

    return str(resolved)


def _handle_openclaw_experience(parts: list) -> Dict[str, Any]:
    """Record an experience/lesson from the agent."""
    lesson = " ".join(parts[1:]).strip().strip('"').strip("'")
    if not lesson:
        return {"ok": False, "error": "Usage: --openclaw-experience \"lesson text\""}

    learnings_dir = Path("/Applications/AITerminalTools/runtime/experience")
    learnings_dir.mkdir(parents=True, exist_ok=True)
    learnings_file = learnings_dir / "lessons.jsonl"

    import time as _time
    entry = {
        "lesson": lesson,
        "source": "openclaw-agent",
        "severity": "info",
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        with open(learnings_file, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"ok": True, "output": f"Experience recorded: {lesson}"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to record: {e}"}


def _handle_openclaw_status(_parts: list) -> Dict[str, Any]:
    """Report current project/tool status."""
    root = _get_project_root()
    tool_dir = root / "tool"

    status_lines = ["=== OPENCLAW Status ==="]

    # Tool count
    if tool_dir.exists():
        tools = [t for t in os.listdir(tool_dir) if (tool_dir / t / "tool.json").exists()]
        status_lines.append(f"Tools installed: {len(tools)}")

    # Skills count
    skills_dir = root / "skills" / "core"
    if skills_dir.exists():
        skill_count = len([s for s in os.listdir(skills_dir) if (skills_dir / s / "SKILL.md").exists()])
        status_lines.append(f"Core skills: {skill_count}")

    # Learnings count
    learnings_file = Path("/Applications/AITerminalTools/runtime/experience/lessons.jsonl")
    if learnings_file.exists():
        try:
            count = sum(1 for _ in open(learnings_file))
            status_lines.append(f"Recorded lessons: {count}")
        except Exception:
            pass

    return {"ok": True, "output": "\n".join(status_lines)}


def _handle_openclaw_memory_search(parts: list) -> Dict[str, Any]:
    """Search past lessons/experiences for relevant knowledge."""
    query = " ".join(parts[1:]).strip().strip('"').strip("'").lower()
    if not query:
        return {"ok": False, "error": 'Usage: --openclaw-memory-search "search query"'}

    learnings_file = Path("/Applications/AITerminalTools/runtime/experience/lessons.jsonl")
    if not learnings_file.exists():
        return {"ok": True, "output": "No lessons recorded yet."}

    results = []
    query_words = set(query.split())

    try:
        with open(learnings_file) as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line.strip())
                    lesson = entry.get("lesson", "")
                    tool = entry.get("tool", "")
                    context = entry.get("context", "")
                    severity = entry.get("severity", "info")
                    searchable = f"{lesson} {tool} {context}".lower()

                    # Score by word overlap
                    match_count = sum(1 for w in query_words if w in searchable)
                    if match_count > 0:
                        results.append((match_count, i, severity, tool, lesson))
                except Exception:
                    pass
    except Exception as e:
        return {"ok": False, "error": f"Failed to search: {e}"}

    if not results:
        return {"ok": True, "output": f"No lessons found matching '{query}'."}

    results.sort(key=lambda x: (-x[0], -x[1]))
    top = results[:10]

    lines = [f"Found {len(results)} matching lessons (showing top {len(top)}):"]
    for score, idx, severity, tool, lesson in top:
        tool_tag = f" [{tool}]" if tool else ""
        lines.append(f"  [{severity}]{tool_tag} {lesson}")

    return {"ok": True, "output": "\n".join(lines)}


def execute_command(command: str) -> Dict[str, Any]:
    """Execute a sandboxed command and return the output.

    The command is parsed, validated against allowed/blocked lists,
    and path arguments are checked against protected patterns.
    Special --openclaw-* commands are handled internally.
    """
    command = command.strip()
    if not command:
        return {"ok": False, "error": "Empty command"}

    parts = command.split()
    base_cmd = parts[0]

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

    if base_cmd in BLOCKED_COMMANDS:
        return {"ok": False, "error": f"Command '{base_cmd}' is not permitted"}

    # Check if it's a project tool (e.g., BILIBILI, GMAIL, etc.)
    if _is_project_tool(base_cmd):
        return _execute_project_tool(command)

    if base_cmd not in ALLOWED_COMMANDS:
        return {"ok": False, "error": f"Command '{base_cmd}' is not recognized. Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}"}

    # Check all path-like arguments
    for arg in parts[1:]:
        if arg.startswith("-"):
            continue
        resolved = _resolve_path(arg)
        if resolved and is_path_protected(resolved):
            return {"ok": False, "error": f"Access denied: '{arg}' is in a protected area"}

    # Special handling for 'ls' to filter protected entries
    if base_cmd == "ls":
        return _sandboxed_ls(parts)

    if base_cmd == "cat":
        return _sandboxed_cat(parts)

    # General execution with timeout
    try:
        root = str(_get_project_root())
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
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out (30s limit)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _sandboxed_ls(parts: list) -> Dict[str, Any]:
    """List directory with protected entries filtered out."""
    root = _get_project_root()
    target = str(root)

    flags = []
    for p in parts[1:]:
        if p.startswith("-"):
            flags.append(p)
        else:
            resolved = _resolve_path(p)
            if not resolved:
                return {"ok": False, "error": f"Invalid path: {p}"}
            if is_path_protected(resolved):
                return {"ok": False, "error": f"Access denied: '{p}'"}
            target = resolved

    try:
        entries = os.listdir(target)
        entries = filter_listing(entries, target)
        entries.sort()

        if "-l" in flags or "-la" in flags or "-al" in flags:
            lines = []
            for e in entries:
                full = os.path.join(target, e)
                try:
                    st = os.stat(full)
                    is_dir = os.path.isdir(full)
                    prefix = "d" if is_dir else "-"
                    size = st.st_size
                    lines.append(f"{prefix}  {size:>8}  {e}")
                except Exception:
                    lines.append(f"?         ?  {e}")
            return {"ok": True, "output": "\n".join(lines)}
        else:
            return {"ok": True, "output": "\n".join(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _sandboxed_cat(parts: list) -> Dict[str, Any]:
    """Read a file with protection checks."""
    if len(parts) < 2:
        return {"ok": False, "error": "Usage: cat <file>"}

    target = parts[1]
    resolved = _resolve_path(target)
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
    """Execute a project tool command (e.g., BILIBILI search ...).
    
    Runs the tool's main.py via Python as a subprocess.
    """
    root = _get_project_root()
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
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        output = output.strip()
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
        if result.returncode != 0:
            return {"ok": False, "error": output or f"Exit code {result.returncode}"}
        return {"ok": True, "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Tool '{tool_name}' timed out after 60s"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _handle_openclaw_write_file(command: str) -> Dict[str, Any]:
    """Write content to a file. Format: --openclaw-write-file <path> <content>
    
    The content is everything after the path argument. The path is validated
    against protected patterns. Parent directories are created automatically.
    """
    parts = command.split(None, 2)
    if len(parts) < 3:
        return {"ok": False, "error": "Usage: --openclaw-write-file <path> <content>"}
    
    target = parts[1]
    content = parts[2]
    
    resolved = _resolve_path(target)
    if not resolved:
        return {"ok": False, "error": f"Invalid path: {target}"}
    if is_path_protected(resolved):
        return {"ok": False, "error": f"Access denied: '{target}' is protected"}
    
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return {"ok": True, "output": f"Written {len(content)} bytes to {target}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _handle_openclaw_web_search(parts: list) -> Dict[str, Any]:
    """Search the web via the TAVILY tool if available."""
    if len(parts) < 2:
        return {"ok": False, "error": "Usage: --openclaw-web-search <query>"}
    
    query = " ".join(parts[1:]).strip('"').strip("'")
    root = _get_project_root()
    tavily_main = root / "tool" / "TAVILY" / "main.py"
    
    if not tavily_main.exists():
        return {"ok": False, "error": "TAVILY tool not installed. Use direct curl for web searches."}
    
    try:
        result = subprocess.run(
            ["python3", str(tavily_main), "search", query, "--limit", "5"],
            capture_output=True, text=True, timeout=30,
            cwd=str(root),
        )
        if result.returncode == 0:
            return {"ok": True, "output": result.stdout}
        return {"ok": False, "error": result.stderr or "Search failed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Search timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _handle_openclaw_tool_help(parts: list) -> Dict[str, Any]:
    """Return for_agent.md content of a specific tool, giving the remote agent
    immediate knowledge of the tool's commands and capabilities without needing
    to cat multiple files."""
    if len(parts) < 2:
        root = _get_project_root()
        tool_dir = root / "tool"
        tools = []
        if tool_dir.exists():
            for t in sorted(os.listdir(tool_dir)):
                if is_path_protected(tool_dir / t):
                    continue
                fa = tool_dir / t / "for_agent.md"
                tj = tool_dir / t / "tool.json"
                desc = ""
                if tj.exists():
                    try:
                        with open(tj) as f:
                            desc = json.load(f).get("description", "")
                    except Exception:
                        pass
                has_help = fa.exists()
                tools.append(f"  {t} {'[doc]' if has_help else '[no doc]'} {desc}")
        return {"ok": True, "output": "Usage: --openclaw-tool-help <TOOL_NAME>\n\nAvailable tools:\n" + "\n".join(tools)}

    tool_name = parts[1].upper()
    root = _get_project_root()
    fa_path = root / "tool" / tool_name / "for_agent.md"

    if is_path_protected(root / "tool" / tool_name):
        return {"ok": False, "error": f"Access denied: tool '{tool_name}' is protected"}

    if not fa_path.exists():
        readme = root / "tool" / tool_name / "README.md"
        if readme.exists():
            try:
                with open(readme, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) > MAX_OUTPUT_LENGTH:
                    content = content[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
                return {"ok": True, "output": f"[README.md for {tool_name}]\n{content}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"No documentation found for tool '{tool_name}'"}

    try:
        with open(fa_path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + "\n... [truncated]"
        return {"ok": True, "output": f"[for_agent.md for {tool_name}]\n{content}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_project_summary() -> str:
    """Generate a brief summary of the project structure for the remote agent."""
    root = _get_project_root()
    lines = ["Project: AITerminalTools", f"Root: {root}", ""]

    # Top-level directories
    lines.append("Top-level directories:")
    try:
        entries = sorted(os.listdir(root))
        entries = filter_listing(entries, str(root))
        for e in entries:
            full = root / e
            if full.is_dir():
                lines.append(f"  {e}/")
            elif full.is_file():
                lines.append(f"  {e}")
    except Exception:
        lines.append("  [error reading root]")

    # Tool list
    tool_dir = root / "tool"
    if tool_dir.exists():
        lines.append("")
        lines.append("Available tools:")
        tools = sorted(os.listdir(tool_dir))
        tools = filter_listing(tools, str(tool_dir))
        for t in tools:
            tool_json = tool_dir / t / "tool.json"
            desc = ""
            if tool_json.exists():
                try:
                    with open(tool_json) as f:
                        info = json.load(f)
                    desc = f" - {info.get('description', '')}"
                except Exception:
                    pass
            lines.append(f"  {t}{desc}")

    return "\n".join(lines)
