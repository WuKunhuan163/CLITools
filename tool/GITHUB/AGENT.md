# GITHUB - Agent Guide

GitHub integration via GitHub MCP

## Quick Reference

```bash
GITHUB status          # Check status and capabilities
GITHUB config <k> <v>  # Set API credentials
GITHUB setup           # Install dependencies and configure
```

## Capabilities

- repositories
- issues
- pull-requests
- code-search
- file-operations

Required credentials: `GITHUB_PERSONAL_ACCESS_TOKEN`

## Notes

- Run `GITHUB setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/GITHUB/data/config.json`.
- Use `GITHUB --json` for machine-readable output.
