# WPS — Agent Reference

## Quick Start
```
WPS status    # Check auth state
WPS page      # Current page info
WPS me        # User info (requires auth)
WPS docs      # Recent documents (requires auth)
```

## CDP API (`tool.WPS.logic.chrome.api`)
- `find_wps_tab()` — Locate the WPS/KDocs tab
- `get_auth_state()` — Check authentication state
- `get_page_info()` — Get page title/URL/heading
- `get_user_info()` — Read name, avatar, localStorage data
- `get_recent_docs()` — List recent documents from DOM

## Notes
- Requires Chrome CDP on port 9222
- Searches for tabs matching `kdocs`, `wps.cn`, or `wps.com`
- WPS login supports WeChat, QQ, and email/password

## ToS Compliance

**Status: MEDIUM RISK** -- WPS ToS prohibits unauthorized automated access. Current implementation uses DOM scraping (10 DOM calls). **Migration recommended**: KDocs Developer Platform API should be used instead (100 calls/day test, 200/day production). CDMCP should only be retained for initial login.

**Alternative**: WPS WebOffice Open Platform + KDocs Developer API with registered application.
