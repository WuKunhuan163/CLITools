# CLOUDFLARE

Cloudflare infrastructure management via Cloudflare MCP

**Purpose**: Manage DNS, Workers, R2 storage, and other Cloudflare services.

## Capabilities

- dns
- workers
- r2-storage
- analytics
- firewall

## Usage

```bash
CLOUDFLARE status          # Show tool status
CLOUDFLARE config <k> <v>  # Set configuration
CLOUDFLARE setup           # Install dependencies
```

## Environment Variables

- `CLOUDFLARE_API_TOKEN`

## API Key

Obtain credentials at: https://dash.cloudflare.com/profile/api-tokens

## MCP Backend

Package: `mcp-server-cloudflare`
