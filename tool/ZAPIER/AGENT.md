# ZAPIER - Agent Guide

Workflow automation via Zapier MCP

## Quick Reference

```bash
ZAPIER status          # Check status and capabilities
ZAPIER config <k> <v>  # Set API credentials
ZAPIER setup           # Install dependencies and configure
```

## Capabilities

- trigger-zap
- list-actions
- execute-action

Required credentials: `ZAPIER_MCP_URL`

## Notes

- Run `ZAPIER setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/ZAPIER/data/config.json`.
- Use `ZAPIER --json` for machine-readable output.
