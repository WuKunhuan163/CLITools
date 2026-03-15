# ATLASSIAN

Atlassian account management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Atlassian Home session in Chrome to access user profile, notifications, and preferences via the gateway API.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Atlassian tab with authenticated session

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-me` | Show user profile |
| `--mcp-notifications` | List recent notifications |
| `--mcp-preferences` | Show user preferences |

### Usage

```bash
ATLASSIAN --mcp-me
ATLASSIAN --mcp-notifications
ATLASSIAN --mcp-preferences
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
