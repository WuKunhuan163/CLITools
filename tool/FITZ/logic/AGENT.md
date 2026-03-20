# FITZ Logic — Technical Reference

## pdf/wrapper.py — FitzWrapper

Suppresses unwanted mupdf C-library stderr output using low-level `os.dup2`:
- `_suppress_stderr()`: Redirects fd 2 to /dev/null
- `_restore_stderr()`: Restores original fd 2
- Wraps fitz operations with automatic suppression/restoration

Also sets `fitz.TOOLS.mupdf_display_errors(False)` at import time.

## Gotchas

1. **Low-level fd manipulation**: Uses `os.dup2` — not thread-safe. Don't use in concurrent contexts.
2. **Template tool**: FITZ serves as a development template/showcase. Check `tool.json` for "Showcase tool development guidelines".
