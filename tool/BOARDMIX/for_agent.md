# BOARDMIX -- For Agent Reference

Boardmix collaborative whiteboard automation via CDMCP.

## Quick Reference

```bash
BOARDMIX --mcp-boot          # Boot session
BOARDMIX --mcp-status        # Auth & page state
BOARDMIX --mcp-state         # Full JSON state
BOARDMIX --mcp-boards        # List boards
BOARDMIX --mcp-explore       # DOM exploration
```

## Key Behaviors

- Uses CDMCP session management (auto-recovery, visual overlays).
- Brand color: `#4A6CF7` (Boardmix blue).
- URL pattern: `boardmix.com`.
- Requires active Chrome session with boardmix.com logged in.

## Development Status

Early exploration phase. Use `--mcp-explore` to discover interactive elements.
