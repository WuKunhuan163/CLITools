# SENTRY - Agent Guide

AI-powered error monitoring via Sentry MCP

## Quick Reference

```bash
SENTRY status          # Check status and capabilities
SENTRY config <k> <v>  # Set API credentials
SENTRY setup           # Install dependencies and configure
```

## Capabilities

- list-issues
- error-details
- performance-monitoring
- alerts

Required credentials: `SENTRY_AUTH_TOKEN`

## Notes

- Run `SENTRY setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/SENTRY/data/config.json`.
- Use `SENTRY --json` for machine-readable output.
