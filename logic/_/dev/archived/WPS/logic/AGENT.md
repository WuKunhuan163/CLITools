# WPS Logic — Technical Reference

## Architecture

Standard CDMCP tool pattern. Tab discovery via `find_wps_tab()` matching `kdocs.cn` or `wps.com`.

## chrome/api.py

- `find_wps_tab()`: Searches for KDocs/WPS tabs
- `get_auth_state()`: Cookie-based auth check
- `get_user_info()`: Account name, email, membership
- `get_recent_docs()`: Document list from authenticated session

## Gotchas

1. **Dual domain**: WPS uses both `kdocs.cn` (China) and `wps.com` (international). Tab discovery checks both.
2. **Requires auth**: All data operations need an authenticated session.
