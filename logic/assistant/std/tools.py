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
    """Build env dict with bin/ and homebrew paths prepended.

    Ensures ecosystem tools (TOOL, BRAIN, SKILLS, etc.) are accessible
    from any workspace CWD, not just the project root.
    """
    env = os.environ.copy()
    extra_paths = []
    bin_dir = os.path.join(project_root, "bin")
    if os.path.isdir(bin_dir):
        extra_paths.append(bin_dir)
        extra_paths.extend(
            os.path.join(bin_dir, d) for d in os.listdir(bin_dir)
            if os.path.isdir(os.path.join(bin_dir, d)))
    homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    extra_paths.extend(p for p in homebrew_paths if os.path.isdir(p))
    if extra_paths:
        env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")
    env["TOOL_PROJECT_ROOT"] = project_root
    return env


@register_tool("exec")
def handle_exec(args: dict, ctx: ToolContext) -> dict:
    cmd = args.get("command", "")
    block_ms = args.get("block_until_ms", _DEFAULT_BLOCK_MS)
    timeout_policy = args.get("timeout_policy", "ok")

    first_word = cmd.strip().split()[0] if cmd.strip() else "exec"
    exec_desc = f"Run {first_word}" if len(cmd) > 40 else cmd
    ctx.emit({"type": "tool", "name": "exec", "desc": exec_desc, "cmd": cmd})

    try:
        from logic.assistant.sandbox import get_sandbox
        import uuid as _uuid
        sb = get_sandbox()
        sb.mode = ctx.mode
        decision, reason = sb.check_permission(cmd, cwd=ctx.cwd)
        if decision == "deny":
            ctx.emit({"type": "tool_result", "ok": False,
                       "output": f"[Sandbox] Blocked: {reason}"})
            return {"ok": False, "output": f"[Sandbox] Blocked: {reason}"}
        if decision in ("ask", "ask_mandatory"):
            mandatory = decision == "ask_mandatory"
            req_id = str(_uuid.uuid4())[:8]
            sb.create_pending(req_id, cmd, ctx.session_id, mandatory=mandatory)
            ctx.emit({"type": "sandbox_prompt", "request_id": req_id,
                       "cmd": cmd, "normalized": sb._normalize_cmd(cmd),
                       "mandatory": mandatory,
                       "timeout": 0 if mandatory else sb.popup_timeout,
                       "created_at": time.time()})
            while True:
                pending = sb.get_pending(req_id)
                if pending is None:
                    break
                time.sleep(0.5)
            resolved = sb.get_resolved(req_id)
            if resolved == "deny":
                ctx.emit({"type": "tool_result", "ok": False,
                           "output": "[Sandbox] Command denied by user."})
                return {"ok": False, "output": "[Sandbox] Command denied by user."}
    except ImportError:
        pass

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

    if os.path.isfile(path) and (start_line is None or end_line is None):
        ctx.emit({"type": "tool", "name": "read",
                  "desc": f"Read {os.path.basename(path)}", "cmd": path})
        msg = ("You must specify start_line and end_line. "
               "Use search() first to find the relevant line range, "
               "then read_file with precise line numbers.")
        ctx.emit({"type": "tool_result", "ok": False, "output": msg})
        return {"ok": False, "output": msg}

    ctx.turn_reads.append(path)
    basename = os.path.basename(path.rstrip("/"))
    is_full_read = False
    read_display = None
    try:
        if os.path.isdir(path):
            read_desc = f"List {basename}" if basename else "List directory"
            ctx.emit({"type": "tool", "name": "read", "desc": read_desc, "cmd": path})
            entries = sorted(os.listdir(path))[:50]
            content = f"Directory listing of {path}:\n" + "\n".join(entries)
        else:
            raw = open(path, encoding='utf-8', errors='replace').read()
            lines = raw.splitlines(keepends=True)
            total_lines = len(lines)
            s = max(1, start_line) - 1
            e = min(total_lines, end_line)
            is_full_read = (s == 0 and e >= total_lines)

            read_desc = f"Read {basename}"
            if not is_full_read:
                read_desc += f" L{s+1}-{e}"
            ctx.emit({"type": "tool", "name": "read", "desc": read_desc, "cmd": path,
                      "start_line": start_line, "end_line": end_line,
                      "_is_full_read": is_full_read})

            selected = lines[s:e]
            numbered = [f"{s+i+1:>4}| {line}" for i, line in enumerate(selected)]
            content = "".join(numbered)
            if len(content) > 15000:
                content = content[:15000] + f"\n... (truncated, lines {s+1}-{e} of {total_lines})"
            else:
                content += f"\n[Lines {s+1}-{e} of {total_lines} total]"
            if not is_full_read:
                read_display = _build_read_display(
                    lines, s, e, total_lines, ctx_n=ctx.context_lines)
        emit_data = {"type": "tool_result", "ok": True, "output": content,
                     "_is_full_read": is_full_read}
        if not is_full_read and not os.path.isdir(path) and read_display:
            emit_data["_read_display"] = read_display
        ctx.emit(emit_data)
        if ctx.env_obj:
            ctx.env_obj.record_result(f"read:{path}", True, content[:200])
        rs = getattr(ctx, 'round_store', None)
        if rs:
            rel = os.path.relpath(path, ctx.cwd) if os.path.isabs(path) else path
            rs.record_file_op(
                getattr(ctx, 'session_id', ''),
                getattr(ctx, 'round_num', 0),
                "read", rel, content,
                start_line=start_line or 0,
                end_line=end_line or 0)
        return {"ok": True, "output": content}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        if ctx.env_obj:
            ctx.env_obj.record_result(f"read:{path}", False, str(e))
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
        if ctx.env_obj:
            ctx.env_obj.record_result(f"search:{pattern}", True, output[:300])
        return {"ok": True, "output": output}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        if ctx.env_obj:
            ctx.env_obj.record_result(f"search:{pattern}", False, str(e))
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
    is_new_file = not os.path.exists(path)
    old_content_for_diff = None
    if not is_new_file:
        try:
            old_content_for_diff = open(path, encoding='utf-8', errors='replace').read()
        except Exception:
            pass

    desc = f"Created {write_basename} (New)" if is_new_file else f"Edited {write_basename}"
    ctx.emit({"type": "tool", "name": "edit_file", "desc": desc, "file": path,
              "_is_new": is_new_file})
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

        if old_content_for_diff is not None and old_content_for_diff != content:
            gui_output = _compute_write_diff(old_content_for_diff, content, getattr(ctx, 'context_lines', 2))
            ctx.emit({"type": "tool_result", "ok": True,
                      "output": gui_output, "_is_diff": True,
                      "name": "edit_file", "_path": path,
                      "_old_text": old_content_for_diff, "_new_text": content})
        else:
            all_lines = content.split('\n')
            gui_limit = 2000
            if len(all_lines) > gui_limit + 10:
                gui_preview = '\n'.join(all_lines[:gui_limit]) + f'\n... ({len(all_lines) - gui_limit} more lines)'
            else:
                gui_preview = content
            ctx.emit({"type": "tool_result", "ok": True,
                      "output": base_msg + warn_suffix + "\n" + gui_preview,
                      "name": "edit_file", "_path": path,
                      "_is_new": is_new_file})
        if ctx.env_obj:
            ctx.env_obj.record_result(f"write:{path}", True, f"{size} bytes")

        agent_limit = 50
        if len(all_lines) > agent_limit + 10:
            agent_preview = '\n'.join(all_lines[:agent_limit]) + f'\n... ({len(all_lines) - agent_limit} more lines)'
        else:
            agent_preview = content
        return {"ok": True, "output": base_msg + warn_suffix + "\n" + agent_preview}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        if ctx.env_obj:
            ctx.env_obj.record_result(f"write:{path}", False, str(e))
        return {"ok": False, "output": str(e)}


