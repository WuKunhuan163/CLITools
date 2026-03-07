"""Multi-line terminal input widget with placeholder and Ctrl+Enter submit.

Provides a rich input experience for CLI applications:
- Gray placeholder text when buffer is empty
- Enter creates a new line; Ctrl+D (or Ctrl+J) submits
- Backspace on an empty line deletes that line
- After submit, input text is reprinted in a highlight color
- External injection support via a callable check
- Full UTF-8 support including CJK wide characters

Uses raw terminal mode (termios) for character-by-character processing.

Usage:
    from logic.turing.multiline_input import multiline_input

    text = multiline_input(
        prompt=">> ",
        placeholder="Type command here, press Ctrl+D to submit.",
        inject_check=my_inject_fn,
    )

Submit keys (any of):
    Ctrl+D (\\x04)  - standard "end of input"
    Ctrl+J (\\x0a)  - LF / line feed
    Ctrl+Enter      - works on terminals that send CSI u (\\x1b[13;5u)
"""
import sys
import os
import unicodedata
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


def _char_width(ch: str) -> int:
    """Terminal display width of a single character."""
    eaw = unicodedata.east_asian_width(ch)
    return 2 if eaw in ('W', 'F') else 1


def _str_width(s: str) -> int:
    """Terminal display width of a string."""
    return sum(_char_width(c) for c in s)


def _get_terminal_fd():
    """Get a usable terminal file descriptor."""
    try:
        if sys.stdin and sys.stdin.isatty():
            return sys.stdin.fileno()
    except Exception:
        pass
    return None


def _read_utf8_char(fd: int) -> bytes:
    """Read one complete UTF-8 character from a raw file descriptor."""
    b0 = os.read(fd, 1)
    if not b0:
        return b0
    first = b0[0]
    if first < 0x80:
        return b0
    if first & 0xE0 == 0xC0:
        remaining = 1
    elif first & 0xF0 == 0xE0:
        remaining = 2
    elif first & 0xF8 == 0xF0:
        remaining = 3
    else:
        return b0
    extra = os.read(fd, remaining)
    return b0 + extra


def _read_escape_seq(fd: int) -> bytes:
    """Read an escape sequence after the initial \\x1b byte."""
    buf = b''
    for _ in range(8):
        r, _, _ = _select.select([fd], [], [], 0.02)
        if not r:
            break
        b = os.read(fd, 1)
        buf += b
        if len(buf) >= 2 and buf[0:1] == b'[':
            last = buf[-1:]
            if last.isalpha() or last == b'~' or last == b'u':
                break
    return buf


def multiline_input(
    prompt: str = "",
    placeholder: str = "Type here, Ctrl+D to submit.",
    submit_color: str = _SUBMIT_STYLE,
    inject_check: Optional[Callable[[], Optional[str]]] = None,
    poll_interval: float = 0.1,
) -> str:
    """Read multi-line input with placeholder, submit, and injection.

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

    leading = ""
    display_prompt = prompt
    while display_prompt.startswith("\n"):
        leading += "\n"
        display_prompt = display_prompt[1:]

    if leading:
        _raw_write(leading)

    prompt_width = _str_width(display_prompt)

    lines = [""]
    cursor_line = 0
    cursor_col = 0
    showing_placeholder = True

    vis_row = 0
    vis_total = 1

    _show_prompt(display_prompt, placeholder, showing_placeholder)

    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            if inject_check:
                injected = inject_check()
                if injected is not None:
                    _clear_area(vis_row, vis_total)
                    text = injected.strip()
                    _show_submitted(display_prompt, text, submit_color)
                    return text

            ready, _, _ = _select.select([fd], [], [], poll_interval)
            if not ready:
                continue

            ch = _read_utf8_char(fd)
            if not ch:
                _clear_area(vis_row, vis_total)
                return "/quit"

            # Ctrl+C → quit
            if ch == b'\x03':
                _clear_area(vis_row, vis_total)
                _raw_write("\r\n")
                return "/quit"

            # Ctrl+D or Ctrl+J → submit
            if ch in (b'\x04', b'\x0a'):
                text = "\n".join(lines)
                _clear_area(vis_row, vis_total)
                _show_submitted(display_prompt, text, submit_color)
                return text

            # Enter (CR) → new line
            if ch == b'\r':
                if showing_placeholder:
                    showing_placeholder = False
                    _clear_area(vis_row, vis_total)
                    lines = [""]
                    cursor_line = 0
                    cursor_col = 0
                    vis_row = 0
                    vis_total = 1

                tail = lines[cursor_line][cursor_col:]
                lines[cursor_line] = lines[cursor_line][:cursor_col]
                cursor_line += 1
                lines.insert(cursor_line, tail)
                cursor_col = 0
                vis_row, vis_total = _redraw(
                    display_prompt, prompt_width, lines,
                    cursor_line, cursor_col, vis_row, vis_total)
                continue

            # Backspace / Delete
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
                    _clear_area(vis_row, vis_total)
                    _show_prompt(display_prompt, placeholder, True)
                    cursor_line = 0
                    cursor_col = 0
                    vis_row = 0
                    vis_total = 1
                else:
                    vis_row, vis_total = _redraw(
                        display_prompt, prompt_width, lines,
                        cursor_line, cursor_col, vis_row, vis_total)
                continue

            # Escape sequences (arrow keys, Ctrl+Enter via CSI u, etc.)
            if ch == b'\x1b':
                seq = _read_escape_seq(fd)

                # Ctrl+Enter via CSI u encoding: \x1b[13;5u
                if seq == b'[13;5u':
                    text = "\n".join(lines)
                    _clear_area(vis_row, vis_total)
                    _show_submitted(display_prompt, text, submit_color)
                    return text

                if seq == b'[A':
                    if cursor_line > 0:
                        cursor_line -= 1
                        cursor_col = min(cursor_col, len(lines[cursor_line]))
                        vis_row, vis_total = _redraw(
                            display_prompt, prompt_width, lines,
                            cursor_line, cursor_col, vis_row, vis_total)
                elif seq == b'[B':
                    if cursor_line < len(lines) - 1:
                        cursor_line += 1
                        cursor_col = min(cursor_col, len(lines[cursor_line]))
                        vis_row, vis_total = _redraw(
                            display_prompt, prompt_width, lines,
                            cursor_line, cursor_col, vis_row, vis_total)
                elif seq == b'[C':
                    if cursor_col < len(lines[cursor_line]):
                        cursor_col += 1
                        vis_row, vis_total = _redraw(
                            display_prompt, prompt_width, lines,
                            cursor_line, cursor_col, vis_row, vis_total)
                elif seq == b'[D':
                    if cursor_col > 0:
                        cursor_col -= 1
                        vis_row, vis_total = _redraw(
                            display_prompt, prompt_width, lines,
                            cursor_line, cursor_col, vis_row, vis_total)
                continue

            # Regular character input (including multi-byte UTF-8)
            try:
                char = ch.decode('utf-8')
            except UnicodeDecodeError:
                continue
            if not char or ord(char[0]) < 32:
                continue

            if showing_placeholder:
                showing_placeholder = False
                _clear_area(vis_row, vis_total)
                lines = [""]
                cursor_line = 0
                cursor_col = 0
                vis_row = 0
                vis_total = 1

            line = lines[cursor_line]
            lines[cursor_line] = line[:cursor_col] + char + line[cursor_col:]
            cursor_col += len(char)
            vis_row, vis_total = _redraw(
                display_prompt, prompt_width, lines,
                cursor_line, cursor_col, vis_row, vis_total)

    except KeyboardInterrupt:
        _clear_area(vis_row, vis_total)
        _raw_write("\r\n")
        return "/quit"
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


def _clear_area(vis_row: int, vis_total: int):
    """Erase all lines of the current input area.

    vis_row: which row the cursor is on (0-indexed from top of input area)
    vis_total: how many rows are currently displayed
    """
    down = vis_total - 1 - vis_row
    if down > 0:
        _raw_write(f"\033[{down}B")
    for i in range(vis_total):
        _raw_write("\r\033[K")
        if i < vis_total - 1:
            _raw_write("\033[A")


def _redraw(prompt: str, prompt_width: int, lines: list,
            cursor_line: int, cursor_col: int,
            vis_row: int, vis_total: int) -> tuple:
    """Redraw all input lines and position the cursor.

    Returns (new_vis_row, new_vis_total) for tracking.
    """
    total = len(lines)

    if vis_row > 0:
        _raw_write(f"\033[{vis_row}A")

    for i, line in enumerate(lines):
        pfx = prompt if i == 0 else " " * prompt_width
        _raw_write(f"\r\033[K{pfx}{line}")
        if i < total - 1:
            _raw_write("\r\n")

    extra = vis_total - total
    if extra > 0:
        for _ in range(extra):
            _raw_write("\r\n\033[K")
        _raw_write(f"\033[{extra}A")

    up = total - 1 - cursor_line
    if up > 0:
        _raw_write(f"\033[{up}A")

    pfx = prompt if cursor_line == 0 else " " * prompt_width
    col_pos = _str_width(pfx) + _str_width(lines[cursor_line][:cursor_col])
    _raw_write(f"\r\033[{col_pos}C" if col_pos > 0 else "\r")

    return cursor_line, total


def _show_submitted(prompt: str, text: str, color: str):
    """Re-render the submitted text in the highlight color."""
    prompt_width = _str_width(prompt)
    text_lines = text.split("\n") if text else [""]
    for i, line in enumerate(text_lines):
        pfx = prompt if i == 0 else " " * prompt_width
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
