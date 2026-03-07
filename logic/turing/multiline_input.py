"""Multi-line terminal input widget with placeholder and Ctrl+Enter submit.

Provides a rich input experience for CLI applications:
- Gray placeholder text when buffer is empty
- Enter creates a new line; Ctrl+Enter submits
- Backspace on an empty line deletes that line
- After submit, input text is reprinted in a highlight color
- External injection support via a callable check

Uses raw terminal mode (termios) for character-by-character processing.

Usage:
    from logic.turing.multiline_input import multiline_input

    text = multiline_input(
        prompt=">> ",
        placeholder="Type command here, press Ctrl+Enter to submit.",
        inject_check=my_inject_fn,
    )
"""
import sys
import os
import select as _select
from typing import Callable, Optional

from logic.config import get_color

try:
    import termios
    import tty
except ImportError:
    termios = None
    tty = None

BOLD = get_color("BOLD")
DIM = get_color("DIM", "\033[2m")
BLUE = get_color("BLUE")
RESET = get_color("RESET")

_PLACEHOLDER_STYLE = DIM
_SUBMIT_STYLE = BLUE


def _get_terminal_fd():
    """Get a usable terminal file descriptor."""
    try:
        if sys.stdin and sys.stdin.isatty():
            return sys.stdin.fileno()
    except Exception:
        pass
    return None


def multiline_input(
    prompt: str = "",
    placeholder: str = "Type command here, press Ctrl+Enter to submit.",
    submit_color: str = _SUBMIT_STYLE,
    inject_check: Optional[Callable[[], Optional[str]]] = None,
    poll_interval: float = 0.1,
) -> str:
    """Read multi-line input with placeholder, Ctrl+Enter submit, and injection.

    Parameters
    ----------
    prompt : str
        Prompt prefix shown on the first line (e.g., ``">> "``).
    placeholder : str
        Gray hint shown when buffer is empty. Disappears on first keystroke.
    submit_color : str
        ANSI color applied to the final text after submit.
    inject_check : callable, optional
        Called periodically; if it returns a non-None string, that string
        is used as the input (external injection). Signature: ``() -> str|None``.
    poll_interval : float
        Seconds between inject_check polls when no key is pending.

    Returns
    -------
    str
        The submitted text (may be multi-line).  Returns ``"/quit"`` on
        Ctrl-C or EOF.
    """
    fd = _get_terminal_fd()
    if fd is None or termios is None:
        return _fallback_input(prompt, inject_check)

    lines = [""]
    cursor_line = 0
    cursor_col = 0
    showing_placeholder = True

    _show_prompt(prompt, placeholder, showing_placeholder)

    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            # Check for injected commands
            if inject_check:
                injected = inject_check()
                if injected is not None:
                    _clear_input_area(prompt, lines, cursor_line, showing_placeholder)
                    text = injected.strip()
                    _show_submitted(prompt, text, submit_color)
                    return text

            ready, _, _ = _select.select([fd], [], [], poll_interval)
            if not ready:
                continue

            ch = os.read(fd, 1)
            if not ch:
                _clear_input_area(prompt, lines, cursor_line, showing_placeholder)
                return "/quit"

            # Ctrl+C
            if ch == b'\x03':
                _clear_input_area(prompt, lines, cursor_line, showing_placeholder)
                _raw_write("\r\n")
                return "/quit"

            # Ctrl+Enter (Ctrl+J = \x0a in raw mode)
            if ch == b'\x0a':
                text = "\n".join(lines)
                _clear_input_area(prompt, lines, cursor_line, showing_placeholder)
                _show_submitted(prompt, text, submit_color)
                return text

            # Enter = new line
            if ch == b'\r':
                if showing_placeholder:
                    showing_placeholder = False
                    _clear_input_area(prompt, lines, cursor_line, True)
                    lines = [""]
                    cursor_line = 0
                    cursor_col = 0

                tail = lines[cursor_line][cursor_col:]
                lines[cursor_line] = lines[cursor_line][:cursor_col]
                cursor_line += 1
                lines.insert(cursor_line, tail)
                cursor_col = 0
                _redraw(prompt, lines, cursor_line, cursor_col)
                continue

            # Backspace
            if ch in (b'\x7f', b'\x08'):
                if showing_placeholder:
                    continue
                if cursor_col > 0:
                    line = lines[cursor_line]
                    lines[cursor_line] = line[:cursor_col - 1] + line[cursor_col:]
                    cursor_col -= 1
                elif cursor_line > 0:
                    prev_len = len(lines[cursor_line - 1])
                    lines[cursor_line - 1] += lines[cursor_line]
                    lines.pop(cursor_line)
                    cursor_line -= 1
                    cursor_col = prev_len

                if lines == [""]:
                    showing_placeholder = True
                    _clear_input_area(prompt, lines, cursor_line, False)
                    _show_prompt(prompt, placeholder, True)
                    cursor_line = 0
                    cursor_col = 0
                else:
                    _redraw(prompt, lines, cursor_line, cursor_col)
                continue

            # Escape sequences (arrows, etc.)
            if ch == b'\x1b':
                seq = b''
                ready2, _, _ = _select.select([fd], [], [], 0.05)
                if ready2:
                    seq = os.read(fd, 2)
                if seq == b'[A':  # Up
                    if cursor_line > 0:
                        cursor_line -= 1
                        cursor_col = min(cursor_col, len(lines[cursor_line]))
                        _redraw(prompt, lines, cursor_line, cursor_col)
                elif seq == b'[B':  # Down
                    if cursor_line < len(lines) - 1:
                        cursor_line += 1
                        cursor_col = min(cursor_col, len(lines[cursor_line]))
                        _redraw(prompt, lines, cursor_line, cursor_col)
                elif seq == b'[C':  # Right
                    if cursor_col < len(lines[cursor_line]):
                        cursor_col += 1
                        _redraw(prompt, lines, cursor_line, cursor_col)
                elif seq == b'[D':  # Left
                    if cursor_col > 0:
                        cursor_col -= 1
                        _redraw(prompt, lines, cursor_line, cursor_col)
                continue

            # Regular character
            try:
                char = ch.decode('utf-8', errors='ignore')
            except Exception:
                continue
            if not char or ord(char) < 32:
                continue

            if showing_placeholder:
                showing_placeholder = False
                _clear_input_area(prompt, lines, cursor_line, True)
                lines = [""]
                cursor_line = 0
                cursor_col = 0

            line = lines[cursor_line]
            lines[cursor_line] = line[:cursor_col] + char + line[cursor_col:]
            cursor_col += 1
            _redraw(prompt, lines, cursor_line, cursor_col)

    except (EOFError, OSError):
        return "/quit"
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)


