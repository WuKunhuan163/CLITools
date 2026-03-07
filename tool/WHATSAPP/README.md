# WHATSAPP

WhatsApp Web messaging tool via Chrome DevTools Protocol.

## Overview

Access WhatsApp chats, contacts, and profile through the linked
WhatsApp Web session using Chrome CDP. Requires scanning the QR code
with your phone to establish the link.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- WhatsApp Web tab open at `web.whatsapp.com`
- Phone linked via QR code scan

## Commands

| Command   | Description                              |
|-----------|------------------------------------------|
| `status`  | Check link/authentication state          |
| `page`    | Show current page info                   |
| `chats`   | List visible chats (requires link)       |
| `profile` | Show profile info (requires link)        |

## Usage

```bash
WHATSAPP status
WHATSAPP chats
WHATSAPP profile
```

## Architecture

- `logic/chrome/api.py` — CDP-based WhatsApp Web functions
- `logic/interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
