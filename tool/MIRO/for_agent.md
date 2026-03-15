# MIRO -- For Agent Reference

Miro collaborative whiteboard automation via CDMCP.

## Quick Reference

```bash
MIRO --mcp-boot          # Boot session
MIRO --mcp-status        # Auth & page state
MIRO --mcp-state         # Full JSON state
MIRO --mcp-boards        # List boards
MIRO --mcp-explore       # DOM exploration
```

## Key Behaviors

- Uses CDMCP session management (auto-recovery, visual overlays).
- Brand color: `#FFD02F` (Miro yellow).
- URL pattern: `miro.com`.
- Requires active Chrome session with miro.com logged in.

## Development Status

Early exploration phase. Use `--mcp-explore` to discover interactive elements.
