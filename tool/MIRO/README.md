# MIRO

Miro collaborative whiteboard automation via CDMCP (Chrome DevTools MCP).

## Purpose

Access Miro boards, sticky notes, diagrams, and collaborative features via the authenticated miro.com session using Chrome DevTools Protocol.

## MCP Commands

```bash
MIRO --mcp-boot          # Boot CDMCP session with Miro tab
MIRO --mcp-status        # Check auth state and page info
MIRO --mcp-state         # Get full MCP state as JSON
MIRO --mcp-session       # Show session details
MIRO --mcp-boards        # List boards on current page
MIRO --mcp-explore       # Run DOM exploration (Phase 1)
```

## Setup

1. Ensure Chrome is running with remote debugging on port 9222.
2. Log into miro.com in Chrome.
3. Run `MIRO --mcp-boot` to create a CDMCP session.

## Dependencies

- PYTHON (runtime)
- websocket-client (CDP communication)
- GOOGLE.CDMCP (session management, overlays, interactions)
