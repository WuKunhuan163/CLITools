# GOOGLE.GS -- Google Scholar MCP

Automate Google Scholar searches, citation management, author discovery,
and library operations via CDMCP session management and visual overlays.

## Prerequisites

- Chrome with `--remote-debugging-port=9222`
- GOOGLE.CDMCP tool installed
- Logged into Google account in Chrome

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Search & Navigation
```bash
GOOGLE.GS --mcp-search large language model reasoning    # Search papers
GOOGLE.GS --mcp-search transformers --year-from 2023     # With year filter
GOOGLE.GS --mcp-results                                  # Re-read current results
GOOGLE.GS --mcp-next                                     # Next page
GOOGLE.GS --mcp-prev                                     # Previous page
GOOGLE.GS --mcp-filter --time 2025                       # Filter: since 2025
GOOGLE.GS --mcp-filter --sort date                       # Sort by date
```

### Per-Result Actions
```bash
GOOGLE.GS --mcp-open --index 0          # Open paper link
GOOGLE.GS --mcp-save --index 0          # Save to Google Scholar library
GOOGLE.GS --mcp-cite --index 0          # Get citation formats + BibTeX
GOOGLE.GS --mcp-cited-by --index 0      # Papers citing this paper
GOOGLE.GS --mcp-pdf --index 0           # Get PDF URL
```

### Profile & Library
```bash
GOOGLE.GS --mcp-profile                 # Open your Scholar profile
GOOGLE.GS --mcp-library                 # View saved papers
GOOGLE.GS --mcp-author Geoffrey Hinton  # Search for author profiles
```

### Session & State
```bash
GOOGLE.GS --mcp-boot                    # Boot Scholar session in dedicated window
GOOGLE.GS --mcp-state                   # Get Turing machine state + page info
GOOGLE.GS --mcp-screenshot --output /tmp/shot.png
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Visual Effects

All operations use CDMCP MCP interaction interfaces:
- **Badge**: Blue "GS [session_id]" in top-right corner
- **Lock overlay**: "Locked by Terminal Tool 'GOOGLE.GS', Click to unlock"
- **MCP counter**: Bottom-left timestamp + operation count
- **Element highlight**: Orange outline on target elements during interaction

## State Machine

```
UNINITIALIZED -> BOOTING -> IDLE
IDLE -> SEARCHING -> IDLE
IDLE -> VIEWING_PAPER / VIEWING_PROFILE / VIEWING_CITATIONS
Any -> ERROR -> RECOVERING -> IDLE
```
