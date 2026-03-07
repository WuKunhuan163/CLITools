# INTERCOM

Intercom customer messaging tool via Chrome DevTools Protocol.

## Overview

Access Intercom conversations, contacts, and authentication state through
the authenticated browser session using Chrome CDP.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Intercom session at `app.intercom.com`

## Commands

| Command         | Description                        |
|-----------------|------------------------------------|
| `status`        | Check authentication state         |
| `page`          | Show current page info             |
| `conversations` | List recent conversations          |
| `contacts`      | List contacts                      |

## Usage

```bash
INTERCOM status
INTERCOM page
INTERCOM conversations
INTERCOM contacts
```

## Architecture

- `logic/chrome/api.py` — CDP-based Intercom API functions
- `logic/interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
