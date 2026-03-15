# WPS

WPS Office / KDocs tool via Chrome DevTools Protocol.

## Overview

Access WPS user info and recent documents through the authenticated KDocs/WPS web session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- Authenticated WPS/KDocs session at `kdocs.cn` or `wps.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-me` | Show user info (requires auth) |
| `--mcp-docs` | List recent documents (requires auth) |

### Usage

```bash
WPS --mcp-status
WPS --mcp-me
WPS --mcp-docs
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
