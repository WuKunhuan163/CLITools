# GMAIL

Gmail email client tool via Chrome DevTools Protocol.

## Overview

Read inbox emails, search messages, and list labels through the
authenticated Gmail session using Chrome CDP. Gmail's SPA DOM is
read directly to extract email metadata (from, subject, date,
unread/starred status).

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- Authenticated Gmail session at `mail.google.com`

## Commands

| Command                     | Description                         |
|-----------------------------|-------------------------------------|
| `status`                    | Check auth state and unread count   |
| `page`                      | Show current page/section info      |
| `inbox [--limit N]`         | List inbox emails (requires auth)   |
| `labels`                    | List sidebar labels (requires auth) |
| `search <query> [--limit N]`| Search emails (requires auth)       |

## Usage

```bash
GMAIL status
GMAIL inbox --limit 10
GMAIL labels
GMAIL search "from:github subject:PR"
```

## Architecture

- `logic/chrome/api.py` — CDP-based Gmail functions (DOM reading, search)
- `interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
