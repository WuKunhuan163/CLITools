# DINGTALK - Agent Guide

DingTalk messaging and workspace integration

## Quick Reference

```bash
DINGTALK status          # Check status and capabilities
DINGTALK config <k> <v>  # Set API credentials
DINGTALK setup           # Install dependencies and configure
```

## Capabilities

- send-message
- group-management
- webhook

Required credentials: `DINGTALK_APP_KEY`, `DINGTALK_APP_SECRET`

## Notes

- Run `DINGTALK setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/DINGTALK/data/config.json`.
- Use `DINGTALK --json` for machine-readable output.
