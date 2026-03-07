# SQUARE - Agent Guide

Business and payment platform via Square MCP

## Quick Reference

```bash
SQUARE status          # Check status and capabilities
SQUARE config <k> <v>  # Set API credentials
SQUARE setup           # Install dependencies and configure
```

## Capabilities

- payments
- inventory
- catalog
- customers

Required credentials: `SQUARE_ACCESS_TOKEN`

## Notes

- Run `SQUARE setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/SQUARE/data/config.json`.
- Use `SQUARE --json` for machine-readable output.
