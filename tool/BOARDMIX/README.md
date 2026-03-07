# BOARDMIX

Boardmix collaborative whiteboard automation via CDMCP (Chrome DevTools MCP).

## Purpose

Access Boardmix boards, mind maps, flowcharts, and collaborative features via the authenticated boardmix.com session using Chrome DevTools Protocol.

## MCP Commands

```bash
BOARDMIX --mcp-boot          # Boot CDMCP session with Boardmix tab
BOARDMIX --mcp-status        # Check auth state and page info
BOARDMIX --mcp-state         # Get full MCP state as JSON
BOARDMIX --mcp-session       # Show session details
BOARDMIX --mcp-boards        # List boards on current page
BOARDMIX --mcp-explore       # Run DOM exploration (Phase 1)
```

## Setup

1. Ensure Chrome is running with remote debugging on port 9222.
2. Log into boardmix.com in Chrome.
3. Run `BOARDMIX --mcp-boot` to create a CDMCP session.

## Dependencies

- PYTHON (runtime)
- websocket-client (CDP communication)
- GOOGLE.CDMCP (session management, overlays, interactions)
