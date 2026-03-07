# CLOUDFLARE - Agent Guide

Cloudflare infrastructure management via Cloudflare MCP

## Quick Reference

```bash
CLOUDFLARE status          # Check status and capabilities
CLOUDFLARE config <k> <v>  # Set API credentials
CLOUDFLARE setup           # Install dependencies and configure
```

## Capabilities

- dns
- workers
- r2-storage
- analytics
- firewall

Required credentials: `CLOUDFLARE_API_TOKEN`

## Notes

- Run `CLOUDFLARE setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/CLOUDFLARE/data/config.json`.
- Use `CLOUDFLARE --json` for machine-readable output.

## ToS Compliance

**Status: COMPLIANT** -- This tool uses Cloudflare API v4 via in-page `fetch()` from the authenticated browser session (`_cf_api()` helper). CDMCP is only used for session management and authentication. All data operations go through Cloudflare's official REST API at `api.cloudflare.com`. Cloudflare provides comprehensive API documentation and actively encourages API usage over dashboard automation.
