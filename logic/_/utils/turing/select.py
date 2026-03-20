"""Interactive terminal input components.

Reusable blueprints for terminal CLI interactions:
- select_menu: Arrow-key list selector (up/down/Enter).
- select_horizontal: Inline horizontal selector (left/right/Enter).
- read_masked: Hidden input with dim * feedback.
- erase_lines: Clear N lines above cursor (for step rollback in wizards).

Uses the shared KeyboardSuppressor for terminal state management.

Usage:
    from logic._.utils.turing.select import select_menu, select_horizontal, read_masked, erase_lines

    choice = select_menu("Select a provider:", [...])
    policy = select_horizontal("Allow?", ["Run Everytime", "Run Once", "Reject"])
    key = read_masked("Enter API key:")
    erase_lines(3)  # undo 3 lines of output
"""
import sys
import os
import tty
import termios
from typing import List, Dict, Any, Optional

from pathlib import Path

from logic._.config import get_color
from logic._.lang.utils import get_translation
from logic._.utils.turing.terminal.keyboard import get_global_suppressor

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent)

def _(key: str, default: str, **kwargs) -> str:
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

BOLD = get_color("BOLD")
DIM = get_color("DIM", "\033[2m")
CYAN = get_color("CYAN", "\033[36m")
GREEN = get_color("GREEN")
BLUE = get_color("BLUE")
RESET = get_color("RESET")


