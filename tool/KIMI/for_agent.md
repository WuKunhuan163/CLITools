# KIMI - Agent Guide

Kimi AI assistant API integration

## Quick Reference

```bash
KIMI status          # Check status and capabilities
KIMI config <k> <v>  # Set API credentials
KIMI setup           # Install dependencies and configure
```

## Capabilities

- chat
- long-context
- document-analysis

Required credentials: `KIMI_API_KEY`

## Notes

- Run `KIMI setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/KIMI/data/config.json`.
- Use `KIMI --json` for machine-readable output.
