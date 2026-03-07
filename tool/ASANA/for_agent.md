# ASANA - Agent Guide

Project management via Asana MCP

## Quick Reference

```bash
ASANA status          # Check status and capabilities
ASANA config <k> <v>  # Set API credentials
ASANA setup           # Install dependencies and configure
```

## Capabilities

- list-tasks
- create-task
- update-task
- search-projects

Required credentials: `ASANA_ACCESS_TOKEN`

## Notes

- Run `ASANA setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/ASANA/data/config.json`.
- Use `ASANA --json` for machine-readable output.

## ToS Compliance

**Status: COMPLIANT** -- This tool uses Asana's official REST API via in-page `fetch()` from the authenticated browser session (`_asana_api()` helper). CDMCP is only used for session management. Asana explicitly supports API access with PATs, OAuth, and bot accounts. All data operations go through `app.asana.com/api/1.0/`.
