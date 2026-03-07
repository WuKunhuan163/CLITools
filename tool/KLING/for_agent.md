# KLING - Agent Guide

AI video generation via Kling API

## Quick Reference

```bash
KLING status          # Check status and capabilities
KLING config <k> <v>  # Set API credentials
KLING setup           # Install dependencies and configure
```

## Capabilities

- text-to-video
- image-to-video
- lip-sync
- image-generation
- virtual-try-on

Required credentials: `KLING_ACCESS_KEY`, `KLING_SECRET_KEY`

## Notes

- Run `KLING setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/KLING/data/config.json`.
- Use `KLING --json` for machine-readable output.