def _read_key() -> str:
    """Read a single keypress from stdin (raw mode)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)
        if ch == b'\x03':
            return 'ctrl-c'
        if ch == b'\r' or ch == b'\n':
            return 'enter'
        if ch == b'\x1b':
            seq = os.read(fd, 2)
            if seq == b'[A':
                return 'up'
            if seq == b'[B':
                return 'down'
            if seq == b'[C':
                return 'right'
            if seq == b'[D':
                return 'left'
            return 'esc'
        return ch.decode('utf-8', errors='ignore')
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def select_menu(
    title: str,
    options: List[Dict[str, Any]],
    indent: str = "  ",
    selected_index: int = 0,
) -> Optional[Dict[str, Any]]:
    """Display an interactive arrow-key menu and return the selected option.

    Args:
        title: Header text displayed above the options.
        options: List of dicts, each with at least "label" and "value" keys.
                 Optional "detail" key for extra info shown dimmed.
        indent: Indentation prefix for each line.
        selected_index: Initial selection index.

    Returns:
        The selected option dict, or None if cancelled (Ctrl+C / Esc).
    """
    if not options:
        return None

    cursor = max(0, min(selected_index, len(options) - 1))
    num_lines = len(options) + 1

    def render():
        sys.stdout.write(f"{indent}{BOLD}{title}{RESET}\n")
        for i, opt in enumerate(options):
            label = opt.get("label", str(opt.get("value", "")))
            detail = opt.get("detail", "")
            if i == cursor:
                line = f"{indent}  {CYAN}*{RESET} {CYAN}{BOLD}{label}{RESET}"
            else:
                line = f"{indent}    {label}"
            if detail:
                line += f" {DIM}-- {detail}{RESET}"
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def clear():
        for _ in range(num_lines):
            sys.stdout.write("\033[A\033[K")
        sys.stdout.flush()

    if not sys.stdin.isatty():
        render()
        return options[cursor] if options else None

    suppressor = get_global_suppressor()
    suppressor.start()

    try:
        render()

        while True:
            key = _read_key()
            if key == 'up':
                cursor = (cursor - 1) % len(options)
            elif key == 'down':
                cursor = (cursor + 1) % len(options)
            elif key == 'enter':
                clear()
                selected = options[cursor]
                label = selected.get("label", str(selected.get("value", "")))
                sys.stdout.write(f"{indent}{title} {label}\n")
                sys.stdout.flush()
                return selected
            elif key == 'esc':
                clear()
                sys.stdout.flush()
                return None
            elif key == 'ctrl-c':
                clear()
                sys.stdout.write(f"{indent}{DIM}{_('select_cancelled', 'Cancelled.')}{RESET}\n")
                sys.stdout.flush()
                return None
            else:
                continue

            clear()
            render()
    finally:
        suppressor.stop()


RED = get_color("RED")
YELLOW = get_color("YELLOW")


def select_horizontal(
    prompt: str,
    options: List[str],
    default_index: int = 0,
    indent: str = "    ",
    timeout: float = 0,
) -> Optional[int]:
    """Display an inline horizontal selector (left/right/Enter).

    Shows options on one line: prompt  [*Option A]  Option B  Option C
    The selected option is highlighted with [*...] brackets.

    Args:
        prompt: Question or label text.
        options: List of option labels.
        default_index: Index of the pre-selected option.
        indent: Indentation prefix.
        timeout: Seconds to wait before auto-selecting default (0 = no timeout).

    Returns:
        The index of the selected option, or None if cancelled.
    """
    if not options:
        return None

    cursor = max(0, min(default_index, len(options) - 1))

    def render():
        parts = []
        for i, opt in enumerate(options):
            if i == cursor:
                parts.append(f"{CYAN}{BOLD}[{opt}]{RESET}")
            else:
                parts.append(f"{DIM}{opt}{RESET}")
        line = f"{indent}{prompt}  {'  '.join(parts)}"
        sys.stdout.write(f"\r\033[K{line}")
        sys.stdout.flush()

    if not sys.stdin.isatty():
        render()
        sys.stdout.write("\n")
        return cursor

    suppressor = get_global_suppressor()
    suppressor.start()

    try:
        render()

        deadline = (__import__("time").time() + timeout) if timeout > 0 else 0

        while True:
            if deadline and __import__("time").time() >= deadline:
                sys.stdout.write(f"\r\033[K{indent}{prompt}  {options[cursor]}\n")
                sys.stdout.flush()
                return cursor

            import select as _sel
            if deadline:
                remaining = max(0.05, deadline - __import__("time").time())
                ready, _, _ = _sel.select([sys.stdin], [], [], min(remaining, 0.1))
                if not ready:
                    continue
            key = _read_key()

            if key == 'left':
                cursor = (cursor - 1) % len(options)
            elif key == 'right':
                cursor = (cursor + 1) % len(options)
            elif key == 'enter':
                sys.stdout.write(
                    f"\r\033[K{indent}{prompt}  {options[cursor]}\n")
                sys.stdout.flush()
                return cursor
            elif key in ('esc', 'ctrl-c'):
                sys.stdout.write(f"\r\033[K{indent}{DIM}{_('select_cancelled', 'Cancelled.')}{RESET}\n")
                sys.stdout.flush()
                return None
            else:
                continue

            render()
    finally:
        suppressor.stop()


def read_masked(
    prompt: str = "Enter value:",
    mask_char: str = "*",
    indent: str = "  ",
    allow_empty: bool = False,
) -> Optional[str]:
    """Read input with dim masked feedback (e.g. dim * per character).

    Args:
        prompt: The prompt text to display.
        mask_char: Character to echo for each typed character.
        indent: Indentation prefix.
        allow_empty: If True, accept empty input (Enter with nothing typed).
                     If False, ignore Enter when buffer is empty.

    Returns:
        The entered string, or None if cancelled (Ctrl+C / Esc).
    """
    if not sys.stdin.isatty():
        try:
            return input(f"{indent}{prompt} ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

    sys.stdout.write(f"{indent}{prompt} ")
    sys.stdout.flush()

    buf = []
    fd = sys.stdin.fileno()

    while True:
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = os.read(fd, 1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        if ch == b'\x03' or ch == b'\x1b':
            sys.stdout.write("\n")
            sys.stdout.flush()
            return None
        if ch == b'\r' or ch == b'\n':
            if buf or allow_empty:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return "".join(buf)
            continue
        if ch in (b'\x7f', b'\x08'):
            if buf:
                buf.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue

        try:
            char = ch.decode('utf-8', errors='ignore')
        except Exception:
            continue
        if char and char.isprintable():
            buf.append(char)
            sys.stdout.write(f"{DIM}{mask_char}{RESET}")
            sys.stdout.flush()


def erase_lines(count: int):
    """Erase *count* lines above the cursor (inclusive of current line).

    Moves the cursor up and clears each line. Useful for rolling back
    a wizard step or undoing transient output in multi-step flows.

    Args:
        count: Number of lines to erase (must be >= 0).
    """
    for _ in range(count):
        sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()
