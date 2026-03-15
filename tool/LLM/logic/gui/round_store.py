"""Round data store for session inspection endpoints.

Stores per-round token data (input/output/context) and file operations
(read/edit) for serving via /session/<sid>/<type>/<round_id> endpoints.

Storage: runtime/sessions/<sid>/rounds/<round_id>.json
"""
import json
import os
from typing import Dict, List, Optional
from html import escape as _esc

_SESSIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "runtime", "sessions"
)

MAX_TOKEN_ENTRIES = 1024
MAX_TOKEN_CHARS = 131072  # 128k
MAX_FILE_ENTRIES = 128
MAX_FILE_LINES = 16384
DEFAULT_FILE_LINES = 1024

HARD_LIMITS = {
    "token_entries": MAX_TOKEN_ENTRIES,
    "token_chars": MAX_TOKEN_CHARS,
    "file_entries": MAX_FILE_ENTRIES,
    "file_lines": MAX_FILE_LINES,
}


class RoundStore:
    """In-memory + disk store for round inspection data."""

    def __init__(self, max_token_entries: int = 32,
                 max_token_chars: int = 16384,
                 max_context_entries: int = 8,
                 max_file_entries: int = 32,
                 max_file_lines: int = DEFAULT_FILE_LINES):
        self._token_entries = min(max_token_entries, MAX_TOKEN_ENTRIES)
        self._token_chars = min(max_token_chars, MAX_TOKEN_CHARS)
        self._context_entries = min(max_context_entries, 32)
        self._file_entries = min(max_file_entries, MAX_FILE_ENTRIES)
        self._file_lines = min(max_file_lines, MAX_FILE_LINES)

        self._data: Dict[str, Dict[int, dict]] = {}

    def record_round(self, session_id: str, round_num: int,
                     input_tokens: str = "",
                     output_tokens: str = "",
                     context_messages: Optional[list] = None):
        """Record token data for a round."""
        if session_id not in self._data:
            self._data[session_id] = {}

        trunc_input = input_tokens[:self._token_chars] if input_tokens else ""
        trunc_output = output_tokens[:self._token_chars] if output_tokens else ""

        entry = self._data[session_id].get(round_num, {})
        entry["input"] = trunc_input
        entry["output"] = trunc_output
        if context_messages is not None:
            ctx_str = json.dumps(context_messages[-self._context_entries:],
                                 ensure_ascii=False, indent=1)
            entry["context"] = ctx_str[:self._token_chars]
        self._data[session_id][round_num] = entry

        while len(self._data[session_id]) > self._token_entries:
            oldest = min(self._data[session_id].keys())
            del self._data[session_id][oldest]

    def record_file_op(self, session_id: str, round_num: int,
                       op_type: str, rel_path: str,
                       content: str = "",
                       start_line: int = 0, end_line: int = 0,
                       old_content: str = "", new_content: str = "",
                       op_id: int = 0):
        """Record a file read or edit operation."""
        if session_id not in self._data:
            self._data[session_id] = {}
        entry = self._data[session_id].get(round_num, {})

        ops_key = "file_ops"
        if ops_key not in entry:
            entry[ops_key] = []

        lines = content.split("\n") if content else []
        if len(lines) > self._file_lines:
            lines = lines[:self._file_lines]
            lines.append(f"... (truncated, {len(content.splitlines())} total lines)")

        op_data = {
            "type": op_type,
            "path": rel_path,
            "content": "\n".join(lines),
            "start_line": start_line,
            "end_line": end_line,
            "id": op_id,
        }
        if op_type == "edit":
            old_lines = old_content.split("\n") if old_content else []
            new_lines = new_content.split("\n") if new_content else []
            if len(old_lines) > self._file_lines:
                old_lines = old_lines[:self._file_lines]
            if len(new_lines) > self._file_lines:
                new_lines = new_lines[:self._file_lines]
            op_data["old_content"] = "\n".join(old_lines)
            op_data["new_content"] = "\n".join(new_lines)

        entry[ops_key].append(op_data)

        while len(entry[ops_key]) > self._file_entries:
            entry[ops_key].pop(0)

        self._data[session_id][round_num] = entry

    def get_token_data(self, session_id: str, round_num: int,
                       data_type: str) -> Optional[str]:
        """Get token data for rendering. Returns raw text or None."""
        rounds = self._data.get(session_id, {})
        entry = rounds.get(round_num, {})
        return entry.get(data_type)

    def get_file_op(self, session_id: str, round_num: int,
                    op_type: str, rel_path: str,
                    op_id: int = 0) -> Optional[dict]:
        """Get a specific file operation."""
        rounds = self._data.get(session_id, {})
        entry = rounds.get(round_num, {})
        for op in entry.get("file_ops", []):
            if (op["type"] == op_type and
                op["path"] == rel_path and
                op.get("id", 0) == op_id):
                return op
        return None

    def list_file_ops(self, session_id: str, round_num: int) -> List[dict]:
        """List all file ops for a round."""
        rounds = self._data.get(session_id, {})
        entry = rounds.get(round_num, {})
        return entry.get("file_ops", [])


