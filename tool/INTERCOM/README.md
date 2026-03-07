# INTERCOM

Intercom customer messaging tool via Chrome DevTools Protocol.

## Overview

Access Intercom conversations, contacts, and authentication state through the authenticated browser session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Intercom session at `app.intercom.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-conversations` | List recent conversations |
| `--mcp-contacts` | List contacts |

### Usage

```bash
INTERCOM --mcp-status
INTERCOM --mcp-page
INTERCOM --mcp-conversations
INTERCOM --mcp-contacts
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
