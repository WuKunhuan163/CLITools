# INTERCOM - Agent Guide

Customer messaging via Intercom MCP

## Quick Reference

```bash
INTERCOM status          # Check status and capabilities
INTERCOM config <k> <v>  # Set API credentials
INTERCOM setup           # Install dependencies and configure
```

## Capabilities

- conversations
- contacts
- articles
- tickets

Required credentials: `INTERCOM_ACCESS_TOKEN`

## Notes

- Run `INTERCOM setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/INTERCOM/data/config.json`.
- Use `INTERCOM --json` for machine-readable output.
