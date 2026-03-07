# HEYGEN - Agent Guide

AI avatar video generation via HeyGen API

## Quick Reference

```bash
HEYGEN status          # Check status and capabilities
HEYGEN config <k> <v>  # Set API credentials
HEYGEN setup           # Install dependencies and configure
```

## Capabilities

- avatar-management
- voice-selection
- video-generation

Required credentials: `HEYGEN_API_KEY`

## Notes

- Run `HEYGEN setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/HEYGEN/data/config.json`.
- Use `HEYGEN --json` for machine-readable output.