def _build_diff_preview(all_lines, start_lineno, old_lines, new_lines, new_all, ctx_n):
    """Build a diff preview with context lines and hidden-line markers."""
    diff_lines = []
    pre_start = max(0, start_lineno - ctx_n)
    if pre_start > 0:
        diff_lines.append(f"@@hide {pre_start}")
    for i in range(pre_start, start_lineno):
        if i < len(all_lines):
            diff_lines.append(f" {i+1:>5}|{all_lines[i]}")
    for ol in old_lines:
        diff_lines.append(f"-{ol}")
    for nl in new_lines:
        diff_lines.append(f"+{nl}")
    new_change_end = start_lineno + len(new_lines)
    for i in range(new_change_end, min(len(new_all), new_change_end + ctx_n)):
        diff_lines.append(f" {i+1:>5}|{new_all[i]}")
    remaining = len(new_all) - min(len(new_all), new_change_end + ctx_n)
    if remaining > 0:
        diff_lines.append(f"@@hide {remaining}")
    return "\n".join(diff_lines)


def _apply_edit_and_emit(path, content, old_lines_text, new_text, start_lineno,
                         ctx, ctx_n=None):
    """Apply an edit, run syntax check, emit diff preview, return result."""
    if ctx_n is None:
        ctx_n = getattr(ctx, 'context_lines', 2)
    old_lines = old_lines_text.splitlines()
    new_lines = new_text.splitlines()
    all_lines = content.splitlines()

    new_content = content.replace(old_lines_text, new_text, 1)

    _syntax_warning = ""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        try:
            compile(new_content, path, 'exec')
        except SyntaxError as e:
            _syntax_warning = (f"⚠ Syntax warning: "
                               f"{e.msg} ({os.path.basename(path)}, line {e.lineno})")

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    new_all = new_content.splitlines()
    diff_preview = _build_diff_preview(all_lines, start_lineno, old_lines,
                                       new_lines, new_all, ctx_n)
    if _syntax_warning:
        diff_preview += f"\n\n{_syntax_warning}"
    ctx.emit({"type": "tool_result", "ok": True,
              "output": diff_preview,
              "name": "edit_file", "_path": path,
              "_old_text": old_lines_text, "_new_text": new_text})
    if ctx.env_obj:
        ctx.env_obj.record_result(f"edit:{path}", True, diff_preview)
    rs = getattr(ctx, 'round_store', None)
    sid = getattr(ctx, 'session_id', '')
    rn = getattr(ctx, 'round_num', 0)
    if rs:
        rel = os.path.relpath(path, ctx.cwd) if os.path.isabs(path) else path
        rs.record_file_op(sid, rn, "edit", rel, new_content,
                          old_content=old_lines_text, new_content=new_text)
    return {"ok": True, "output": f"Edit applied to {path}"}


