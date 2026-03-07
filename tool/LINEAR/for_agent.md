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

## ToS Compliance

**Status: COMPLIANT** -- This tool only reads from `localStorage` (ApplicationStore) and `document.cookie` for auth state and user info. No DOM manipulation, UI clicking, or form filling is performed. This is equivalent to reading session tokens from the browser context, which is acceptable for the auth/bootstrap flow. For future data operations (issues, projects), the Linear GraphQL API at `api.linear.app/graphql` should be used.
