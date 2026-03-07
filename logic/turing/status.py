"""Reusable terminal status-message formatters.

Enforces the minimal-emphasis rule: bold/color only on the core phrase,
complements and details in default or dim style.  All functions return
formatted strings — the caller decides when to print or write them.

Usage::

    from logic.turing.status import fmt_status, fmt_detail, fmt_stage

    print(fmt_status("Saved.", dim="3 policies"))
    print(fmt_detail("Session be58ac60 is ready."))
    print(fmt_stage("Starting session...", status="active"))
"""

from __future__ import annotations

import os
import shutil
from typing import Optional

from logic.config import get_color

BOLD = get_color("BOLD", "\033[1m")
DIM = get_color("DIM", "\033[2m")
GREEN = get_color("GREEN_NORMAL", "\033[32m")
RED = get_color("RED_NORMAL", "\033[31m")
RESET = get_color("RESET", "\033[0m")

_L1 = ">"
_L2 = "-"

_STATUS_COLORS = {
    "active": "",
    "done": GREEN,
    "error": RED,
    "cancelled": DIM,
}


def _term_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 120


def _truncate(text: str, width: int) -> str:
    """Truncate visible characters to *width*, ignoring ANSI escapes."""
    visible = 0
    i = 0
    while i < len(text):
        if text[i] == "\033":
            j = i + 1
            while j < len(text) and text[j] not in "mGHJK":
                j += 1
            i = j + 1
            continue
        visible += 1
        if visible > width:
            return text[:i] + "..."
        i += 1
    return text


# ── Public API ──────────────────────────────────────────────────────

def fmt_status(label: str, complement: str = "", dim: str = "",
               style: str = "default", indent: int = 2) -> str:
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
    prefix = " " * indent
    color = {"success": GREEN, "error": RED}.get(style, "")
    parts = [f"{prefix}{color}{BOLD}{label}{RESET}"]
    if complement:
        parts.append(f" {complement}")
    if dim:
        parts.append(f" {DIM}{dim}{RESET}")
    raw = "".join(parts)
    return _truncate(raw, _term_width())


def fmt_detail(text: str, indent: int = 4, styled: bool = False) -> str:
    """Format a detail/sub-info line (indented, auto-dimmed).

    Args:
        text: The detail content.
        indent: Leading spaces (default 4 = 2 for parent + 2 for nesting).
        styled: If True, skip auto-dimming — caller provides own ANSI.

    Returns:
        A fully ANSI-formatted string (no trailing newline).
    """
    prefix = " " * indent
    if styled:
        return _truncate(f"{prefix}{text}", _term_width())
    return _truncate(f"{prefix}{DIM}{text}{RESET}", _term_width())


def fmt_stage(label: str, desc: str = "", status: str = "active",
              depth: int = 1) -> str:
    """Format a stage indicator line: ``> {label} {desc}``.

    The ``>`` marker is colored by *status*; the *label* is always bold;
    *desc* stays in default style.

    Args:
        label: Bold stage name (e.g., ``"Starting session..."``).
        desc: Optional description after the label.
        status: ``"active"`` | ``"done"`` | ``"error"`` | ``"cancelled"``.
        depth: 1 = top-level (2-space indent), 2 = nested (4-space indent).

    Returns:
        A fully ANSI-formatted string (no trailing newline).
    """
    indent = "    " if depth == 2 else "  "
    indicator = _L2 if depth == 2 else _L1
    suffix = f" {desc}" if desc else ""
    color = _STATUS_COLORS.get(status, "")
    if color:
        raw = f"{indent}{color}{indicator}{RESET} {BOLD}{label}{RESET}{suffix}"
    else:
        raw = f"{indent}{indicator} {BOLD}{label}{RESET}{suffix}"
    return _truncate(raw, _term_width())
