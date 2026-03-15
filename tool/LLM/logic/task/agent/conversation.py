"""GUI-agnostic conversation manager for LLM agent sessions.

Provides a stateful middle layer between any GUI (HTML, tkinter, CLI)
and the LLM provider. All GUIs call the same methods; events are
emitted via a callback for rendering.

Supports system context feeds that package runtime state alongside
user messages, providing the agent with short-term memory. As tools
are discovered and lessons learned, the context feed evolves.

Usage:
    from tool.LLM.logic.task.agent.conversation import ConversationManager

    mgr = ConversationManager(provider_name="zhipu-glm-4.7")
    mgr.on_event(lambda evt: push_to_gui(evt))

    mgr.new_session("s1")
    mgr.send_message("s1", "Explain SSE in 3 sentences")
    # Events emitted: user → thinking → text → complete

    # With system context feed:
    mgr.send_message("s1", "Fix the BILIBILI bug",
                     context_feed={"hint": "BILIBILI search returns empty results"})
"""
import threading
import time
import uuid
import platform
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))

from tool.LLM.logic.session_context import SessionContext


@dataclass
class AgentEnvironment:
    """Tracks what the agent has discovered — short-term memory.

    Mirrors OPENCLAW's AgentEnvironment. As the agent explores (exec,
    search, read), observations accumulate here and get serialized
    into the next turn's context.
    """
    visible_tools: Dict[str, str] = field(default_factory=dict)
    visible_skills: Dict[str, str] = field(default_factory=dict)
    last_results: List[Dict[str, Any]] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def observe_tool(self, name: str, desc: str):
        self.visible_tools[name] = desc

    def record_result(self, cmd: str, ok: bool, preview: str = ""):
        self.last_results.append({
            "cmd": cmd, "ok": ok, "preview": preview[:300],
        })
        if len(self.last_results) > 5:
            self.last_results = self.last_results[-5:]

    def record_error(self, msg: str):
        self.errors.append(msg)
        if len(self.errors) > 3:
            self.errors = self.errors[-3:]

    def record_lesson(self, lesson: str):
        self.lessons.append(lesson)
        if len(self.lessons) > 5:
            self.lessons = self.lessons[-5:]

    def serialize(self) -> str:
        """Serialize into a context block for the next turn.

        Generates three types of awareness:
        1. State awareness: what tools/results are known
        2. Action awareness: what succeeded/failed recently
        3. Next-step hints: what the agent should consider doing next
        """
        parts = []
        if self.visible_tools:
            lines = ["[Discovered tools]"]
            for name, desc in self.visible_tools.items():
                lines.append(f"  {name}: {desc}")
            parts.append("\n".join(lines))
        if self.last_results:
            lines = ["[Recent command results]"]
            for r in self.last_results:
                status = "OK" if r["ok"] else "FAILED"
                lines.append(f"  [{status}] {r['cmd']}")
                if r["preview"]:
                    lines.append(f"    {r['preview'][:150]}")
            parts.append("\n".join(lines))

            awareness = self._generate_awareness()
            if awareness:
                parts.append(awareness)

        if self.errors:
            parts.append("[Errors to address]\n" + "\n".join(f"  - {e}" for e in self.errors))
        if self.lessons:
            parts.append("[Lessons learned]\n" + "\n".join(f"  - {l}" for l in self.lessons))
        return "\n\n".join(parts)

    def _generate_awareness(self) -> str:
        """Generate awareness cues based on current state."""
        cues = []
        if not self.last_results:
            return ""

        last = self.last_results[-1]

        failed_count = sum(1 for r in self.last_results if not r["ok"])
        if failed_count >= 3:
            cues.append(
                "WARNING: Multiple consecutive failures detected. "
                "Stop repeating the same approach. Try a completely different strategy: "
                "use a different tool, try a simpler command (ls, cat), or ask the user for help.")

        if last["cmd"].startswith("TOOL --search"):
            cues.append("Search completed. Execute the found command to get real data.")

        if not last["ok"]:
            cues.append(f"Last command failed. Consider: check tool docs or source code.")
            if self.errors:
                cues.append("Active errors exist. Fix them before proceeding.")

        if last["cmd"].startswith("read:") or last["cmd"].startswith("cat "):
            cues.append("File read completed. Use the information to proceed with the task.")

        has_search = any("--search" in r["cmd"] for r in self.last_results)
        has_exec = any(
            not r["cmd"].startswith("TOOL --search") and
            not r["cmd"].startswith("read:") and
            not r["cmd"].startswith("cat ") and
            not r["cmd"].startswith("search:")
            for r in self.last_results
        )
        if has_search and has_exec and last["ok"]:
            cues.append("Tool execution succeeded. Present results to the user.")

        if not cues:
            return ""
        return "[Next-step awareness]\n" + "\n".join(f"  - {c}" for c in cues)


_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))


def build_runtime_state() -> str:
    """Build a runtime state header with process/system info."""
    import datetime
    lines = [
        "---",
        f"timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"platform: {platform.system()} {platform.release()}",
        f"project_root: {_PROJECT_ROOT}",
        "---",
    ]
    return "\n".join(lines)


@dataclass
class Session:
    id: str
    title: str = "New Task"
    status: str = "idle"
    context: SessionContext = field(default_factory=SessionContext)
    environment: AgentEnvironment = field(default_factory=AgentEnvironment)
    created_at: float = field(default_factory=time.time)
    message_count: int = 0
    codebase_root: Optional[str] = None


BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Execute a shell command and return output. Use this to run CLI tools like BILIBILI, TOOL, GOOGLE, etc. Example: BILIBILI trending --limit 10",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command, e.g. 'BILIBILI boot', 'BILIBILI trending --limit 10', 'TOOL --list'"},
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
            "name": "todo",
            "description": "Manage a TODO list: init, update, or delete items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["init", "update", "delete"], "description": "Action: init (create list), update (change status), delete (remove item)"},
                    "items": {"type": "array", "items": {"type": "object"}, "description": "For init: [{id, text, status}]. For update: [{id, status}]. For delete: [{id}]."},
                },
                "required": ["action"],
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
                    "pattern": {"type": "string", "description": "Search pattern (regex or glob)"},
                    "path": {"type": "string", "description": "Directory to search in (default: project root)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content. Use for creating HTML, CSS, JS, Python, or any text files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write (absolute or relative to project root)"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific text in a file. Use this to modify existing files without rewriting the whole file. First read_file to see current content, then use edit_file to make targeted changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_text": {"type": "string", "description": "Exact text to find and replace (must exist in the file)"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a question and wait for their response. Use when you need clarification, approval, or feedback before proceeding.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask the user"},
                },
                "required": ["question"],
            },
        },
    },
]


class ConversationManager:
    """Stateful conversation orchestrator.

    All GUI variants (HTML, CLI, tkinter) use this same interface.
    Events are dispatched via ``on_event`` callback in the protocol
    format expected by ``AgentGUIEngine``.
    """

    def __init__(self, provider_name: str = "zhipu-glm-4.7",
                 system_prompt: str = "",
                 enable_tools: bool = False,
                 sandbox_policy: str = "ask",
                 default_codebase: Optional[str] = None,
                 brain=None):
        self._provider_name = provider_name
        self._system_prompt = system_prompt
        self._enable_tools = enable_tools
        self._sandbox_policy = sandbox_policy
        self._default_codebase = default_codebase
        self._tool_handlers: Dict[str, Callable] = {}
        self._sessions: Dict[str, Session] = {}
        self._active_session_id: Optional[str] = None
        self._current_turn_session_id: Optional[str] = None
        self._event_cb: Optional[Callable] = None
        self._lock = threading.Lock()

        if brain is not None:
            self._brain = brain
        else:
            from tool.LLM.logic.brain import Brain
            self._brain = Brain()

        if enable_tools:
            self._register_default_tool_handlers()

    @property
    def brain(self):
        return self._brain

    def on_event(self, cb: Callable):
        """Register event callback: ``cb(event_dict)``."""
        self._event_cb = cb

    def register_tool_def(self, tool_def: dict):
        """Register an additional tool definition (OpenAI function-calling format).

        The handler must also be registered via ``register_tool(name, handler)``.
        """
        if not hasattr(self, '_extra_tools'):
            self._extra_tools: list = []
        self._extra_tools.append(tool_def)

    def _emit(self, evt: dict):
        if self._event_cb:
            self._event_cb(evt)

    def _get_current_environment(self) -> Optional[AgentEnvironment]:
        """Return the AgentEnvironment for the session currently being processed."""
        sid = self._current_turn_session_id
        if sid and sid in self._sessions:
            return self._sessions[sid].environment
        return None

    def _package_message(self, session: Session, text: str,
                         context_feed: Optional[Dict[str, Any]] = None) -> str:
        """Package user text with system state for the LLM.

        Combines: runtime state + agent environment + context_feed + user text.
        """
        parts = []

        cwd = self._get_cwd()
        if session.message_count == 1:
            parts.append(build_runtime_state())
            parts.append(f"[Working directory] {cwd}\nAll relative paths resolve against this directory. Use relative paths.")
            try:
                files = os.listdir(cwd)
                if files:
                    listing = ", ".join(sorted(files)[:30])
                    parts.append(f"[Files in directory] {listing}")
                else:
                    parts.append("[Files in directory] (empty directory)")
            except OSError:
                pass
        else:
            try:
                files = [f for f in os.listdir(cwd)
                         if not f.startswith('.')]
                if files:
                    listing = ", ".join(sorted(files)[:20])
                    parts.append(
                        f"[IMPORTANT] Before modifying any file, you MUST "
                        f"read_file first to see current content. Files in "
                        f"directory: {listing}")
            except OSError:
                pass

        env_block = session.environment.serialize()
        if env_block:
            parts.append(env_block)

        if context_feed:
            feed_parts = []
            if context_feed.get("hint"):
                feed_parts.append(f"[System hint] {context_feed['hint']}")
            if context_feed.get("errors"):
                feed_parts.append("[Known errors]\n" +
                                  "\n".join(f"  - {e}" for e in context_feed["errors"]))
            if context_feed.get("tools_available"):
                lines = ["[Available tools]"]
                for name, desc in context_feed["tools_available"].items():
                    lines.append(f"  {name}: {desc}")
                feed_parts.append("\n".join(lines))
            if context_feed.get("lesson"):
                feed_parts.append(f"[Lesson] {context_feed['lesson']}")
            if feed_parts:
                parts.append("\n".join(feed_parts))

        parts.append(text)
        return "\n\n".join(parts)

    # ── Tool Registration ──

    def register_tool(self, name: str, handler: Callable):
        """Register a custom tool handler: ``handler(args_dict) -> dict``."""
        self._tool_handlers[name] = handler

    def _register_default_tool_handlers(self):
        self._tool_handlers["exec"] = self._handle_exec
        self._tool_handlers["read_file"] = self._handle_read_file
        self._tool_handlers["todo"] = self._handle_todo
        self._tool_handlers["search"] = self._handle_search
        self._tool_handlers["write_file"] = self._handle_write_file
        self._tool_handlers["edit_file"] = self._handle_edit_file
        self._tool_handlers["ask_user"] = self._handle_ask_user

    def _get_cwd(self) -> str:
        """Return working directory: session codebase or project root."""
        sid = self._current_turn_session_id
        if sid and sid in self._sessions:
            codebase = self._sessions[sid].codebase_root
            if codebase and os.path.isdir(codebase):
                return codebase
        return _PROJECT_ROOT

    def _handle_exec(self, args: dict) -> dict:
        import subprocess
        cmd = args.get("command", "")
        cwd = self._get_cwd()
        project_root = _PROJECT_ROOT
        self._emit({"type": "tool", "name": "exec", "desc": cmd, "cmd": cmd})

        env = os.environ.copy()
        extra_paths = []
        bin_dir = os.path.join(project_root, "bin")
        if os.path.isdir(bin_dir):
            extra_paths.extend(
                os.path.join(bin_dir, d) for d in os.listdir(bin_dir)
                if os.path.isdir(os.path.join(bin_dir, d)))
        homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
        extra_paths.extend(p for p in homebrew_paths if os.path.isdir(p))
        if extra_paths:
            env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")

        env_obj = self._get_current_environment()
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60,
                cwd=cwd, env=env,
            )
            output = result.stdout + result.stderr
            ok = result.returncode == 0
            self._emit({"type": "tool_result", "ok": ok, "output": output[:3000]})
            if env_obj:
                env_obj.record_result(cmd, ok, output[:300])
                if not ok:
                    env_obj.record_error(f"Command failed: {cmd}")
            self._brain.learn_from_result(cmd, ok, output[:500])
            return {"ok": ok, "output": output[:3000]}
        except subprocess.TimeoutExpired:
            self._emit({"type": "tool_result", "ok": False, "output": "Command timed out (60s)"})
            if env_obj:
                env_obj.record_result(cmd, False, "Timeout")
                env_obj.record_error(f"Timeout: {cmd}")
            self._brain.learn_from_result(cmd, False, "Timeout")
            return {"ok": False, "output": "Timeout"}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if env_obj:
                env_obj.record_result(cmd, False, str(e))
                env_obj.record_error(str(e))
            self._brain.learn_from_result(cmd, False, str(e))
            return {"ok": False, "output": str(e)}

    def _handle_read_file(self, args: dict) -> dict:
        path = args.get("path", "")
        if not os.path.isabs(path):
            path = os.path.join(self._get_cwd(), path)
        if hasattr(self, '_turn_reads'):
            self._turn_reads.append(path)
        self._emit({"type": "tool", "name": "read", "desc": path, "cmd": path})
        env_obj = self._get_current_environment()
        try:
            if os.path.isdir(path):
                entries = sorted(os.listdir(path))[:50]
                content = f"Directory listing of {path}:\n" + "\n".join(entries)
            else:
                content = open(path, encoding='utf-8', errors='replace').read()[:3000]
            self._emit({"type": "tool_result", "ok": True, "output": content})
            if env_obj:
                env_obj.record_result(f"read:{path}", True, content[:200])
            return {"ok": True, "output": content}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if env_obj:
                env_obj.record_result(f"read:{path}", False, str(e))
            return {"ok": False, "output": str(e)}

    def _handle_todo(self, args: dict) -> dict:
        action = args.get("action", "init")
        items = args.get("items", [])
        if action == "init":
            self._emit({"type": "todo", "items": items})
        elif action == "update":
            for item in items:
                self._emit({"type": "todo_update", "id": item.get("id"), "status": item.get("status")})
        elif action == "delete":
            for item in items:
                self._emit({"type": "todo_delete", "id": item.get("id")})
        return {"ok": True}

    def _handle_search(self, args: dict) -> dict:
        import subprocess, shutil
        pattern = args.get("pattern", "")
        path = args.get("path", ".")
        cwd = self._get_cwd()
        self._emit({"type": "tool", "name": "search", "desc": f"Search: {pattern}", "cmd": f"search '{pattern}' {path}"})
        env_obj = self._get_current_environment()
        try:
            if shutil.which("rg"):
                cmd = ["rg", "--max-count", "10", "--no-heading", pattern, path]
            else:
                cmd = ["grep", "-rn", "--include=*.py", "--include=*.js",
                       "--include=*.html", "--include=*.css", "--include=*.md",
                       "--include=*.json", "--include=*.txt", "--include=*.yaml",
                       "-m", "10", pattern, path]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15, cwd=cwd,
            )
            output = result.stdout[:2000] or "(no matches)"
            self._emit({"type": "tool_result", "ok": True, "output": output})
            if env_obj:
                env_obj.record_result(f"search:{pattern}", True, output[:300])
            return {"ok": True, "output": output}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if env_obj:
                env_obj.record_result(f"search:{pattern}", False, str(e))
            return {"ok": False, "output": str(e)}

    def _handle_write_file(self, args: dict) -> dict:
        path = args.get("path", "")
        content = args.get("content", "")
        if not path:
            return {"ok": False, "output": "Missing file path"}

        if not os.path.isabs(path):
            path = os.path.join(self._get_cwd(), path)

        if os.path.exists(path):
            try:
                existing_size = os.path.getsize(path)
                new_size = len(content.encode('utf-8'))
                if existing_size > 200 and new_size < existing_size * 0.4:
                    return {
                        "ok": False,
                        "output": (
                            f"REJECTED: New content ({new_size} bytes) is much "
                            f"smaller than existing file ({existing_size} bytes). "
                            f"You are probably writing a FRAGMENT instead of the "
                            f"complete file. Use read_file to get the full current "
                            f"content, then write the COMPLETE file with your "
                            f"changes merged in."),
                    }
            except OSError:
                pass

        content_hash = hash(content)
        if not hasattr(self, '_write_history'):
            self._write_history: Dict[str, list] = {}
        if not hasattr(self, '_dup_counts'):
            self._dup_counts: Dict[str, int] = {}
        history = self._write_history.setdefault(path, [])
        if content_hash in history:
            self._dup_counts[path] = self._dup_counts.get(path, 0) + 1
            dup_count = self._dup_counts[path]
            if dup_count >= 3:
                self._dup_counts[path] = 0
                return {
                    "ok": False,
                    "output": (
                        f"STUCK IN LOOP: You have written the same content to "
                        f"{os.path.basename(path)} {dup_count + 1} times. STOP. "
                        f"Take a completely different approach: "
                        f"1) Use read_file to see the CURRENT file content. "
                        f"2) Think about what is actually wrong. "
                        f"3) Write a DIFFERENT fix. "
                        f"If you cannot fix it, use ask_user to request help."),
                }
            return {
                "ok": False,
                "output": (
                    f"DUPLICATE WRITE DETECTED: You already wrote identical "
                    f"content to {path}. Read the file back, identify what's "
                    f"wrong, and write a DIFFERENT fix."),
            }
        self._dup_counts.pop(path, None)
        history.append(content_hash)
        if len(history) > 10:
            history[:] = history[-10:]

        if not hasattr(self, '_turn_writes'):
            self._turn_writes: List[str] = []
        self._turn_writes.append(path)

        self._emit({"type": "tool", "name": "write_file", "desc": f"Write: {path}", "cmd": f"write {path}"})
        env_obj = self._get_current_environment()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            size = len(content)

            warnings = self._check_write_quality(path, content)
            result_msg = f"Written {size} bytes to {path}"
            if warnings:
                result_msg += "\n\nQUALITY WARNINGS (fix these now):\n" + "\n".join(
                    f"- {w}" for w in warnings)
                if hasattr(self, '_quality_warnings'):
                    self._quality_warnings[path] = warnings
            else:
                if hasattr(self, '_quality_warnings'):
                    self._quality_warnings.pop(path, None)

            self._emit({"type": "tool_result", "ok": True, "output": result_msg})
            if env_obj:
                env_obj.record_result(f"write:{path}", True, f"{size} bytes")
            return {"ok": True, "output": result_msg}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if env_obj:
                env_obj.record_result(f"write:{path}", False, str(e))
            return {"ok": False, "output": str(e)}

    @staticmethod
    def _check_write_quality(path: str, content: str) -> List[str]:
        """Run automated quality checks on written files."""
        warnings = []
        ext = os.path.splitext(path)[1].lower()

        if ext == ".py":
            try:
                compile(content, path, 'exec')
            except SyntaxError as e:
                warnings.append(
                    f"SYNTAX ERROR at line {e.lineno}: {e.msg}. "
                    f"Common fix: use single quotes inside f-strings "
                    f"(e.g., f\"{{bm['title']}}\" not f\"{{bm[\"title\"]}}\"). "
                    f"Rewrite the file with correct syntax.")

        if ext == ".html":
            placeholders = ["Short bio", ">Name<", ">Role<",
                            "placeholder text", "Lorem ipsum",
                            ">Description<", ">Title<"]
            found = [p for p in placeholders
                     if p.lower() in content.lower()]
            if found:
                warnings.append(
                    f"Contains placeholder text: {', '.join(found)}. "
                    f"Replace with realistic content (real names, specific descriptions).")

            import re as _re
            has_placeholder_img = _re.search(
                r'src=["\'][^"\']*placeholder[^"\']*["\']', content, _re.IGNORECASE)
            if has_placeholder_img:
                warnings.append(
                    "References nonexistent placeholder image file. "
                    "Remove the <img> tag and use a <div> with the person's "
                    "initials styled as a circle (width/height: 80px, "
                    "border-radius: 50%, background: gradient).")

            if "fonts.googleapis" not in content and "fonts.google" not in content:
                warnings.append(
                    "No Google Fonts import. Add: "
                    '<link href="https://fonts.googleapis.com/css2?'
                    'family=Inter:wght@400;600;700&display=swap" rel="stylesheet">')

        elif ext == ".css":
            import re
            colors = re.findall(r'#[0-9a-fA-F]{3,6}', content)
            generic = {"#333", "#333333", "#666", "#666666", "#999",
                       "#fff", "#ffffff", "#f4f4f4", "#f5f5f5", "#f4f4f9",
                       "#eee", "#eeeeee", "#ddd", "#ccc", "#000", "#000000"}
            unique_colors = set(c.lower() for c in colors) - generic
            if len(unique_colors) == 0 and colors:
                warnings.append(
                    "All colors are generic greys/whites (#333, #fff, etc). "
                    "REWRITE this file with a real color palette. Example: "
                    "background: #0f0f23, card bg: #1a1a3e, accent: #16c79a, "
                    "text: #e0e0e0. You MUST rewrite this CSS file now.")

            if "transition" not in content:
                warnings.append(
                    "No CSS transitions found. Add transition properties "
                    "for smooth hover effects.")

            if "padding" not in content:
                warnings.append(
                    "No padding found. Cards/sections need inner padding "
                    "for readability.")

        return warnings

    def _handle_edit_file(self, args: dict) -> dict:
        path = args.get("path", "")
        old_text = args.get("old_text", "")
        new_text = args.get("new_text", "")
        if not path or not old_text:
            return {"ok": False, "output": "Missing path or old_text"}

        if not os.path.isabs(path):
            path = os.path.join(self._get_cwd(), path)

        self._emit({"type": "tool", "name": "edit_file",
                     "desc": f"Edit: {os.path.basename(path)}", "cmd": f"edit {path}"})
        env_obj = self._get_current_environment()
        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            count = content.count(old_text)
            if count == 0:
                self._emit({"type": "tool_result", "ok": False,
                             "output": "old_text not found in file"})
                if env_obj:
                    env_obj.record_result(f"edit:{path}", False, "not found")
                return {"ok": False,
                        "output": "old_text not found in file. Use read_file to "
                                  "see the exact current content."}
            if count > 1:
                self._emit({"type": "tool_result", "ok": False,
                             "output": f"old_text found {count} times (ambiguous)"})
                return {"ok": False,
                        "output": f"old_text found {count} times. Provide more "
                                  f"context to make it unique."}

            new_content = content.replace(old_text, new_text, 1)

            ext = os.path.splitext(path)[1].lower()
            if ext == ".py":
                try:
                    compile(new_content, path, 'exec')
                except SyntaxError as e:
                    self._emit({"type": "tool_result", "ok": False,
                                 "output": f"Edit would cause syntax error: {e}"})
                    return {"ok": False,
                            "output": f"Edit rejected — would cause syntax error "
                                      f"at line {e.lineno}: {e.msg}. Fix and retry."}

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            diff_preview = f"-{old_text[:80]}\n+{new_text[:80]}"
            self._emit({"type": "tool_result", "ok": True,
                         "output": f"Edited {os.path.basename(path)}\n{diff_preview}"})
            if env_obj:
                env_obj.record_result(f"edit:{path}", True, diff_preview)
            return {"ok": True, "output": f"Edit applied to {path}"}
        except Exception as e:
            self._emit({"type": "tool_result", "ok": False, "output": str(e)})
            if env_obj:
                env_obj.record_result(f"edit:{path}", False, str(e))
            return {"ok": False, "output": str(e)}

    def _handle_ask_user(self, args: dict) -> dict:
        question = args.get("question", "")
        self._emit({"type": "ask_user", "question": question})
        return {"ok": True, "output": f"[Question sent to user: {question}] The user will respond in a follow-up message. For now, continue with your best judgment or wait."}

    @staticmethod
    def _parse_text_tool_calls(text: str):
        """Parse tool calls embedded in text (e.g. <tool_call>func(args)</tool_call>).

        Some models output tool calls as text instead of structured API calls.
        Returns (cleaned_text, tool_calls_list).
        """
        import re, json as _json, uuid as _uuid

        patterns = [
            re.compile(
                r'<tool_call>\s*(\w+)\s*\(\s*(.*?)\s*\)\s*</tool_call>',
                re.DOTALL),
            re.compile(
                r'<tool_call>\s*(\w+)\s*\(\s*(.*?)\s*\)\s*$',
                re.DOTALL),
        ]

        tool_calls = []
        cleaned = text

        for pattern in patterns:
            for match in pattern.finditer(text):
                func_name = match.group(1)
                args_raw = match.group(2)
                args_dict = {}
                try:
                    args_dict = _json.loads("{" + args_raw + "}")
                except Exception:
                    kv_pattern = re.compile(
                        r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
                        re.DOTALL)
                    for kv in kv_pattern.finditer(args_raw):
                        key = kv.group(1)
                        val = kv.group(2)
                        try:
                            import ast
                            args_dict[key] = ast.literal_eval(val)
                        except Exception:
                            args_dict[key] = val.strip('"').strip("'")

                if func_name and args_dict:
                    tool_calls.append({
                        "id": f"text_tc_{_uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": _json.dumps(args_dict),
                        },
                    })
                    cleaned = cleaned.replace(match.group(0), "")

        return cleaned.strip(), tool_calls

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """Execute a single tool call from the LLM."""
        import json as _json
        func = tool_call.get("function", {})
        name = func.get("name", "")
        try:
            args = _json.loads(func.get("arguments", "{}"))
        except Exception:
            args = {}

        handler = self._tool_handlers.get(name)
        if handler:
            return handler(args)
        self._emit({"type": "text", "tokens": f"Unknown tool: {name}"})
        return {"ok": False, "output": f"Unknown tool: {name}"}

    # ── Session Management ──

    def new_session(self, session_id: str = None, title: str = "New Task",
                    codebase_root: Optional[str] = None) -> str:
        sid = session_id or str(uuid.uuid4())[:8]
        codebase = codebase_root or self._default_codebase

        prompt = self._system_prompt
        bootstrap = self._brain.get_session_bootstrap(sid, codebase)
        if bootstrap:
            prompt = prompt + "\n\n" + bootstrap

        ctx = SessionContext(system_prompt=prompt)
        with self._lock:
            self._sessions[sid] = Session(
                id=sid, title=title, context=ctx, codebase_root=codebase)
            if self._active_session_id is None:
                self._active_session_id = sid
        self._emit({"type": "session_created", "id": sid, "title": title,
                     "codebase_root": codebase})
        return sid

    def rename_session(self, session_id: str, new_title: str):
        with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.title = new_title
        self._emit({"type": "session_renamed", "id": session_id, "title": new_title})

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            if self._active_session_id == session_id:
                remaining = list(self._sessions.keys())
                self._active_session_id = remaining[-1] if remaining else None
        self._emit({"type": "session_deleted", "id": session_id})

    def set_active(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._active_session_id = session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"id": s.id, "title": s.title, "status": s.status,
             "message_count": s.message_count, "created_at": s.created_at}
            for s in self._sessions.values()
        ]

    # ── Conversation ──

    def send_message(self, session_id: str, text: str,
                     blocking: bool = False,
                     context_feed: Optional[Dict[str, Any]] = None,
                     break_after_first_reply: bool = False):
        """Send a user message and get LLM response.

        Parameters
        ----------
        session_id : str
        text : str
            The user's message.
        blocking : bool
            If True, blocks until the turn completes.
        context_feed : dict, optional
            Additional system state to package with the message.
            Keys: ``hint`` (str), ``errors`` (list[str]),
            ``tools_available`` (dict), ``lesson`` (str).
        break_after_first_reply : bool
            If True, stop after first agent reply (no Round 2).
        """
        if blocking:
            self._run_turn(session_id, text, context_feed, break_after_first_reply)
        else:
            t = threading.Thread(target=self._run_turn,
                                 args=(session_id, text, context_feed, break_after_first_reply),
                                 daemon=True)
            t.start()

    def _run_turn(self, session_id: str, text: str,
                  context_feed: Optional[Dict[str, Any]] = None,
                  break_after_first_reply: bool = False):
        session = self._sessions.get(session_id)
        if not session:
            self._emit({"type": "error", "message": f"Session {session_id} not found"})
            return

        session.status = "running"
        session.message_count += 1
        self._current_turn_session_id = session_id
        self._turn_writes = []
        self._turn_reads: List[str] = []
        self._quality_warnings: Dict[str, List[str]] = {}
        self._emit({"type": "session_status", "id": session_id, "status": "running"})

        # Build user event with prompt + ecosystem context + system state
        ecosystem = {}
        system_state = {"nudge_triggered": False}
        try:
            from logic.agent.ecosystem import build_ecosystem_info, build_system_state
            _proj = getattr(self, "_project_root", None) or _PROJECT_ROOT
            ecosystem = build_ecosystem_info(str(_proj))
            system_state = build_system_state(
                session_env=session.environment,
                nudge_triggered=False,
                quality_warnings=self._quality_warnings,
                last_tool_results=session.environment.last_results if session.environment else None,
            )
        except Exception:
            pass
        user_evt = {
            "type": "user",
            "prompt": text,
            "ecosystem": ecosystem,
            "user_rationale": ecosystem.get("user_rationale", ""),
            "system_state": system_state,
        }
        self._emit(user_evt)

        if session.context.needs_compression(trigger_ratio=0.6):
            self._compress_context(session)

        packaged = self._package_message(session, text, context_feed)
        session.context.add_user(packaged)

        auto_title = session.message_count == 1 and session.title == "New Task"

        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)

            if not provider.is_available():
                self._emit({"type": "text", "tokens": f"Error: Provider {self._provider_name} is not available."})
                self._emit({"type": "complete"})
                session.status = "idle"
                self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                return

            tools = None
            if self._enable_tools and provider.capabilities.supports_tool_calling:
                tools = list(BUILTIN_TOOLS)
                if hasattr(self, '_extra_tools'):
                    tools.extend(self._extra_tools)
            from tool.LLM.logic.registry import get_pipeline
            pipeline = get_pipeline(self._provider_name)

            max_tool_rounds = 15
            round_num = 0
            empty_retries = 0
            max_empty_retries = pipeline.get_max_retries()
            consecutive_empty = 0
            MAX_CONSECUTIVE_EMPTY = 3

            default_max_tokens = min(
                getattr(provider.capabilities, 'max_output_tokens', 4096) or 4096,
                8192)
            current_max_tokens = default_max_tokens

            while round_num < max_tool_rounds:
                round_num += 1
                full_text = ""
                tool_calls_accum = []

                self._emit({
                    "type": "llm_request",
                    "provider": self._provider_name,
                    "round": round_num,
                })

                use_streaming = empty_retries == 0

                first_chunk = True
                api_messages = pipeline.prepare_messages(
                    session.context.get_messages_for_api(),
                    turn_number=session.message_count,
                )
                api_tools = pipeline.prepare_tools(tools, provider.capabilities)

                if use_streaming:
                    for chunk in provider.stream(
                        api_messages,
                        temperature=0.7,
                        max_tokens=current_max_tokens,
                        tools=api_tools,
                    ):
                        if first_chunk and chunk.get("ok"):
                            first_chunk = False
                            self._emit({"type": "llm_response_start", "round": round_num})

                        if chunk.get("ok"):
                            t = chunk.get("text", "")
                            if t:
                                full_text += t
                            tc = chunk.get("tool_calls")
                            if tc:
                                tool_calls_accum.extend(tc)
                            if chunk.get("done"):
                                if chunk.get("tool_calls"):
                                    tool_calls_accum = chunk["tool_calls"]
                                latency = chunk.get("latency_s")
                                self._last_finish_reason = chunk.get("finish_reason", "")
                                self._last_usage = chunk.get("usage", {})
                                stream_end_evt = {
                                    "type": "llm_response_end",
                                    "round": round_num,
                                    "latency_s": latency,
                                    "has_tool_calls": bool(tool_calls_accum),
                                    "provider": self._provider_name,
                                    "model": chunk.get("model", self._provider_name),
                                }
                                if chunk.get("usage"):
                                    stream_end_evt["usage"] = chunk["usage"]
                                self._emit(stream_end_evt)
                                if break_after_first_reply and not tool_calls_accum and round_num >= 3:
                                    self._emit({"type": "text",
                                                "tokens": f"[Break after round {round_num} — stopping.]\n"})
                                    self._emit({"type": "complete"})
                                    session.status = "idle"
                                    self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                                    return
                                break
                        else:
                            err = chunk.get("error", "Unknown error")
                            self._emit({"type": "text", "tokens": f"Error: {err}"})
                            self._emit({"type": "complete"})
                            session.status = "idle"
                            self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                            return
                else:
                    self._emit({"type": "llm_response_start", "round": round_num})
                    import time as _time
                    t0 = _time.time()
                    result = provider.send(
                        api_messages,
                        temperature=0.7,
                        max_tokens=current_max_tokens,
                        tools=api_tools,
                    )
                    latency = _time.time() - t0
                    self._last_finish_reason = result.get("finish_reason", "")
                    self._last_usage = result.get("usage", {})
                    if result.get("ok"):
                        full_text = result.get("text", "") or ""
                        if result.get("tool_calls"):
                            tool_calls_accum = result["tool_calls"]
                    else:
                        err = result.get("error", "Unknown error")
                        self._emit({"type": "text", "tokens": f"Error: {err}"})
                        self._emit({"type": "complete"})
                        session.status = "idle"
                        self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                        return
                    resp_event = {
                        "type": "llm_response_end",
                        "round": round_num,
                        "latency_s": round(latency, 3),
                        "has_tool_calls": bool(tool_calls_accum),
                        "provider": self._provider_name,
                        "model": result.get("model", self._provider_name),
                    }
                    if result.get("usage"):
                        resp_event["usage"] = result["usage"]
                    self._emit(resp_event)

                if full_text and not tool_calls_accum and "<tool_call>" in full_text:
                    cleaned, parsed_tcs = self._parse_text_tool_calls(full_text)
                    if parsed_tcs:
                        self._emit({"type": "text",
                                    "tokens": f"[Parsed {len(parsed_tcs)} text-embedded tool call(s)]\n"})
                        tool_calls_accum.extend(parsed_tcs)
                        full_text = cleaned

                if full_text or tool_calls_accum:
                    consecutive_empty = 0
                if full_text:
                    self._emit({"type": "text", "tokens": full_text})

                if break_after_first_reply and not tool_calls_accum and round_num >= 3:
                    self._emit({"type": "text",
                                "tokens": f"[Break after round {round_num} — stopping.]\n"})
                    self._emit({"type": "complete"})
                    session.status = "idle"
                    self._emit({"type": "session_status", "id": session_id, "status": "idle"})
                    return

                if not full_text and not tool_calls_accum:
                    consecutive_empty += 1
                    if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                        self._emit({"type": "text",
                                    "tokens": f"[{consecutive_empty} consecutive empty responses — "
                                    "stopping to avoid wasting API calls.]\n"})
                        break

                    last_finish = getattr(self, '_last_finish_reason', "")
                    last_usage = getattr(self, '_last_usage', {})
                    validation = pipeline.validate_response(
                        full_text, tool_calls_accum, last_finish, last_usage)
                    if not validation.get("valid", True) and validation.get("retry"):
                        if validation.get("increase_max_tokens"):
                            new_max = pipeline.get_recommended_max_tokens(
                                current_max_tokens)
                            if new_max > current_max_tokens:
                                current_max_tokens = new_max
                                self._emit({"type": "text",
                                            "tokens": f"[Reasoning model budget exceeded, "
                                            f"retrying with max_tokens={current_max_tokens}...]\n"})
                            else:
                                self._emit({"type": "text",
                                            "tokens": "[Reasoning budget maxed out, retrying...]\n"})
                        else:
                            self._emit({"type": "text",
                                        "tokens": f"[{validation.get('reason', 'Retrying')}]\n"})
                        continue

                if not tool_calls_accum:
                    if full_text:
                        session.context.add_assistant(full_text)
                        if (tools and round_num <= 6
                                and self._should_nudge(full_text, round_num)):
                            has_read = any(
                                r.get("cmd", "").startswith("read:")
                                for r in session.environment.last_results)
                            if has_read:
                                nudge = (
                                    "You already read the file. Now use "
                                    "write_file to apply your fix. The content "
                                    "parameter must be the COMPLETE file with "
                                    "ALL imports, functions, and your changes "
                                    "merged in. Do NOT write just a fragment.")
                            else:
                                nudge = (
                                    "You described changes but didn't apply them. "
                                    "First read_file to get the current content, "
                                    "then use write_file with the COMPLETE file "
                                    "(all imports, all functions, everything) with "
                                    "your changes merged in.")
                            session.context.add_user(nudge)
                            self._emit({"type": "text",
                                         "tokens": "[Nudging agent...]\n"})
                            continue

                        unfixed = self._get_unfixed_quality_warnings()
                        if unfixed and round_num <= 12:
                            parts = []
                            for fpath, warns in list(unfixed.items())[:2]:
                                fname = os.path.basename(fpath)
                                parts.append(
                                    f"{fname}: " + "; ".join(warns[:2]))
                            fix_nudge = (
                                "UNRESOLVED QUALITY ISSUES — fix these before "
                                "finishing:\n" + "\n".join(parts))
                            session.context.add_user(fix_nudge)
                            self._emit({"type": "text",
                                         "tokens": "[Fixing quality issues...]\n"})
                            continue

                        if session.message_count >= 2:
                            unverified = self._get_unverified_writes()
                            if unverified and round_num <= 12:
                                verify_nudge = (
                                    f"You wrote {len(unverified)} file(s) but never "
                                    f"read them back to verify. Use read_file to "
                                    f"confirm ALL requested changes are present: "
                                    + ", ".join(os.path.basename(p) for p in unverified[:3]))
                                session.context.add_user(verify_nudge)
                                self._emit({"type": "text",
                                             "tokens": "[Verifying written files...]\n"})
                                continue
                    elif tools and empty_retries < max_empty_retries:
                        empty_retries += 1
                        session.context.add_assistant(
                            "I understand. Let me take action now.")
                        retry_prompt = (
                            "Your last response was empty. Use write_file "
                            "to create/update files, or exec to run commands. "
                            "Take action NOW — call a tool.")
                        session.context.add_user(retry_prompt)
                        self._emit({"type": "text",
                                     "tokens": "[Empty response, retrying...]\n"})
                        continue
                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": tool_calls_accum,
                }
                session.context.add_raw_message(assistant_msg)

                for tc in tool_calls_accum:
                    result = self._execute_tool_call(tc)
                    tool_id = tc.get("id", "")
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": result.get("output", ""),
                    }
                    session.context.add_raw_message(tool_msg)

            self._emit({"type": "complete"})

            if auto_title:
                self._generate_title_async(session_id, text, full_text)

        except Exception as e:
            self._emit({"type": "text", "tokens": f"Exception: {e}"})
            self._emit({"type": "complete"})

        session.status = "done"
        self._emit({"type": "session_status", "id": session_id, "status": "done"})

    def _generate_title_async(self, session_id: str, user_msg: str, assistant_msg: str):
        """Generate a short title for the conversation."""
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)
            result = provider.send([
                {"role": "system", "content": "Generate a concise title (5-8 words max) for this conversation. Output ONLY the title, nothing else."},
                {"role": "user", "content": f"User: {user_msg[:200]}\nAssistant: {assistant_msg[:200]}"},
            ], temperature=0.3, max_tokens=30)
            if result.get("ok"):
                title = result["text"].strip().strip('"').strip("'")
                if title and len(title) < 80:
                    self.rename_session(session_id, title)
        except Exception:
            pass

    def generate_title(self, session_id: str) -> Optional[str]:
        """Synchronously generate and set a title. Returns the title or None."""
        session = self._sessions.get(session_id)
        if not session or session.message_count == 0:
            return None
        msgs = session.context.messages
        user_msg = next((m["content"] for m in msgs if m["role"] == "user"), "")
        asst_msg = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
        if not user_msg:
            return None
        self._generate_title_async(session_id, user_msg, asst_msg)
        return self._sessions.get(session_id, Session(id="")).title

    # ── Verification ──

    def _get_unverified_writes(self) -> List[str]:
        """Return files that were written this turn but never read back."""
        writes = getattr(self, '_turn_writes', [])
        reads = set(getattr(self, '_turn_reads', []))
        return [w for w in writes if w not in reads]

    def _get_unfixed_quality_warnings(self) -> Dict[str, List[str]]:
        """Return quality warnings that haven't been resolved by a rewrite."""
        return dict(getattr(self, '_quality_warnings', {}))

    # ── Nudge Detection ──

    @staticmethod
    def _should_nudge(text: str, round_num: int = 0) -> bool:
        """Detect if the agent described code changes without applying them.

        Returns True if the text looks like a description of code changes
        (contains code blocks, file references, or change verbs) rather
        than a final answer to a question.
        """
        text_lower = text.lower()

        if round_num <= 2 and len(text) < 200:
            return True

        code_indicators = ["```", "def ", "class ", "import ",
                           "<html", "function ", "const "]
        has_code = any(ind in text_lower for ind in code_indicators)

        action_indicators = [
            "here's the updated", "here is the", "i would",
            "you can add", "modify", "change the",
            "update the", "replace", "add the following",
            "here's how",
            "我将", "首先创建", "接下来", "然后创建",
            "开始创建", "第一步", "第二步", "下面",
            "创建以下", "编写", "修改",
        ]
        has_action_desc = any(ind in text_lower for ind in action_indicators)

        applied_indicators = [
            "i've created", "i've updated", "i've fixed",
            "i have created", "i have updated", "done.",
            "file has been", "successfully",
            "已创建", "已完成", "已修改", "已写入", "创建完毕",
        ]
        already_applied = any(ind in text_lower for ind in applied_indicators)

        return (has_code or has_action_desc) and not already_applied

    # ── Context Compression ──

    def _compress_context(self, session: Session):
        """Compress conversation context when it grows too large."""
        self._emit({"type": "text", "tokens": "[Compressing context...]\n"})
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(self._provider_name)
            prompt = session.context.build_compression_prompt(target_ratio=0.15)
            result = provider.send(
                session.context.get_messages_for_api() + [
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            if result.get("ok") and result.get("text"):
                summary = result["text"]
                session.context.apply_compression(summary)
                self._brain.on_session_end(session.id, summary)
                self._emit({"type": "text",
                             "tokens": "[Context compressed successfully]\n"})
        except Exception as e:
            self._emit({"type": "text",
                         "tokens": f"[Context compression failed: {e}]\n"})

    # ── State Export ──

    def get_state(self) -> Dict[str, Any]:
        """Export full state for persistence or debugging."""
        return {
            "provider": self._provider_name,
            "active_session": self._active_session_id,
            "sessions": {
                sid: {
                    "id": s.id, "title": s.title, "status": s.status,
                    "message_count": s.message_count,
                    "context": s.context.to_dict(),
                }
                for sid, s in self._sessions.items()
            },
        }
