# LINEAR

Linear product development tool via Chrome DevTools Protocol.

## Overview

Access Linear user info, authentication state, and organization data through the authenticated browser session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Linear session at `linear.app`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication and organization state |
| `--mcp-me` | Show user info (account ID, email, orgs) |
| `--mcp-page` | Show current page state |

### Usage

```bash
LINEAR --mcp-status
LINEAR --mcp-me
LINEAR --mcp-page
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
