# GMAIL Logic — Technical Reference

## Architecture

Standard CDMCP tool with DOM-based operations. Gmail is a single-page app; data is read from rendered DOM rows (inbox) and page title (unread count, email address).

## chrome/api.py

- `find_gmail_tab()`: Matches `mail.google.com`
- `get_inbox()`: Scrapes inbox table rows from DOM
- `get_labels()`: Extracts label list from sidebar
- `search_emails()`: Types into Gmail search bar, reads results
- `send_email()`: Clicks Compose, fills To/Subject/Body, clicks Send

## Gotchas

1. **DOM-dependent**: Gmail frequently changes DOM structure. Selectors may need updating.
2. **Compose flow**: Uses UI automation (button clicks, field fills) — timing-sensitive.
3. **No API access**: Unlike Sentry/Cloudflare, Gmail doesn't expose same-origin REST API. All operations go through DOM.
