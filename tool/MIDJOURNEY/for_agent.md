# MIDJOURNEY - Agent Guide

AI image generation via Midjourney API

## Quick Reference

```bash
MIDJOURNEY status          # Check status and capabilities
MIDJOURNEY config <k> <v>  # Set API credentials
MIDJOURNEY setup           # Install dependencies and configure
```

## Capabilities

- text-to-image
- image-transform
- upscale
- variations
- blend

Required credentials: `ACEDATACLOUD_API_TOKEN`

## Notes

- Run `MIDJOURNEY setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/MIDJOURNEY/data/config.json`.
- Use `MIDJOURNEY --json` for machine-readable output.
