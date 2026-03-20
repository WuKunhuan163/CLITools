# CLOUDFLARE

Cloudflare account management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Cloudflare dashboard session in Chrome to perform API operations without requiring a separate API token.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Cloudflare dashboard tab (`dash.cloudflare.com`) with authenticated session

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-user` | Show authenticated user info |
| `--mcp-account` | Show account info |
| `--mcp-zones` | List DNS zones |
| `--mcp-dns <zone_id>` | List DNS records for a zone |
| `--mcp-workers` | List Workers scripts |
| `--mcp-pages` | List Pages projects |
| `--mcp-kv` | List KV namespaces |

### Usage

```bash
CLOUDFLARE --mcp-user
CLOUDFLARE --mcp-zones
CLOUDFLARE --mcp-dns <zone_id>
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
