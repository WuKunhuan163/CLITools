# PAYPAL

PayPal payment integration tool via Chrome DevTools Protocol.

## Overview

Access PayPal account info, balance, and recent activity through the authenticated browser session.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated PayPal session at `paypal.com`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

| Command | Description |
|---------|-------------|
| `--mcp-status` | Check authentication state |
| `--mcp-page` | Show current page info |
| `--mcp-account` | Show account info (requires auth) |
| `--mcp-activity` | Show recent transactions (auth) |

### Usage

```bash
PAYPAL --mcp-status
PAYPAL --mcp-account
PAYPAL --mcp-activity
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |
