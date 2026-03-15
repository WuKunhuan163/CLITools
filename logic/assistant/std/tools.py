"""Standard tool implementations.

Each tool function takes (args: dict, ctx: ToolContext) -> dict.
"""
import os
import subprocess
import shutil
import threading
import time
from typing import List

from logic.assistant.std.registry import register_tool, ToolContext

_DEFAULT_BLOCK_MS = 30000


def _get_limit(key: str, default: int) -> int:
    """Read a configurable limit from LLM config, with fallback."""
    try:
        from tool.LLM.logic.config import get_config_value
        val = get_config_value(key)
        if val is not None:
            return int(val)
    except Exception:
        pass
    return default


def _build_exec_env(project_root: str) -> dict:
    """Build env dict with bin/ and homebrew paths prepended."""
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
    return env


@register_tool("exec")
def handle_exec(args: dict, ctx: ToolContext) -> dict:
    cmd = args.get("command", "")
    block_ms = args.get("block_until_ms", _DEFAULT_BLOCK_MS)
    timeout_policy = args.get("timeout_policy", "ok")

    first_word = cmd.strip().split()[0] if cmd.strip() else "exec"
    exec_desc = f"Run {first_word}" if len(cmd) > 40 else cmd
    ctx.emit({"type": "tool", "name": "exec", "desc": exec_desc, "cmd": cmd})

    env = _build_exec_env(ctx.project_root)
    max_exec = _get_limit("max_exec_chars", 6000)

    if block_ms == 0:
        return _exec_background(cmd, env, ctx, max_exec, timeout_policy)

    block_s = block_ms / 1000.0

    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=ctx.cwd, env=env,
        )
        stdout_parts: List[str] = []
        stderr_parts: List[str] = []
        finished = threading.Event()

        def _reader():
            try:
                out, err = proc.communicate()
                stdout_parts.append(out or "")
                stderr_parts.append(err or "")
            except Exception:
                pass
            finally:
                finished.set()

        t = threading.Thread(target=_reader, daemon=True)
        t.start()

        if finished.wait(timeout=block_s):
            output = "".join(stdout_parts) + "".join(stderr_parts)
            ok = proc.returncode == 0
            ctx.emit({"type": "tool_result", "ok": ok, "output": output[:max_exec],
                       "pid": proc.pid, "elapsed_ms": int(block_s * 1000)})
            return {"ok": ok, "output": output[:max_exec],
                    "pid": proc.pid, "exit_code": proc.returncode}

        ok = timeout_policy == "ok"
        msg = (
            f"[Command still running after {block_ms}ms, moved to background. "
            f"pid={proc.pid}]"
        )
        ctx.emit({"type": "tool_result", "ok": ok, "output": msg,
                   "pid": proc.pid, "running": True})
        return {"ok": ok, "output": msg,
                "pid": proc.pid, "running": True}

    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


def _exec_background(cmd: str, env: dict, ctx: ToolContext,
                     max_exec: int, timeout_policy: str) -> dict:
    """Immediately background the command (block_until_ms=0)."""
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=ctx.cwd, env=env,
        )
        ok = timeout_policy == "ok"
        msg = f"[Started in background. pid={proc.pid}]"
        ctx.emit({"type": "tool_result", "ok": ok, "output": msg,
                   "pid": proc.pid, "running": True})
        return {"ok": ok, "output": msg, "pid": proc.pid, "running": True}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


@register_tool("read_file")
def handle_read_file(args: dict, ctx: ToolContext) -> dict:
    MAX_READ_CHARS = _get_limit("max_read_chars", 12000)
    path = args.get("path", "")
    start_line = args.get("start_line")
    end_line = args.get("end_line")
    if not os.path.isabs(path):
        path = os.path.join(ctx.cwd, path)
    ctx.turn_reads.append(path)
    basename = os.path.basename(path.rstrip("/"))
    read_desc = f"Read {basename}" if basename else "List directory"
    if start_line or end_line:
        read_desc += f" L{start_line or 1}-{end_line or 'end'}"
    ctx.emit({"type": "tool", "name": "read", "desc": read_desc, "cmd": path})
    try:
        if os.path.isdir(path):
            entries = sorted(os.listdir(path))[:50]
            content = f"Directory listing of {path}:\n" + "\n".join(entries)
        else:
            raw = open(path, encoding='utf-8', errors='replace').read()
            lines = raw.splitlines(keepends=True)
            total_lines = len(lines)
            if start_line or end_line:
                s = max(1, start_line or 1) - 1
                e = min(total_lines, end_line or total_lines)
                selected = lines[s:e]
                numbered = [f"{s+i+1:>4}| {line}" for i, line in enumerate(selected)]
                content = "".join(numbered)
                if len(content) > 15000:
                    content = content[:15000] + f"\n... (truncated, lines {s+1}-{e} of {total_lines})"
                else:
                    content += f"\n[Lines {s+1}-{e} of {total_lines} total]"
            else:
                content = raw[:MAX_READ_CHARS]
                if len(raw) > MAX_READ_CHARS:
                    content += (
                        f"\n\n... (truncated at {MAX_READ_CHARS} chars, total "
                        f"{len(raw)} chars, {total_lines} lines. Use "
                        f"start_line/end_line to read specific sections.)")
        ctx.emit({"type": "tool_result", "ok": True, "output": content})
        return {"ok": True, "output": content}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


@register_tool("search")
def handle_search(args: dict, ctx: ToolContext) -> dict:
    pattern = args.get("pattern", "")
    path = args.get("path", ".")
    search_desc = f'Search for "{pattern}"' + (f" in {os.path.basename(path)}" if path != "." else "")
    ctx.emit({"type": "tool", "name": "search", "desc": search_desc, "cmd": f"search '{pattern}' {path}"})
    try:
        if shutil.which("rg"):
            cmd = ["rg", "--max-count", "10", "--no-heading",
                   "--type-add", "src:*.py", "--type-add", "src:*.js",
                   "--type-add", "src:*.html", "--type-add", "src:*.css",
                   "--type-add", "src:*.md", "--type-add", "src:*.json",
                   "--type-add", "src:*.txt", "--type-add", "src:*.yaml",
                   "-t", "src", pattern, path]
        else:
            cmd = ["grep", "-rn", "--include=*.py", "--include=*.js",
                   "--include=*.html", "--include=*.css", "--include=*.md",
                   "--include=*.json", "--include=*.txt", "--include=*.yaml",
                   "-m", "10", pattern, path]
        result = subprocess.run(cmd, capture_output=True, timeout=15, cwd=ctx.cwd)
        output = result.stdout.decode("utf-8", errors="replace")[:2000] or "(no matches)"
        abs_path = os.path.join(ctx.cwd, path) if not os.path.isabs(path) else path
        if os.path.isfile(abs_path):
            prefix = path + ":"
            lines = output.split("\n")
            output = "\n".join(
                line[len(prefix):] if line.startswith(prefix) else line
                for line in lines
            )
        ctx.emit({"type": "tool_result", "ok": True, "output": output})
        return {"ok": True, "output": output}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


@register_tool("write_file")
def handle_write_file(args: dict, ctx: ToolContext) -> dict:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return {"ok": False, "output": "Missing file path"}

    if not os.path.isabs(path):
        path = os.path.join(ctx.cwd, path)

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
                        f"Use read_file to get the full current content, then "
                        f"write the COMPLETE file with your changes merged in."),
                }
        except OSError:
            pass

    content_hash = hash(content)
    history = ctx.write_history.setdefault(path, [])
    if content_hash in history:
        ctx.dup_counts[path] = ctx.dup_counts.get(path, 0) + 1
        dup_count = ctx.dup_counts[path]
        if dup_count >= 3:
            ctx.dup_counts[path] = 0
            return {
                "ok": False,
                "output": (
                    f"STUCK IN LOOP: You have written the same content to "
                    f"{os.path.basename(path)} {dup_count + 1} times. STOP. "
                    f"Take a completely different approach."),
            }
        return {
            "ok": False,
            "output": (
                f"DUPLICATE WRITE DETECTED: You already wrote identical "
                f"content to {path}. Read the file back and write a DIFFERENT fix."),
        }
    ctx.dup_counts.pop(path, None)
    history.append(content_hash)
    if len(history) > 10:
        history[:] = history[-10:]

    ctx.turn_writes.append(path)

    write_basename = os.path.basename(path)
    ctx.emit({"type": "tool", "name": "write_file", "desc": f"Edited {write_basename}", "file": path})
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        size = len(content)

        warnings = check_write_quality(path, content)
        base_msg = f"Written {size} bytes to {path}"
        warn_suffix = ""
        if warnings:
            warn_suffix = "\n\nQUALITY WARNINGS (fix these now):\n" + "\n".join(
                f"- {w}" for w in warnings)

        all_lines = content.split('\n')
        gui_limit = 2000
        if len(all_lines) > gui_limit + 10:
            gui_preview = '\n'.join(all_lines[:gui_limit]) + f'\n... ({len(all_lines) - gui_limit} more lines)'
        else:
            gui_preview = content
        ctx.emit({"type": "tool_result", "ok": True,
                  "output": base_msg + warn_suffix + "\n" + gui_preview})

        agent_limit = 50
        if len(all_lines) > agent_limit + 10:
            agent_preview = '\n'.join(all_lines[:agent_limit]) + f'\n... ({len(all_lines) - agent_limit} more lines)'
        else:
            agent_preview = content
        return {"ok": True, "output": base_msg + warn_suffix + "\n" + agent_preview}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


