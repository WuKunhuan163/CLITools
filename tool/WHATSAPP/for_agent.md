# WHATSAPP - Agent Guide

WhatsApp Business API integration

## Quick Reference

```bash
WHATSAPP status          # Check status and capabilities
WHATSAPP config <k> <v>  # Set API credentials
WHATSAPP setup           # Install dependencies and configure
```

## Capabilities

- send-message
- send-template
- receive-message

Required credentials: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`

## Notes

- Run `WHATSAPP setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/WHATSAPP/data/config.json`.
- Use `WHATSAPP --json` for machine-readable output.
