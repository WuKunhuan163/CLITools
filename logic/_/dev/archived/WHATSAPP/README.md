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

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check link/authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-chats` | List visible chats (requires link) |
| `--mcp-profile` | Show profile info (requires link) |
| `--mcp-search <query>` | Search contacts/chats |
| `--mcp-send <number> <message>` | Send a message to a phone number |

### Usage

```bash
WHATSAPP --mcp-status
WHATSAPP --mcp-chats
WHATSAPP --mcp-profile
WHATSAPP --mcp-search "John"
WHATSAPP --mcp-send "+1234567890" "Hello!"
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Architecture

- `logic/chrome/api.py` -- CDP-based WhatsApp Web functions
- `interface/main.py` -- Cross-tool interface exports
