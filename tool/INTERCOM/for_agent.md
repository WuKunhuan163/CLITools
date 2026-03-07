# INTERCOM — Agent Reference

## Quick Start
```
INTERCOM status        # Check auth state
INTERCOM page          # Current page info
INTERCOM conversations # List conversations (requires auth)
INTERCOM contacts      # List contacts (requires auth)
```

## CDP API (`tool.INTERCOM.logic.chrome.api`)
- `find_intercom_tab()` — Locate the Intercom browser tab
- `get_auth_state()` — Check if user is authenticated
- `get_page_info()` — Get current page title/URL/heading
- `get_conversations(limit)` — List conversations (authenticated)
- `get_contacts(limit)` — List contacts (authenticated)

## Notes
- Requires Chrome CDP on port 9222
- The user may be on a sign-up page (not yet authenticated)
- Read operations work; write operations require full authentication
