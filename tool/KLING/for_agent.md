# KLING — Agent Reference

## Quick Start
```
KLING me      # User info (ID, name, email)
KLING points  # Credit points balance
KLING page    # Current page state
KLING history # Generation history from DOM
```

## CDP API (`tool.KLING.logic.chrome.api`)
- `find_kling_tab()` — Locate the Kling AI browser tab
- `get_user_info()` — Read user data from localStorage
- `get_points()` — Read credit points from DOM
- `get_page_info()` — Get current page title/URL
- `get_generation_history()` — Read visible generation items from DOM

## Notes
- Requires Chrome CDP on port 9222
- Data comes from localStorage and DOM (not direct API)
- Kling's API gateway (`api-app-global.klingai.com`) blocks cross-origin fetch
- Navigate to Assets page before calling `history` command
