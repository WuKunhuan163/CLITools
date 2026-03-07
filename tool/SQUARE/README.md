# SQUARE

Square business platform tool via Chrome DevTools Protocol.

## Overview

Access Square dashboard info, merchant data, and payment overview through the authenticated browser session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Square session at `squareup.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-dashboard` | Show dashboard summary (auth) |

### Usage

```bash
SQUARE --mcp-status
SQUARE --mcp-page
SQUARE --mcp-dashboard
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
