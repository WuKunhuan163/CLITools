# LINEAR — Agent Reference

## Quick Start
```
LINEAR status  # Auth and organization state
LINEAR me      # User info (account ID, email, orgs)
LINEAR page    # Current page state
```

## CDP API (`tool.LINEAR.logic.chrome.api`)
- `find_linear_tab()` — Locate the Linear browser tab
- `get_auth_state()` — Check authentication and org presence
- `get_user_info()` — Read user data from localStorage `ApplicationStore`
- `get_page_info()` — Get current page title/URL/pathname

## Notes
- Requires Chrome CDP on port 9222
- Data comes from localStorage (not direct API)
- Linear's GraphQL API at `client-api.linear.app` requires token auth
- User may be authenticated but have no organizations yet
