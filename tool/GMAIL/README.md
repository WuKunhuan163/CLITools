# GMAIL

Gmail email client via the official Gmail REST API with OAuth2 authentication.

## Overview

Read inbox, search emails, send messages, manage labels, and perform
message operations (trash, star, mark read/unread) through the
official Gmail API. CDMCP (Chrome DevTools Protocol) is used only for
the initial OAuth consent flow.

## Prerequisites

1. **Google Cloud Project** with Gmail API enabled
2. **OAuth 2.0 credentials** (Desktop application type)
3. Chrome with `--remote-debugging-port=9222` (optional, for OAuth flow)

## First-Time Setup

```bash
GMAIL setup    # Enter your Google Cloud OAuth client_id and client_secret
GMAIL auth     # Opens browser for consent → paste authorization code
```

## Commands

### Session / Auth

| Command | Description |
|---------|-------------|
| `setup` | Configure OAuth2 client credentials (one-time) |
| `auth` | Run OAuth2 consent flow in browser |
| `status` | Check authentication state and profile |
| `page` | Show current Gmail tab info (if open) |

### Read

| Command | Description |
|---------|-------------|
| `inbox [--limit N]` | List inbox emails with message IDs |
| `labels` | List all Gmail labels with counts |
| `search <query> [--limit N]` | Search emails |
| `read <msg_id>` | Read full email body |
| `message <msg_id>` | Get message metadata (headers, labels) |

### Write

| Command | Description |
|---------|-------------|
| `send <to> [--subject S] [--body B] [--cc C] [--bcc B]` | Send an email |
| `trash <msg_id>` | Move message to Trash |
| `mark-read <msg_id>` | Mark as read |
| `mark-unread <msg_id>` | Mark as unread |
| `star <msg_id>` | Star a message |
| `unstar <msg_id>` | Unstar a message |

### Usage

```bash
GMAIL status
GMAIL inbox --limit 10
GMAIL search "from:github subject:PR" --limit 5
GMAIL read 18e1a2b3c4d5e6f7
GMAIL send user@example.com --subject "Hello" --body "Hi there"
GMAIL trash 18e1a2b3c4d5e6f7
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Architecture

- `logic/gmail_api.py` — OAuth2 token management + Gmail REST API client
- `logic/chrome/api.py` — Thin wrapper; CDMCP used only for auth state check
- `interface/main.py` — Cross-tool interface exports

## Token Storage

- `data/credentials.json` — OAuth client_id and client_secret
- `data/token.json` — Access and refresh tokens (auto-refreshed)
