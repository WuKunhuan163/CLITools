# SQUARE — Agent Reference

## Quick Start
```
SQUARE status     # Check auth state
SQUARE page       # Current page info
SQUARE dashboard  # Dashboard summary (requires auth)
```

## CDP API (`tool.SQUARE.logic.chrome.api`)
- `find_square_tab()` — Locate the Square browser tab
- `get_auth_state()` — Check if user is authenticated
- `get_page_info()` — Get current page title/URL
- `get_dashboard_info()` — Read merchant/balance from dashboard DOM

## Notes
- Requires Chrome CDP on port 9222
- Square uses email/phone login and passkey (no Google sign-in)
- Dashboard command requires authenticated session

## ToS Compliance

**Status: MEDIUM RISK** -- Square Developer Terms restrict non-API access. Current implementation uses DOM scraping (7 DOM calls). **Migration recommended**: Use Square Developer API with OAuth. CDMCP should only be retained for initial login.

**Alternative**: Square Developer API with OAuth credentials.
