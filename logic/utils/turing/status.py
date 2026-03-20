"""Reusable terminal status-message formatters.

Enforces the minimal-emphasis rule: bold/color only on the core phrase,
complements and details in default or dim style.  All functions return
formatted strings — the caller decides when to print or write them.

Usage::

    from logic.utils.turing.status import fmt_status, fmt_detail, fmt_stage

    print(fmt_status("Saved.", dim="3 policies"))
    print(fmt_detail("Session be58ac60 is ready."))
    print(fmt_stage("Starting session...", status="active"))
"""

from __future__ import annotations

import shutil

from logic._.config import get_color, get_global_config

BOLD = get_color("BOLD", "\033[1m")
DIM = get_color("DIM", "\033[2m")
GREEN = get_color("GREEN", "\033[1m\033[32m")
RED = get_color("RED", "\033[1m\033[31m")
YELLOW = get_color("YELLOW", "\033[1m\033[33m")
RESET = get_color("RESET", "\033[0m")

_L1 = ">"
_L2 = "-"

_STATUS_COLORS = {
    "active": "",
    "done": GREEN,
    "error": RED,
    "cancelled": DIM,
}


def get_cli_indent() -> int:
    """Return the configured CLI indentation width (default 4)."""
    val = get_global_config("cli_indent", 4)
    try:
        return max(0, int(val))
    except (TypeError, ValueError):
        return 4


def _term_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 120


def _char_width(ch: str) -> int:
    """Return the display width of a single character (2 for CJK, 1 otherwise)."""
    import unicodedata
    cat = unicodedata.east_asian_width(ch)
    return 2 if cat in ("W", "F") else 1


def _truncate(text: str, width: int) -> str:
    """Truncate visible columns to *width*, ignoring ANSI escapes.

    Accounts for CJK double-width characters.
    When truncation is needed, reserves 3 visible columns for ``...``
    so the ellipsis always fits on the same line.
    """
    visible = 0
    i = 0
    cutoff = max(1, width - 3)
    cut_pos = -1
    while i < len(text):
        if text[i] == "\033":
            j = i + 1
            while j < len(text) and text[j] not in "mGHJK":
                j += 1
            i = j + 1
            continue
        cw = _char_width(text[i])
        visible += cw
        if cut_pos < 0 and visible >= cutoff:
            cut_pos = i + 1
        if visible > width:
            if cut_pos > 0:
                return text[:cut_pos] + f"{RESET}..."
            return text[:i] + f"{RESET}..."
        i += 1
    return text


# ── Public API ──────────────────────────────────────────────────────

def fmt_status(label: str, complement: str = "", dim: str = "",
               style: str = "default", indent: int = -1) -> str:
    """Format a one-line status message.

    Args:
        label: Core phrase — rendered **bold** (and optionally colored).
        complement: Follows the label in default (unformatted) style.
        dim: Follows the complement (or label) in dim style.
        style: ``"default"`` | ``"success"`` | ``"error"``.
        indent: Leading spaces.

    Returns:
        A fully ANSI-formatted string (no trailing newline).

    Examples::

        fmt_status("Saved.")                    # bold only
        fmt_status("Saved.", dim="3 policies")  # bold + dim
        fmt_status("Failed.", complement="Try /setup.", style="error")
    """
    if indent < 0:
        indent = get_cli_indent()
    prefix = " " * indent
    color = {"success": GREEN, "error": RED}.get(style, "")
    parts = [f"{RESET}{prefix}{color}{BOLD}{label}{RESET}"]
    if complement:
        parts.append(f" {complement}")
    if dim:
        parts.append(f" {DIM}{dim}{RESET}")
    raw = "".join(parts)
    return _truncate(raw, _term_width())


def fmt_detail(text: str, indent: int = -1, styled: bool = False,
               wrap: bool = False) -> str:
    """Format a detail/sub-info line (indented, auto-dimmed).

    Args:
        text: The detail content.
        indent: Leading spaces (default: cli_indent * 2).
        styled: If True, skip auto-dimming -- caller provides own ANSI.
        wrap: If True, wrap long lines instead of truncating.

    Returns:
        A fully ANSI-formatted string (no trailing newline).
    """
    if indent < 0:
        indent = get_cli_indent() * 2
    prefix = " " * indent
    if styled:
        raw = f"{RESET}{prefix}{text}"
    else:
        raw = f"{RESET}{prefix}{DIM}{text}{RESET}"
    width = _term_width()
    if wrap:
        return _wrap_stage(raw, width, cont_indent=indent)
    return _truncate(raw, width)


