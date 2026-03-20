"""Round data store for session inspection endpoints.

Stores per-round token data (input/output/context) and file operations
(read/edit) for serving via /session/<sid>/<type>/<round_id> endpoints.

Storage: data/_/runtime/sessions/<sid>/rounds/<round_id>.json
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

    count_str = f" ({token_count:,})" if token_count else ""
    title = f"{data_type.title()} Tokens{count_str}"
    display = content.replace("\\n", "\n").replace("\\t", "\t")
    lines = display.split("\n")
    numbered = []
    for i, line in enumerate(lines, 1):
        numbered.append(
            f'<span class="ln">{i:>5}</span> {_esc(line)}'
        )
    body = "".join(numbered)

    meta_parts = [f"Session: {_esc(session_id)}",
                  f"Round {round_num}",
                  f"{data_type.title()} Tokens{count_str}"]
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

    body = "".join(numbered)
    return _wrap_page(title, session_id, f"""
    <div class="meta">Session: {_esc(session_id)} &middot; Round {round_num} &middot; Read</div>
    <div class="filepath">{_esc(path)}</div>
    <pre class="code">{body}</pre>
    {truncated}
    """)


def render_edit_page(session_id: str, round_num: int, op: dict) -> str:
    """Render full file snapshot with changed lines highlighted in red/green."""
    path = op["path"]
    old_text = op.get("old_content", "")
    new_text = op.get("new_content", "")
    full_content = op.get("content", "")
    title = f"Edit {path} - Round {round_num}"

    if not full_content:
        body = "<span class='meta'>No file content available.</span>"
        return _wrap_page(title, session_id, f"""
        <div class="meta">Session: {_esc(session_id)} &middot; Round {round_num} &middot; Edit</div>
        <div class="filepath">{_esc(path)}</div>
        <pre class="code diff">{body}</pre>
        """)

    all_lines = full_content.split("\n")
    old_lines = old_text.split("\n") if old_text else []
    new_lines = new_text.split("\n") if new_text else []

    added_start = -1
    added_end = -1
    if new_text and new_text in full_content:
        char_pos = full_content.find(new_text)
        added_start = full_content[:char_pos].count("\n")
        added_end = added_start + len(new_lines) - 1

    lines_out = []
    for i, line in enumerate(all_lines):
        ln = f'<span class="ln">{i+1:>5}</span>'
        if added_start <= i <= added_end:
            if i == added_start and old_lines:
                for ol in old_lines:
                    lines_out.append(f'<span class="del"><span class="ln">{"":>5}</span> {_esc(ol)}</span>')
            lines_out.append(f'<span class="add">{ln} {_esc(line)}</span>')
        else:
            lines_out.append(f'<span class="hl">{ln} {_esc(line)}</span>')

    body = "".join(lines_out)

    return _wrap_page(title, session_id, f"""
    <div class="meta">Session: {_esc(session_id)} &middot; Round {round_num} &middot; Edit</div>
    <div class="filepath">{_esc(path)}</div>
    <pre class="code diff">{body}</pre>
    """)


def _not_found_page(msg: str) -> str:
    return _wrap_page("Not Found", "", f'<div class="meta" style="text-align:center;padding:40px;">{_esc(msg)}</div>')


def _wrap_page(title: str, session_id: str, body: str) -> str:
    favicon = ('data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 '
               'width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 '
               'fill=%22%235b8def%22><path d=%22M21.928 11.607c-.202-.488-.635-.605'
               '-.928-.633V8c0-1.103-.897-2-2-2h-6V4.61c.305-.274.5-.668.5-1.11a1.5'
               ' 1.5 0 0 0-3 0c0 .442.195.836.5 1.11V6H5c-1.103 0-2 .897-2 '
               '2v2.997l-.082.006A1 1 0 0 0 1.99 12v2a1 1 0 0 0 1 1H3v5c0 1.103'
               '.897 2 2 2h14c1.103 0 2-.897 2-2v-5a1 1 0 0 0 1-1v-1.938a1.006 '
               '1.006 0 0 0-.072-.455zM5 20V8h14l.001 3.996L19 12v2l.001.005.001 '
               '5.995H5z%22/><ellipse cx=%228.5%22 cy=%2212%22 rx=%221.5%22 '
               'ry=%222%22/><ellipse cx=%2215.5%22 cy=%2212%22 rx=%221.5%22 '
               'ry=%222%22/><path d=%22M8 16h8v2H8z%22/></svg>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<link rel="icon" href="{favicon}">
<style>
:root {{ --bg: #1e1e2e; --surface: #272740; --text: #cdd6f4; --text-2: #a6adc8;
         --accent: #89b4fa; --green: #a6e3a1; --red: #f38ba8; --yellow: #f9e2af;
         --mono: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; --border: #45475a; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font-family: var(--mono);
        font-size: 13px; line-height: 1.65; padding: 16px; }}
.meta {{ color: var(--text-2); font-size: 11px; margin-bottom: 8px; padding: 8px 12px;
         background: var(--surface); border-radius: 6px; border-left: 3px solid var(--accent); }}
.filepath {{ color: var(--accent); font-size: 13px; font-weight: 600; margin: 8px 0;
             padding: 6px 12px; background: var(--surface); border-radius: 4px; }}
.code {{ background: var(--surface); padding: 12px 0; border-radius: 8px;
         overflow-x: auto; white-space: pre; border: 1px solid var(--border);
         line-height: 1.65; font-size: 13px; }}
.code > span {{ display: block; padding: 0 12px; }}
.code > span:hover {{ background: rgba(255,255,255,0.03); }}
.ln {{ color: var(--text-2); opacity: 0.4; display: inline-block; min-width: 4ch;
       text-align: right; margin-right: 16px; user-select: none; font-size: 12px; }}
.hl {{ background: rgba(137, 180, 250, 0.08); }}
.diff .add {{ color: var(--green); display: block; padding: 0 12px; background: rgba(166, 227, 161, 0.08); }}
.diff .del {{ color: var(--red); display: block; padding: 0 12px; background: rgba(243, 139, 168, 0.08); }}
.diff .hdr {{ color: var(--text-2); display: block; padding: 0 12px; font-weight: 600; }}
.diff .hunk {{ color: var(--accent); display: block; padding: 0 12px; }}
.diff .ctx {{ color: var(--text-2); display: block; padding: 0 12px; }}
.trunc {{ color: var(--yellow); font-size: 11px; padding: 8px 12px; margin-top: 8px;
          background: rgba(249, 226, 175, 0.1); border-radius: 4px; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