def render_token_page(session_id: str, round_num: int,
                      data_type: str, content: Optional[str],
                      token_count: int = 0, cost: float = 0.0) -> str:
    """Render an HTML page for token inspection."""
    if content is None:
        return _not_found_page(f"No {data_type} data for round {round_num}")

    title = f"{data_type.title()} Tokens - Round {round_num}"
    display = content.replace("\\n", "\n").replace("\\t", "\t")
    lines = display.split("\n")
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(
            f'<span class="ln">{i:>5}</span> {_esc(line)}'
        )
    body = "\n".join(numbered)

    meta_parts = [f"Session: {_esc(session_id)}",
                  f"Round {round_num}",
                  data_type.title()]
    if token_count:
        meta_parts.append(f"{token_count:,} tokens")
    if cost:
        meta_parts.append(f"${cost:.6f}")
    meta_line = " &middot; ".join(meta_parts)

    return _wrap_page(title, session_id, f"""
    <div class="meta">{meta_line}</div>
    <pre class="code">{body}</pre>
    """)


def render_read_page(session_id: str, round_num: int, op: dict) -> str:
    """Render a file read page with highlighted read range."""
    path = op["path"]
    content = op["content"]
    start = op.get("start_line", 0)
    end = op.get("end_line", 0)
    title = f"Read {path} - Round {round_num}"

    lines = content.split("\n")
    numbered = []
    for i, line in enumerate(lines, 1):
        actual_line = start + i - 1 if start > 0 else i
        is_highlight = True if (start > 0 and end > 0 and start <= actual_line <= end) else (start == 0)
        cls = ' class="hl"' if is_highlight else ""
        numbered.append(
            f'<span{cls}><span class="ln">{actual_line:>5}</span> {_esc(line)}</span>'
        )

    truncated = ""
    if lines and lines[-1].startswith("... (truncated"):
        truncated = '<div class="trunc">File too large. Only showing read portion.</div>'

    body = "\n".join(numbered)
    return _wrap_page(title, session_id, f"""
    <div class="meta">Session: {_esc(session_id)} &middot; Round {round_num} &middot; Read</div>
    <div class="filepath">{_esc(path)}</div>
    <pre class="code">{body}</pre>
    {truncated}
    """)


def render_edit_page(session_id: str, round_num: int, op: dict) -> str:
    """Render a file edit page with red/green diff highlighting."""
    path = op["path"]
    old_content = op.get("old_content", "")
    new_content = op.get("new_content", "")
    title = f"Edit {path} - Round {round_num}"

    import difflib
    old_lines = old_content.split("\n") if old_content else []
    new_lines = new_content.split("\n") if new_content else []

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=3))

    if not diff:
        if new_content and not old_content:
            numbered = []
            for i, line in enumerate(new_lines, 1):
                numbered.append(f'<span class="add"><span class="ln">{i:>5}</span> +{_esc(line)}</span>')
            body = "\n".join(numbered)
        else:
            body = "<span class='meta'>No changes detected.</span>"
    else:
        lines_out = []
        for line in diff:
            if line.startswith("+++") or line.startswith("---"):
                lines_out.append(f'<span class="hdr">{_esc(line)}</span>')
            elif line.startswith("@@"):
                lines_out.append(f'<span class="hunk">{_esc(line)}</span>')
            elif line.startswith("+"):
                lines_out.append(f'<span class="add">{_esc(line)}</span>')
            elif line.startswith("-"):
                lines_out.append(f'<span class="del">{_esc(line)}</span>')
            else:
                lines_out.append(f'<span class="ctx">{_esc(line)}</span>')
        body = "\n".join(lines_out)

    return _wrap_page(title, session_id, f"""
    <div class="meta">Session: {_esc(session_id)} &middot; Round {round_num} &middot; Edit</div>
    <div class="filepath">{_esc(path)}</div>
    <pre class="code diff">{body}</pre>
    """)


def _not_found_page(msg: str) -> str:
    return _wrap_page("Not Found", "", f'<div class="meta" style="text-align:center;padding:40px;">{_esc(msg)}</div>')


def _wrap_page(title: str, session_id: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
:root {{ --bg: #1e1e2e; --surface: #272740; --text: #cdd6f4; --text-2: #a6adc8;
         --accent: #89b4fa; --green: #a6e3a1; --red: #f38ba8; --yellow: #f9e2af;
         --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; --border: #45475a; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font-family: var(--mono);
        font-size: 12px; line-height: 1.6; padding: 16px; }}
.meta {{ color: var(--text-2); font-size: 11px; margin-bottom: 8px; padding: 8px 12px;
         background: var(--surface); border-radius: 6px; border-left: 3px solid var(--accent); }}
.filepath {{ color: var(--accent); font-size: 13px; font-weight: 600; margin: 8px 0;
             padding: 6px 12px; background: var(--surface); border-radius: 4px; }}
.code {{ background: var(--surface); padding: 12px; border-radius: 8px;
         overflow-x: auto; white-space: pre; border: 1px solid var(--border); }}
.ln {{ color: var(--text-2); opacity: 0.5; display: inline-block; min-width: 5ch;
       text-align: right; margin-right: 12px; user-select: none; }}
.hl {{ background: rgba(137, 180, 250, 0.08); display: block; }}
.diff .add {{ color: var(--green); display: block; background: rgba(166, 227, 161, 0.08); }}
.diff .del {{ color: var(--red); display: block; background: rgba(243, 139, 168, 0.08); }}
.diff .hdr {{ color: var(--text-2); display: block; font-weight: 600; }}
.diff .hunk {{ color: var(--accent); display: block; }}
.diff .ctx {{ color: var(--text-2); display: block; }}
.trunc {{ color: var(--yellow); font-size: 11px; padding: 8px 12px; margin-top: 8px;
          background: rgba(249, 226, 175, 0.1); border-radius: 4px; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
