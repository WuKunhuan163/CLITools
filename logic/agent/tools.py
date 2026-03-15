"""Agent tool definitions and handlers.

Defines the standard tools available to any agent (exec, read_file,
write_file, edit_file, search, ask_user, todo) and their handlers.

Modes:
- agent: Full access to all tools.
- ask:   Read-only. No write_file, edit_file. exec restricted to read-only commands.
- plan:  Read-only. Same restrictions as ask, plus exec blocks scripts entirely.
"""
import os
import subprocess
import shutil
from typing import Any, Callable, Dict, List, Optional

from logic.agent.state import AgentEnvironment


BUILTIN_TOOL_DEFS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Execute a shell command and return output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file. Content must be the COMPLETE file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Full file content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace specific text in a file. First read_file to see current content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_text": {"type": "string", "description": "Exact text to find"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search for files or text patterns in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex/glob)"},
                    "path": {"type": "string", "description": "Directory to search in (default: cwd)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question and wait for response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "Manage a TODO list: init, update, or delete items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["init", "update", "delete"]},
                    "items": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["action"],
            },
        },
    },
]


READONLY_SAFE_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "file",
    "echo", "pwd", "tree", "stat", "which", "type", "env", "printenv",
    "uname", "date", "whoami", "hostname", "df", "du",
    "python3 -c", "python3 -m",
    "git status", "git log", "git diff", "git show", "git branch",
}

READONLY_BLOCKED_PATTERNS = [
    "rm ", "mv ", "cp ", "mkdir ", "touch ", "chmod ", "chown ",
    "sed ", "awk ", "tee ", "dd ", "> ", ">> ",
    "python3 -c \"import os; os.remove", "python3 -c \"open(",
    "npm install", "pip install", "pip3 install",
]


def _is_readonly_safe(cmd: str) -> bool:
    """Check if a command is safe for read-only mode.

    Blocks destructive commands AND script execution (scripts can write files).
    """
    cmd_stripped = cmd.strip()
    for blocked in READONLY_BLOCKED_PATTERNS:
        if blocked in cmd_stripped:
            return False
    first_word = cmd_stripped.split()[0] if cmd_stripped.split() else ""
    if first_word in {"rm", "mv", "cp", "mkdir", "touch", "chmod", "chown",
                      "chgrp", "kill", "pkill", "killall", "sudo", "su",
                      "ssh", "scp", "rsync", "open", "osascript",
                      "shutdown", "reboot", "tee", "dd"}:
        return False
    script_runners = {"python3", "python", "node", "ruby", "perl", "php"}
    if first_word in script_runners:
        if "-c" not in cmd_stripped and "-m" not in cmd_stripped:
            return False
    return True


def _is_plan_safe(cmd: str) -> bool:
    """Plan mode: strictest. Block all scripts including inline (-c)."""
    if not _is_readonly_safe(cmd):
        return False
    cmd_stripped = cmd.strip()
    first_word = cmd_stripped.split()[0] if cmd_stripped.split() else ""
    script_runners = {"python3", "python", "node", "bash", "sh", "zsh",
                      "ruby", "perl", "php"}
    if first_word in script_runners:
        return False
    return True


def get_tool_defs_for_mode(mode: str = "agent") -> List[Dict[str, Any]]:
    """Return tool definitions appropriate for the given mode."""
    if mode == "agent":
        return list(BUILTIN_TOOL_DEFS)

    readonly_tools = []
    writable_names = {"write_file", "edit_file", "todo"}
    for td in BUILTIN_TOOL_DEFS:
        fname = td.get("function", {}).get("name", "")
        if fname in writable_names:
            continue
        if fname == "exec":
            readonly_exec = {
                "type": "function",
                "function": {
                    "name": "exec",
                    "description": (
                        "Execute a READ-ONLY shell command. "
                        "FORBIDDEN: rm, mv, cp, mkdir, touch, chmod, tee, "
                        "redirect (>), pip/npm install, or running scripts. "
                        "Only ls, cat, grep, rg, find, git status/log/diff, etc."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string",
                                        "description": "Read-only shell command"},
                        },
                        "required": ["command"],
                    },
                },
            }
            readonly_tools.append(readonly_exec)
        else:
            readonly_tools.append(td)
    return readonly_tools


