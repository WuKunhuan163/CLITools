# GMAIL

Gmail email client tool via Chrome DevTools Protocol.

## Overview

Read inbox emails, search messages, and list labels through the
authenticated Gmail session using Chrome CDP.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- Authenticated Gmail session at `mail.google.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check auth state and unread count |
| `--mcp-page` | Show current page/section info |
| `--mcp-inbox [--limit N]` | List inbox emails (requires auth) |
| `--mcp-labels` | List sidebar labels (requires auth) |
| `--mcp-search <query> [--limit N]` | Search emails (requires auth) |
| `--mcp-send <to> <subject> <body>` | Compose and send email |

### Usage

```bash
GMAIL --mcp-status
GMAIL --mcp-inbox --limit 10
GMAIL --mcp-labels
GMAIL --mcp-search "from:github subject:PR"
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Architecture

- `logic/chrome/api.py` -- CDP-based Gmail functions (DOM reading, search)
- `interface/main.py` -- Cross-tool interface exports
