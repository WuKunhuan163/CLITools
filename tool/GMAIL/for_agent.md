# GMAIL — Agent Reference

## Quick Start
```
GMAIL status                    # Auth state + unread count
GMAIL inbox --limit 10          # List inbox emails
GMAIL labels                    # Sidebar labels
GMAIL search "from:github" --limit 5  # Search emails
```

## CDP API (`tool.GMAIL.logic.chrome.api`)
- `find_gmail_tab()` — Locate the Gmail tab
- `get_auth_state()` — Check auth, email, unread count (from title)
- `get_page_info()` — Get page title/URL/section
- `get_inbox(limit)` — Read inbox rows: from, subject, snippet, date, unread, starred
- `get_labels()` — Read sidebar labels with counts
- `search_emails(query, limit)` — Navigate to search and read results

## Notes
- Requires Chrome CDP on port 9222
- Gmail is authenticated via Google account (auto-login if signed in)
- Data is read from the Gmail SPA DOM (tr.zA rows)
- Search uses hash navigation (`#search/<query>`)