class ToolHandlers:
    """Standard tool handler implementations for the agent loop."""

    DEFAULT_EXEC_TIMEOUT = 30

    def __init__(self, cwd: str, project_root: str,
                 env: Optional[AgentEnvironment] = None,
                 emit: Optional[Callable] = None,
                 mode: str = "agent",
                 exec_timeout: Optional[int] = None):
        self._cwd = cwd
        self._project_root = project_root
        self._env = env
        self._emit = emit or (lambda evt: None)
        self._mode = mode
        self._exec_timeout = exec_timeout or self.DEFAULT_EXEC_TIMEOUT
        self._write_history: Dict[str, list] = {}
        self._dup_counts: Dict[str, int] = {}
        self._turn_writes: List[str] = []
        self._turn_reads: List[str] = []
        self._quality_warnings: Dict[str, List[str]] = {}
        self._handlers: Dict[str, Callable] = {
            "exec": self.handle_exec,
            "read_file": self.handle_read_file,
            "write_file": self.handle_write_file,
            "edit_file": self.handle_edit_file,
            "search": self.handle_search,
            "ask_user": self.handle_ask_user,
            "todo": self.handle_todo,
        }

    def get(self, name: str) -> Optional[Callable]:
        return self._handlers.get(name)

    def register(self, name: str, handler: Callable):
        self._handlers[name] = handler

    def reset_turn(self):
        """Reset per-turn tracking."""
        self._turn_writes = []
        self._turn_reads = []
        self._quality_warnings = {}

    @property
    def unverified_writes(self) -> List[str]:
        reads = set(self._turn_reads)
        return [w for w in self._turn_writes if w not in reads]

    @property
    def unfixed_quality_warnings(self) -> Dict[str, List[str]]:
        return dict(self._quality_warnings)

    def handle_exec(self, args: dict) -> dict:
        cmd = args.get("command", "")
        if self._mode in ("ask", "plan"):
            checker = _is_plan_safe if self._mode == "plan" else _is_readonly_safe
            if not checker(cmd):
                msg = (f"BLOCKED: '{cmd}' is not allowed in {self._mode} mode. "
                       f"Only read-only commands (ls, cat, grep, find, git log, etc.) are permitted.")
                self._emit({"type": "tool", "name": "exec", "desc": cmd, "cmd": cmd})
                self._emit({"type": "tool_result", "ok": False, "output": msg})
                return {"ok": False, "output": msg}
        self._emit({"type": "tool", "name": "exec", "desc": cmd, "cmd": cmd})

        env = os.environ.copy()
        extra_paths = []
        bin_dir = os.path.join(self._project_root, "bin")
        if os.path.isdir(bin_dir):
            extra_paths.extend(
                os.path.join(bin_dir, d) for d in os.listdir(bin_dir)
                if os.path.isdir(os.path.join(bin_dir, d)))
        for p in ["/opt/homebrew/bin", "/usr/local/bin"]:
            if os.path.isdir(p):
                extra_paths.append(p)
        if extra_paths:
            env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")

        foreground_timeout = self._exec_timeout
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=foreground_timeout, cwd=self._cwd, env=env)
            output = result.stdout + result.stderr
            ok = result.returncode == 0
            self._emit({"type": "tool_result", "ok": ok, "output": output[:3000]})
            if self._env:
                self._env.record_result(cmd, ok, output[:300])
                if not ok:
                    self._env.record_error(f"Command failed: {cmd}")
            return {"ok": ok, "output": output[:3000]}
        except subprocess.TimeoutExpired:
            bg_result = self._background_exec(cmd, env)
            return bg_result
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if self._env:
                self._env.record_result(cmd, False, str(e))
            return {"ok": False, "output": str(e)}

    def _background_exec(self, cmd: str, env: dict) -> dict:
        """Move a timed-out command to background execution."""
        import tempfile, threading
        log_dir = os.path.join(self._project_root, "tmp", "bg_exec")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"bg_{os.getpid()}_{id(cmd) & 0xFFFF:04x}.log")

        proc = subprocess.Popen(
            cmd, shell=True, stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT, cwd=self._cwd, env=env)

        msg = (f"Command exceeded {self._exec_timeout}s foreground timeout. "
               f"Moved to background (PID: {proc.pid}). "
               f"Output: {log_file}")
        self._emit({"type": "tool_result", "ok": True, "output": msg})
        if self._env:
            self._env.record_result(cmd, True, f"Background PID={proc.pid}")
        return {"ok": True, "output": msg}

    def handle_read_file(self, args: dict) -> dict:
        path = args.get("path", "")
        if not os.path.isabs(path):
            path = os.path.join(self._cwd, path)
        self._turn_reads.append(path)
        self._emit({"type": "tool", "name": "read", "desc": path, "cmd": path})
        try:
            if os.path.isdir(path):
                entries = sorted(os.listdir(path))[:50]
                content = f"Directory listing of {path}:\n" + "\n".join(entries)
                self._emit({"type": "tool_result", "ok": True, "output": content})
                if self._env:
                    self._env.record_result(f"read:{path}", True, content[:200])
                return {"ok": True, "output": content}
            content = open(path, encoding='utf-8', errors='replace').read()[:3000]
            self._emit({"type": "tool_result", "ok": True, "output": content})
            if self._env:
                self._env.record_result(f"read:{path}", True, content[:200])
            return {"ok": True, "output": content}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if self._env:
                self._env.record_result(f"read:{path}", False, str(e))
            return {"ok": False, "output": str(e)}

    def handle_write_file(self, args: dict) -> dict:
        if self._mode in ("ask", "plan"):
            return {"ok": False, "output": f"BLOCKED: write_file is not available in {self._mode} mode."}
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return {"ok": False, "output": "Missing file path"}
        if not os.path.isabs(path):
            path = os.path.join(self._cwd, path)

        if os.path.exists(path):
            try:
                existing_size = os.path.getsize(path)
                new_size = len(content.encode('utf-8'))
                if existing_size > 200 and new_size < existing_size * 0.4:
                    return {
                        "ok": False,
                        "output": (
                            f"REJECTED: New content ({new_size} bytes) is much "
                            f"smaller than existing ({existing_size} bytes). "
                            f"Use read_file first, then write COMPLETE file."),
                    }
            except OSError:
                pass

        content_hash = hash(content)
        history = self._write_history.setdefault(path, [])
        if content_hash in history:
            self._dup_counts[path] = self._dup_counts.get(path, 0) + 1
            dup_count = self._dup_counts[path]
            if dup_count >= 3:
                self._dup_counts[path] = 0
                return {
                    "ok": False,
                    "output": (
                        f"STUCK IN LOOP: Same content written {dup_count + 1} times. "
                        f"Take a different approach or ask_user for help."),
                }
            return {
                "ok": False,
                "output": "DUPLICATE WRITE DETECTED. Read file, identify the issue, write a DIFFERENT fix.",
            }
        self._dup_counts.pop(path, None)
        history.append(content_hash)
        if len(history) > 10:
            history[:] = history[-10:]

        self._turn_writes.append(path)
        self._emit({"type": "tool", "name": "write_file", "desc": f"Write: {path}", "cmd": f"write {path}"})

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            size = len(content)

            from logic.agent.quality import check_write_quality
            warnings = check_write_quality(path, content)
            result_msg = f"Written {size} bytes to {path}"
            if warnings:
                result_msg += "\n\nQUALITY WARNINGS:\n" + "\n".join(f"- {w}" for w in warnings)
                self._quality_warnings[path] = warnings
            else:
                self._quality_warnings.pop(path, None)

            self._emit({"type": "tool_result", "ok": True, "output": result_msg})
            if self._env:
                self._env.record_result(f"write:{path}", True, f"{size} bytes")
                self._env.files_written.append(path)
            return {"ok": True, "output": result_msg}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if self._env:
                self._env.record_result(f"write:{path}", False, str(e))
            return {"ok": False, "output": str(e)}

    def handle_edit_file(self, args: dict) -> dict:
        if self._mode in ("ask", "plan"):
            return {"ok": False, "output": f"BLOCKED: edit_file is not available in {self._mode} mode."}
        path = args.get("path", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        if not path or not old_text:
            return {"ok": False, "output": "Missing path or old_text"}
        if not os.path.isabs(path):
            path = os.path.join(self._cwd, path)

        self._emit({"type": "tool", "name": "edit_file",
                     "desc": f"Edit: {os.path.basename(path)}", "cmd": f"edit {path}"})
        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            count = content.count(old_text)
            if count == 0:
                self._emit({"type": "tool_result", "ok": False, "output": "old_text not found"})
                return {"ok": False, "output": "old_text not found. Use read_file to see exact content."}
            if count > 1:
                return {"ok": False, "output": f"old_text found {count} times (ambiguous)."}

            new_content = content.replace(old_text, new_text, 1)
            ext = os.path.splitext(path)[1].lower()
            if ext == ".py":
                try:
                    compile(new_content, path, 'exec')
                except SyntaxError as e:
                    return {"ok": False,
                            "output": f"Edit would cause syntax error at line {e.lineno}: {e.msg}"}

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            diff_preview = f"-{old_text[:80]}\n+{new_text[:80]}"
            self._emit({"type": "tool_result", "ok": True, "output": f"Edited {os.path.basename(path)}"})
            if self._env:
                self._env.record_result(f"edit:{path}", True, diff_preview)
            return {"ok": True, "output": f"Edit applied to {path}"}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            return {"ok": False, "output": str(e)}

    def handle_search(self, args: dict) -> dict:
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        self._emit({"type": "tool", "name": "search", "desc": f"Search: {pattern}",
                     "cmd": f"search '{pattern}' {path}"})
        try:
            if shutil.which("rg"):
                cmd = ["rg", "--max-count", "10", "--no-heading", pattern, path]
            else:
                cmd = ["grep", "-rn",
                       "--include=*.py", "--include=*.js", "--include=*.html",
                       "--include=*.css", "--include=*.md", "--include=*.json",
                       "-m", "10", pattern, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15,
                                    cwd=self._cwd)
            output = result.stdout[:2000] or "(no matches)"
            self._emit({"type": "tool_result", "ok": True, "output": output})
            if self._env:
                self._env.record_result(f"search:{pattern}", True, output[:300])
            return {"ok": True, "output": output}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            return {"ok": False, "output": str(e)}

    def handle_ask_user(self, args: dict) -> dict:
        question = args.get("question", "")
        self._emit({"type": "ask_user", "question": question})
        return {"ok": True, "output": f"[Question sent to user: {question}]"}

    def handle_todo(self, args: dict) -> dict:
        action = args.get("action", "init")
        items = args.get("items", [])
        if action == "init":
            self._emit({"type": "todo", "items": items})
        elif action == "update":
            for item in items:
                self._emit({"type": "todo_update", "id": item.get("id"),
                             "status": item.get("status")})
        elif action == "delete":
            for item in items:
                self._emit({"type": "todo_delete", "id": item.get("id")})
        return {"ok": True}
