# KLING

Kling AI video generation tool via Chrome DevTools Protocol.

## Overview

Access Kling AI user info, credit points, and generation history through the authenticated browser session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Kling AI session at `app.klingai.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-me` | Show user info (ID, name, email) |
| `--mcp-points` | Show credit points balance |
| `--mcp-page` | Show current page state |
| `--mcp-history` | Show recent generation history |

### Usage

```bash
KLING --mcp-me
KLING --mcp-points
KLING --mcp-history
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
