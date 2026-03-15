# SENTRY

Sentry error monitoring tool via Chrome DevTools Protocol.

## Overview

Access Sentry organizations, projects, and issues through the authenticated browser session using same-origin REST API.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Sentry session at `sentry.io`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-orgs` | List organizations (requires auth) |
| `--mcp-projects <org>` | List projects (requires auth) |
| `--mcp-issues <org>` | List issues (requires auth) |

### Usage

```bash
SENTRY --mcp-status
SENTRY --mcp-orgs
SENTRY --mcp-projects my-org
SENTRY --mcp-issues my-org --project my-project
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