@register_tool("edit_file")
def handle_edit_file(args: dict, ctx: ToolContext) -> dict:
    path = args.get("path", "")
    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    if not path:
        return {"ok": False, "output": "Missing path"}
    if not old_text:
        return handle_write_file({"path": path, "content": new_text}, ctx)

    if not os.path.isabs(path):
        path = os.path.join(ctx.cwd, path)

    if old_text == new_text:
        ctx.emit({"type": "tool", "name": "edit_file",
                  "desc": f"Edit {os.path.basename(path)}", "cmd": f"edit {path}"})
        ctx.emit({"type": "tool_result", "ok": True, "output": "(no change)"})
        return {"ok": True, "output": "No change — old_text and new_text are identical."}

    ctx.emit({"type": "tool", "name": "edit_file",
              "desc": f"Edit {os.path.basename(path)}", "cmd": f"edit {path}"})
    try:
        content = open(path, encoding='utf-8', errors='replace').read()
        count = content.count(old_text)
        if count == 0:
            ctx.emit({"type": "tool_result", "ok": False,
                       "output": "old_text not found in file"})
            if ctx.env_obj:
                ctx.env_obj.record_result(f"edit:{path}", False, "not found")
            return {"ok": False,
                    "output": "old_text not found in file. Use read_file to "
                              "see the exact current content."}
        if count > 1:
            ctx.emit({"type": "tool_result", "ok": False,
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
                ctx.emit({"type": "tool_result", "ok": False,
                           "output": f"Edit would cause syntax error: {e}"})
                return {"ok": False,
                        "output": f"Edit rejected — syntax error "
                                  f"at line {e.lineno}: {e.msg}. Fix and retry."}

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        diff_lines = []
        for ol in old_lines[:10]:
            diff_lines.append(f"-{ol}")
        for nl in new_lines[:10]:
            diff_lines.append(f"+{nl}")
        diff_preview = "\n".join(diff_lines)
        ctx.emit({"type": "tool_result", "ok": True, "output": diff_preview})
        return {"ok": True, "output": f"Edit applied to {path}"}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        return {"ok": False, "output": str(e)}


@register_tool("todo")
def handle_todo(args: dict, ctx: ToolContext) -> dict:
    action = args.get("action", "init")
    items = args.get("items", [])
    if action == "init":
        ctx.emit({"type": "todo", "items": items})
    elif action == "update":
        for item in items:
            ctx.emit({"type": "todo_update", "id": item.get("id"), "status": item.get("status")})
    elif action == "delete":
        for item in items:
            ctx.emit({"type": "todo_delete", "id": item.get("id")})
    return {"ok": True}


@register_tool("ask_user")
def handle_ask_user(args: dict, ctx: ToolContext) -> dict:
    question = args.get("question", "")
    ctx.emit({"type": "ask_user", "question": question})
    return {"ok": True, "output": f"[Question sent to user: {question}] The user will respond in a follow-up message."}


@register_tool("experience")
def handle_experience(args: dict, ctx: ToolContext) -> dict:
    lesson = args.get("lesson", "")
    if not lesson:
        return {"ok": False, "error": "lesson is required"}
    try:
        from logic.search.knowledge import KnowledgeManager
        km = KnowledgeManager(ctx.project_root)
        km.add_lesson(
            lesson,
            tool=args.get("tool"),
            severity=args.get("severity", "info"),
            context=args.get("context", ""),
        )
    except Exception:
        import json as _json
        from datetime import datetime
        entry = {
            "timestamp": datetime.now().isoformat(),
            "lesson": lesson,
            "severity": args.get("severity", "info"),
        }
        if args.get("tool"):
            entry["tool"] = args["tool"]
        lessons_path = os.path.join(ctx.project_root, "runtime", "experience", "lessons.jsonl")
        os.makedirs(os.path.dirname(lessons_path), exist_ok=True)
        with open(lessons_path, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry, ensure_ascii=False) + "\n")
    ctx.emit({"type": "experience", "lesson": lesson, "severity": args.get("severity", "info")})
    return {"ok": True, "output": f"Lesson recorded: {lesson}"}


def check_write_quality(path: str, content: str) -> List[str]:
    """Run automated quality checks on written files."""
    warnings = []
    ext = os.path.splitext(path)[1].lower()

    if ext == ".py":
        try:
            compile(content, path, 'exec')
        except SyntaxError as e:
            warnings.append(
                f"SYNTAX ERROR at line {e.lineno}: {e.msg}. "
                f"Rewrite the file with correct syntax.")

    if ext == ".html":
        placeholders = ["Short bio", ">Name<", ">Role<",
                        "placeholder text", "Lorem ipsum",
                        ">Description<", ">Title<"]
        found = [p for p in placeholders if p.lower() in content.lower()]
        if found:
            warnings.append(
                f"Contains placeholder text: {', '.join(found)}. "
                f"Replace with realistic content.")

        if "fonts.googleapis" not in content and "fonts.google" not in content:
            warnings.append(
                "No Google Fonts import. Add a Google Fonts link.")

    elif ext == ".css":
        import re
        colors = re.findall(r'#[0-9a-fA-F]{3,6}', content)
        generic = {"#333", "#333333", "#666", "#666666", "#999",
                   "#fff", "#ffffff", "#f4f4f4", "#f5f5f5", "#f4f4f9",
                   "#eee", "#eeeeee", "#ddd", "#ccc", "#000", "#000000"}
        unique_colors = set(c.lower() for c in colors) - generic
        if len(unique_colors) == 0 and colors:
            warnings.append(
                "All colors are generic greys/whites. "
                "REWRITE with a real color palette.")

        if "transition" not in content:
            warnings.append("No CSS transitions found.")
        if "padding" not in content:
            warnings.append("No padding found in CSS.")

    return warnings
