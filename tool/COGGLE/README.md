# COGGLE

Coggle mind mapping automation via CDMCP (Chrome DevTools MCP).

## Purpose

Access Coggle mind maps, diagrams, and collaborative features via the authenticated coggle.it session using Chrome DevTools Protocol.

## MCP Commands

```bash
COGGLE --mcp-boot          # Boot CDMCP session with Coggle tab
COGGLE --mcp-status        # Check auth state and page info
COGGLE --mcp-state         # Get full MCP state as JSON
COGGLE --mcp-session       # Show session details
COGGLE --mcp-diagrams      # List diagrams on current page
COGGLE --mcp-explore       # Run DOM exploration (Phase 1)
```

## Setup

1. Ensure Chrome is running with remote debugging on port 9222.
2. Log into coggle.it in Chrome.
3. Run `COGGLE --mcp-boot` to create a CDMCP session.

## Dependencies

- PYTHON (runtime)
- websocket-client (CDP communication)
- GOOGLE.CDMCP (session management, overlays, interactions)
