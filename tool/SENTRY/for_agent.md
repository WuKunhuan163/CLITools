# SENTRY — Agent Reference

## Quick Start
```
SENTRY status               # Check auth state
SENTRY page                 # Current page info
SENTRY orgs                 # List organizations
SENTRY projects <org>       # List projects
SENTRY issues <org>         # List issues
```

## CDP API (`tool.SENTRY.logic.chrome.api`)
- `find_sentry_tab()` — Locate the Sentry browser tab
- `get_auth_state()` — Check authentication state
- `get_page_info()` — Get current page title/URL
- `get_organizations()` — List orgs via `/api/0/organizations/`
- `get_projects(org)` — List projects via same-origin API
- `get_issues(org, project)` — List issues via same-origin API

## Notes
- Requires Chrome CDP on port 9222
- Sentry has same-origin REST API (`/api/0/`) that works with session cookies
- Supports Google and GitHub sign-in
