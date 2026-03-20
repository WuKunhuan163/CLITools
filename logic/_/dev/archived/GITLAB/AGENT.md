# GITLAB - Agent Guide

GitLab integration via GitLab MCP

## Quick Reference

```bash
GITLAB status          # Check status and capabilities
GITLAB config <k> <v>  # Set API credentials
GITLAB setup           # Install dependencies and configure
```

## Capabilities

- repositories
- issues
- merge-requests
- pipelines

Required credentials: `GITLAB_TOKEN`, `GITLAB_URL`

## Notes

- Run `GITLAB setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/GITLAB/data/config.json`.
- Use `GITLAB --json` for machine-readable output.
