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
