# YUQUE Logic

Yuque (语雀) documentation platform via CDMCP. Uses CDMCP sessions with visual overlays and MCP interaction interfaces.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, page info, element scanning |

## API Functions

| Function | Purpose |
|----------|---------|
| `boot_session()` | Create CDMCP session for yuque.com |
| `get_status()` | Session and auth status |
| `get_page_info()` | Current page metadata |
| `scan_elements()` | Scan DOM elements for interaction |
