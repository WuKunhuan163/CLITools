# SUNO - Agent Guide

AI music generation via Suno API

## Quick Reference

```bash
SUNO status          # Check status and capabilities
SUNO config <k> <v>  # Set API credentials
SUNO setup           # Install dependencies and configure
```

## Capabilities

- music-generation
- lyrics-generation
- song-extension
- cover-remix

Required credentials: `ACEDATACLOUD_API_TOKEN`

## Notes

- Run `SUNO setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/SUNO/data/config.json`.
- Use `SUNO --json` for machine-readable output.
