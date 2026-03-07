# logic/turing/display — Agent Reference

## manager.py

Key functions:
- `truncate_to_width(text, max_width)`: Truncate to visible width with ellipsis and ANSI reset
- `_get_configured_width()`: Returns terminal width from config or `shutil.get_terminal_size()`
- `MultiLineManager`: Coordinates multi-line erasable output across Turing stages

Uses `unicodedata` for CJK character width calculation. Handles ANSI escape codes transparently.

## Gotchas

1. **Global lock**: Multi-line output uses a threading lock — do not call display functions from signal handlers.
2. **RTL mode**: `get_rtl_mode()` from `logic.utils` controls right-to-left text support.