@register_tool("edit_file")
def handle_edit_file(args: dict, ctx: ToolContext) -> dict:
    path = args.get("path", "")
    new_text = args.get("new_text", args.get("content", ""))
    start_line = args.get("start_line")
    end_line = args.get("end_line")
    if not path:
        return {"ok": False, "output": "Missing path"}

    abs_path = path if os.path.isabs(path) else os.path.join(ctx.cwd, path)

    try:
        from logic.assistant.sandbox import get_sandbox
        import uuid as _uuid
        sb = get_sandbox()
        edit_decision, edit_reason = sb.check_edit_permission(abs_path)
        if edit_decision == "ask_mandatory":
            req_id = str(_uuid.uuid4())[:8]
            sb.create_pending(req_id, f"edit {abs_path}", getattr(ctx, 'session_id', ''),
                              mandatory=True, kind="edit")
            ctx.emit({"type": "sandbox_prompt", "request_id": req_id,
                       "cmd": f"edit {os.path.basename(abs_path)}",
                       "normalized": f"edit (outside workspace)",
                       "mandatory": True, "timeout": 0,
                       "created_at": time.time()})
            while True:
                pending = sb.get_pending(req_id)
                if pending is None:
                    break
                time.sleep(0.5)
            resolved = sb.get_resolved(req_id)
            if resolved == "deny":
                ctx.emit({"type": "tool_result", "ok": False,
                           "output": f"[Sandbox] Edit denied: file outside workspace"})
                return {"ok": False,
                        "output": f"[Sandbox] Edit denied: {abs_path} is outside workspace"}
    except ImportError:
        pass

    if not os.path.exists(abs_path):
        result = handle_write_file({"path": path, "content": new_text}, ctx)
        result["_is_new_file"] = True
        return result

    if not os.path.isabs(path):
        path = os.path.join(ctx.cwd, path)

    ctx.emit({"type": "tool", "name": "edit_file",
              "desc": f"Edit {os.path.basename(path)}", "cmd": f"edit {path}"})

    try:
        content = open(path, encoding='utf-8', errors='replace').read()
        all_lines = content.splitlines()
        total = len(all_lines)

        if start_line is not None and end_line is not None:
            s = max(1, int(start_line))
            e = min(total, int(end_line))
            if s > total:
                ctx.emit({"type": "tool_result", "ok": False,
                           "output": f"start_line {s} > total lines {total}"})
                return {"ok": False,
                        "output": f"start_line {s} exceeds file length ({total} lines). "
                                  f"Use read_file to check current content."}

            old_range = all_lines[s-1:e]
            old_lines_list = old_range
            new_lines_list = new_text.rstrip("\n").splitlines() if new_text.strip() else []
            start_lineno = s - 1

            result_lines = all_lines[:s-1] + new_lines_list + all_lines[e:]
            new_content = "\n".join(result_lines)
            if content.endswith("\n"):
                new_content += "\n"

            _syntax_warning = ""
            ext = os.path.splitext(path)[1].lower()
            if ext == ".py":
                try:
                    compile(new_content, path, 'exec')
                except SyntaxError as syn_e:
                    _syntax_warning = (f"⚠ Syntax warning: "
                                       f"{syn_e.msg} ({os.path.basename(path)}, line {syn_e.lineno})")

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            new_all = new_content.splitlines()
            diff_preview = _build_diff_preview(
                all_lines, start_lineno, old_lines_list,
                new_lines_list, new_all, ctx.context_lines)
            if _syntax_warning:
                diff_preview += f"\n\n{_syntax_warning}"
            ctx.emit({"type": "tool_result", "ok": True,
                      "output": diff_preview,
                      "name": "edit_file", "_path": path,
                      "_old_text": "\n".join(old_lines_list),
                      "_new_text": new_text.rstrip("\n")})
            if ctx.env_obj:
                ctx.env_obj.record_result(f"edit:{path}", True, diff_preview)
            rs = getattr(ctx, 'round_store', None)
            sid = getattr(ctx, 'session_id', '')
            rn = getattr(ctx, 'round_num', 0)
            if rs:
                rel = os.path.relpath(path, ctx.cwd) if os.path.isabs(path) else path
                rs.record_file_op(sid, rn, "edit", rel, new_content,
                                  old_content="\n".join(old_lines_list),
                                  new_content=new_text)
            return {"ok": True, "output": f"Edit applied to {path} (L{s}-{e})"}

        ctx.emit({"type": "tool_result", "ok": False,
                   "output": "Must provide start_line and end_line for existing files"})
        return {"ok": False,
                "output": "For existing files, provide start_line and end_line to "
                          "specify the edit range. Use read_file first to find "
                          "exact line numbers."}
    except Exception as e:
        ctx.emit({"type": "tool_result", "ok": False, "output": str(e)})
        if ctx.env_obj:
            ctx.env_obj.record_result(f"edit:{path}", False, str(e))
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