def _visible_width(text: str) -> int:
    """Get visible column width of text, handling ANSI escapes and CJK."""
    w = 0
    i = 0
    while i < len(text):
        if text[i] == "\033":
            j = i + 1
            while j < len(text) and text[j] not in "mGHJK":
                j += 1
            i = j + 1
            continue
        w += _char_width(text[i])
        i += 1
    return w


def _wrap_stage(text: str, width: int, cont_indent: int = 4) -> str:
    """Wrap a stage line to *width* with continuation indentation.

    Splits at exact character boundary (no ``...`` truncation). The first
    line uses the full available *width*; continuation lines are indented
    by *cont_indent* spaces and dimmed.
    """
    if _visible_width(text) <= width:
        return text

    lines = []
    cur_line = ""
    cur_vis = 0
    line_idx = 0
    line_width = width
    i = 0

    while i < len(text):
        if text[i] == "\033":
            j = i + 1
            while j < len(text) and text[j] not in "mGHJK":
                j += 1
            cur_line += text[i:j + 1]
            i = j + 1
            continue

        cw = _char_width(text[i])
        if cur_vis + cw > line_width:
            lines.append(cur_line + RESET)
            line_idx += 1
            line_width = width - cont_indent
            cur_line = RESET + " " * cont_indent + DIM + text[i]
            cur_vis = cont_indent + cw
        else:
            cur_line += text[i]
            cur_vis += cw
        i += 1

    if cur_line:
        lines.append(cur_line)

    return "\n".join(lines)


def fmt_stage(label: str, desc: str = "", status: str = "active",
              depth: int = 1) -> str:
    """Format a stage indicator line: ``> {label} {desc}``.

    The ``>`` marker is colored by *status*; the *label* is always bold;
    *desc* stays in default style.  When the line exceeds terminal width,
    it wraps to continuation lines with proper indentation.

    Args:
        label: Bold stage name (e.g., ``"Starting session..."``).
        desc: Optional description after the label.
        status: ``"active"`` | ``"done"`` | ``"error"`` | ``"cancelled"``.
        depth: 1 = top-level (cli_indent), 2 = nested (cli_indent * 2).

    Returns:
        A fully ANSI-formatted string (no trailing newline), possibly multi-line.
    """
    base = get_cli_indent()
    indent = " " * (base * 2 if depth == 2 else base)
    indicator = _L2 if depth == 2 else _L1
    suffix = f" {desc}" if desc else ""
    color = _STATUS_COLORS.get(status, "")
    if color:
        raw = f"{RESET}{indent}{color}{indicator}{RESET} {BOLD}{label}{RESET}{suffix}"
    else:
        raw = f"{RESET}{indent}{indicator} {BOLD}{label}{RESET}{suffix}"
    width = _term_width()
    cont_indent = len(indent) + 2
    return _wrap_stage(raw, width, cont_indent=cont_indent)


def fmt_warning(text: str, indent: int = -1) -> str:
    """Format a warning line: ``Warning:`` label (yellow+dim) + dimmed text.

    Use for non-critical notices that don't interrupt the pipeline.

    Returns:
        A fully ANSI-formatted string (no trailing newline).
    """
    if indent < 0:
        indent = get_cli_indent()
    prefix = " " * indent
    return _truncate(
        f"{RESET}{prefix}{YELLOW}{DIM}Warning:{RESET} {DIM}{text}{RESET}",
        _term_width())


def fmt_info(text: str, indent: int = -1) -> str:
    """Format an informational notice (fully dimmed, no label).

    Use for supplementary context that the user may or may not need.

    Returns:
        A fully ANSI-formatted string (no trailing newline).
    """
    if indent < 0:
        indent = get_cli_indent()
    prefix = " " * indent
    return _truncate(f"{RESET}{prefix}{DIM}{text}{RESET}", _term_width())
