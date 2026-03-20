# GMAIL — Agent Reference

## Architecture

This tool uses the **official Gmail REST API** (https://gmail.googleapis.com/gmail/v1/)
with OAuth2 authentication. CDMCP (Chrome DevTools Protocol) is used **only** for
checking if a Gmail tab is open and for the initial OAuth consent flow.

All data operations (read inbox, send email, search, trash, labels, etc.) go through
the Gmail API via standard HTTP requests with Bearer tokens.

## Setup (One-Time)

```bash
GMAIL setup      # Enter Google Cloud OAuth client_id and client_secret
GMAIL auth       # Opens browser → user approves → paste authorization code
```

**Prerequisites:**
1. Google Cloud Console project with Gmail API enabled
2. OAuth 2.0 credentials (Desktop application type)
3. Add `urn:ietf:wg:oauth:2.0:oob` as an authorized redirect URI

## Quick Start

```bash
GMAIL status                           # Auth state + profile
GMAIL inbox --limit 10                 # List inbox emails (returns message IDs)
GMAIL labels                           # List all labels with counts
GMAIL search "from:github" --limit 5   # Search emails
GMAIL read <msg_id>                    # Read full email body
GMAIL message <msg_id>                 # Get message metadata
GMAIL send user@example.com --subject "Hello" --body "Hi there"
GMAIL trash <msg_id>                   # Move to Trash
GMAIL mark-read <msg_id>              # Mark as read
GMAIL mark-unread <msg_id>            # Mark as unread
GMAIL star <msg_id>                    # Star a message
GMAIL unstar <msg_id>                  # Unstar a message
```

## API Reference (`tool.GMAIL.logic.gmail_api`)

### Auth & Token Management
- `has_credentials()` → bool — Check if OAuth credentials are configured
- `has_token()` → bool — Check if an access token exists
- `get_auth_url()` → str — Generate OAuth2 consent URL
- `exchange_code(code)` → dict — Exchange auth code for tokens
- `refresh_access_token()` → dict — Refresh expired access token
- `save_credentials(client_id, client_secret)` — Store OAuth credentials

### Read Operations
- `get_profile()` → dict — User profile (email, messagesTotal)
- `get_inbox(limit)` → dict — Inbox emails with from/subject/date/snippet/unread/starred
- `list_labels()` → dict — All labels
- `get_label(label_id)` → dict — Label details with message/thread counts
- `list_messages(query, label_ids, max_results, page_token)` → dict — Message ID list
- `get_message(msg_id, fmt)` → dict — Message metadata or full content
- `get_message_body(msg_id)` → dict — Decoded plain-text body
- `search_emails(query, limit)` → dict — Search with summaries
- `list_threads(query, max_results, page_token)` → dict — Thread list
- `get_thread(thread_id)` → dict — Full thread with messages

### Write Operations
- `send_email(to, subject, body, cc, bcc)` → dict — Send email via API
- `trash_message(msg_id)` → dict — Move to Trash
- `untrash_message(msg_id)` → dict — Remove from Trash
- `mark_as_read(msg_id)` → dict — Remove UNREAD label
- `mark_as_unread(msg_id)` → dict — Add UNREAD label
- `star_message(msg_id)` → dict — Add STARRED label
- `unstar_message(msg_id)` → dict — Remove STARRED label

### CDMCP (Session Only)
- `find_gmail_tab()` → dict — Find Gmail tab in Chrome
- `get_auth_state()` → dict — Combined API + browser auth check
- `get_page_info()` → dict — Gmail tab URL/title/section (read-only DOM)

## Key Changes from DOM-Based Version

| Before (DOM scraping) | After (Gmail API) |
|---|---|
| `delete_email(index)` — row index | `trash <msg_id>` — message ID |
| 43 DOM calls (querySelector, click, insertText) | 0 DOM manipulation |
| Fragile CSS selectors (`tr.zA`, `.yW .bA4`) | Stable REST API endpoints |
| `search_emails` navigated hash + scraped DOM | `search_emails` uses Gmail `q` parameter |
| `send_email` filled compose window + clicked Send | `send_email` uses `messages/send` endpoint |

## Token Storage

- Credentials: `tool/GMAIL/data/credentials.json` (client_id, client_secret)
- Tokens: `tool/GMAIL/data/token.json` (access_token, refresh_token)
- Auto-refresh: tokens are refreshed automatically when expired

## ToS Compliance

**Status: COMPLIANT** — This tool now uses the official Gmail REST API
(https://gmail.googleapis.com/gmail/v1/) with proper OAuth2 authorization.
CDMCP is retained only for session management (checking if Gmail tab is open)
and the OAuth consent flow (user manually approves in browser).
No DOM scraping, UI clicking, or automated form filling is performed.

**Previous status**: HIGH RISK (43 DOM calls, UI automation).
**Migration date**: 2026-03-06.