@register_tool("switch_mode")
def handle_switch_mode(args: dict, ctx: ToolContext) -> dict:
    """Handle mode switch requests (e.g. agent -> plan).

    This is a sandbox-like gate: the user controls whether mode switches
    are allowed, denied by default, or require per-instance approval.
    """
    target = args.get("target_mode", args.get("mode", "plan"))
    explanation = args.get("explanation", "")

    ctx.emit({"type": "tool", "name": "switch_mode",
              "desc": f"Switch to {target} mode"})

    try:
        from logic.assistant.sandbox import get_sandbox
        import uuid as _uuid
        sb = get_sandbox()
        policy = sb.mode_switch_policy

        if policy == "deny":
            output = (
                f"[Mode Switch] Denied by policy. Cannot switch to {target} mode.\n"
                "Fallback: Write your plan to a tmp/ script or use the TODO tool "
                "to organize tasks instead."
            )
            ctx.emit({"type": "tool_result", "ok": False, "output": output})
            return {"ok": False, "output": output}

        if policy == "allow":
            sb.mode = target
            ctx.emit({"type": "mode_switch_resolved",
                       "decision": "allow", "target_mode": target})
            output = f"[Mode Switch] Switched to {target} mode."
            ctx.emit({"type": "tool_result", "ok": True, "output": output})
            return {"ok": True, "output": output, "mode": target}

        req_id = str(_uuid.uuid4())[:8]
        sb.create_pending(req_id, f"switch_mode:{target}", ctx.session_id,
                          mandatory=False, kind="mode_switch")
        ctx.emit({"type": "sandbox_prompt", "request_id": req_id,
                   "cmd": f"Switch to {target} mode",
                   "normalized": f"mode → {target}",
                   "mandatory": False,
                   "timeout": sb.mode_switch_timeout,
                   "created_at": time.time(),
                   "kind": "mode_switch",
                   "explanation": explanation})

        while True:
            pending = sb.get_pending(req_id)
            if pending is None:
                break
            time.sleep(0.5)

        resolved = sb.get_resolved(req_id)
        if resolved == "allow":
            sb.mode = target
            ctx.emit({"type": "mode_switch_resolved",
                       "decision": "allow", "target_mode": target})
            output = f"[Mode Switch] Approved. Now in {target} mode."
            ctx.emit({"type": "tool_result", "ok": True, "output": output})
            return {"ok": True, "output": output, "mode": target}
        else:
            output = (
                f"[Mode Switch] User denied switch to {target} mode.\n"
                "Fallback: Write your plan to a tmp/ script or use the TODO tool "
                "to organize tasks instead."
            )
            ctx.emit({"type": "tool_result", "ok": False, "output": output})
            return {"ok": False, "output": output}
    except ImportError:
        output = f"[Mode Switch] Sandbox not available. Proceeding with {target} mode."
        ctx.emit({"type": "tool_result", "ok": True, "output": output})
        return {"ok": True, "output": output, "mode": target}


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


