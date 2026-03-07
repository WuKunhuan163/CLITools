# WPS - Agent Guide

WPS Office document integration

## Quick Reference

```bash
WPS status          # Check status and capabilities
WPS config <k> <v>  # Set API credentials
WPS setup           # Install dependencies and configure
```

## Capabilities

- create-document
- edit-document
- convert-format

Required credentials: `WPS_APP_ID`, `WPS_APP_KEY`

## Notes

- Run `WPS setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/WPS/data/config.json`.
- Use `WPS --json` for machine-readable output.
