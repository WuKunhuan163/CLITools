# ATLASSIAN - Agent Guide

Jira and Confluence integration via Atlassian MCP

## Quick Reference

```bash
ATLASSIAN status          # Check status and capabilities
ATLASSIAN config <k> <v>  # Set API credentials
ATLASSIAN setup           # Install dependencies and configure
```

## Capabilities

- jira-issues
- confluence-pages
- search
- create-update

Required credentials: `ATLASSIAN_API_TOKEN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_SITE_URL`

## Notes

- Run `ATLASSIAN setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/ATLASSIAN/data/config.json`.
- Use `ATLASSIAN --json` for machine-readable output.