def _build_read_display(lines: list, s: int, e: int, total: int, ctx_n: int = 5) -> str:
    """Build display text for a ranged file read with hidden lines and context.

    Format: @@hide N / context lines / @@read / read lines / @@read_end / context / @@hide M
    """
    parts = []
    ctx_start = max(0, s - ctx_n)
    ctx_end = min(total, e + ctx_n)
    if ctx_start > 0:
        parts.append(f"@@hide {ctx_start}")
    for i in range(ctx_start, s):
        ln = lines[i].rstrip('\n').rstrip('\r')
        parts.append(f"{i+1:>4}| {ln}")
    parts.append("@@read")
    for i in range(s, e):
        ln = lines[i].rstrip('\n').rstrip('\r')
        parts.append(f"{i+1:>4}| {ln}")
    parts.append("@@read_end")
    for i in range(e, ctx_end):
        ln = lines[i].rstrip('\n').rstrip('\r')
        parts.append(f"{i+1:>4}| {ln}")
    if ctx_end < total:
        parts.append(f"@@hide {total - ctx_end}")
    return "\n".join(parts)


def _compute_write_diff(old_content: str, new_content: str, ctx_n: int = 5) -> str:
    """Compute a unified diff between old and new file content for GUI display.

    Returns diff in the same format as edit_file (with @@hide, +/- lines, context).
    """
    import difflib
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    diff_lines = []
    all_old = old_content.splitlines()
    all_new = new_content.splitlines()

    groups = list(matcher.get_grouped_opcodes(ctx_n))
    for group in groups:
        first_tag, first_i1, _, _, _ = group[0]
        if first_i1 > 0 and first_tag == 'equal':
            hidden = first_i1
        elif first_i1 > 0:
            hidden = first_i1
        else:
            hidden = 0
        if hidden > 0:
            diff_lines.append(f"@@hide {hidden}")

        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for i in range(i1, i2):
                    diff_lines.append(f" {i+1:>5}|{all_old[i]}")
            elif tag == 'replace':
                for i in range(i1, i2):
                    diff_lines.append(f"-{all_old[i]}")
                for j in range(j1, j2):
                    diff_lines.append(f"+{all_new[j]}")
            elif tag == 'delete':
                for i in range(i1, i2):
                    diff_lines.append(f"-{all_old[i]}")
            elif tag == 'insert':
                for j in range(j1, j2):
                    diff_lines.append(f"+{all_new[j]}")

    last_tag, _, last_i2, _, last_j2 = groups[-1][-1] if groups else ('', 0, 0, 0, 0)
    remaining = len(all_new) - last_j2
    if remaining > 0:
        diff_lines.append(f"@@hide {remaining}")

    return "\n".join(diff_lines)


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
