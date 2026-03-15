# WHIMSICAL

Whimsical whiteboard & flowchart automation via CDMCP (Chrome DevTools MCP).

## Purpose

Access Whimsical boards, flowcharts, mind maps, and docs via the authenticated whimsical.com session using Chrome DevTools Protocol.

## MCP Commands

```bash
WHIMSICAL --mcp-boot          # Boot CDMCP session with Whimsical tab
WHIMSICAL --mcp-status        # Check auth state and page info
WHIMSICAL --mcp-state         # Get full MCP state as JSON
WHIMSICAL --mcp-session       # Show session details
WHIMSICAL --mcp-boards        # List boards on current page
WHIMSICAL --mcp-explore       # Run DOM exploration (Phase 1)
```

## Setup

1. Ensure Chrome is running with remote debugging on port 9222.
2. Log into whimsical.com in Chrome.
3. Run `WHIMSICAL --mcp-boot` to create a CDMCP session.

## Dependencies

- PYTHON (runtime)
- websocket-client (CDP communication)
- GOOGLE.CDMCP (session management, overlays, interactions)
