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

## ToS Compliance

**Status: COMPLIANT** -- This tool uses Atlassian's official REST API via in-page `fetch()` from the authenticated session (`_atlassian_api()` helper). CDMCP is only used for session management. All data operations go through Atlassian's documented API. Note: Atlassian prohibits "robots, spiders, offline readers" that exceed human pace, but API access is explicitly permitted.
