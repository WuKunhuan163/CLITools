# LINEAR - Agent Guide

Product development system via Linear MCP

## Quick Reference

```bash
LINEAR status          # Check status and capabilities
LINEAR config <k> <v>  # Set API credentials
LINEAR setup           # Install dependencies and configure
```

## Capabilities

- list-issues
- create-issue
- update-issue
- search

Required credentials: `LINEAR_API_KEY`

## Notes

- Run `LINEAR setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/LINEAR/data/config.json`.
- Use `LINEAR --json` for machine-readable output.