def _raw_write(s: str):
    """Write directly to stdout fd, bypassing Python buffering."""
    os.write(sys.stdout.fileno(), s.encode('utf-8'))


def _show_prompt(prompt: str, placeholder: str, show_ph: bool):
    """Render the initial prompt line with optional placeholder."""
    if show_ph:
        _raw_write(f"\r{prompt}{_PLACEHOLDER_STYLE}{placeholder}{RESET}")
    else:
        _raw_write(f"\r{prompt}")


def _clear_input_area(prompt: str, lines: list, cursor_line: int,
                       had_placeholder: bool):
    """Erase all lines of the current input area."""
    total_lines = 1 if had_placeholder else len(lines)
    if total_lines > 1:
        _raw_write(f"\033[{total_lines - 1}B")
    for i in range(total_lines):
        _raw_write(f"\r\033[K")
        if i < total_lines - 1:
            _raw_write(f"\033[A")


def _redraw(prompt: str, lines: list, cursor_line: int, cursor_col: int):
    """Redraw all input lines and position the cursor."""
    total = len(lines)

    _raw_write(f"\033[{total}A" if total > 1 else "")
    for i, line in enumerate(lines):
        pfx = prompt if i == 0 else " " * len(prompt)
        _raw_write(f"\r\033[K{pfx}{line}")
        if i < total - 1:
            _raw_write("\r\n")

    lines_below = total - 1 - cursor_line
    if lines_below > 0:
        _raw_write(f"\033[{lines_below}A")
    pfx = prompt if cursor_line == 0 else " " * len(prompt)
    col_pos = len(pfx) + cursor_col
    _raw_write(f"\r\033[{col_pos}C" if col_pos > 0 else "\r")


def _show_submitted(prompt: str, text: str, color: str):
    """Re-render the submitted text in the highlight color."""
    text_lines = text.split("\n") if text else [""]
    for i, line in enumerate(text_lines):
        pfx = prompt if i == 0 else " " * len(prompt)
        _raw_write(f"\r\033[K{pfx}{color}{line}{RESET}")
        if i < len(text_lines) - 1:
            _raw_write("\r\n")
    _raw_write("\r\n")


def _fallback_input(prompt: str,
                    inject_check: Optional[Callable] = None) -> str:
    """Non-raw fallback for environments without termios."""
    try:
        if inject_check:
            injected = inject_check()
            if injected is not None:
                return injected.strip()
        line = input(prompt)
        return line
    except (EOFError, KeyboardInterrupt):
        return "/quit"
