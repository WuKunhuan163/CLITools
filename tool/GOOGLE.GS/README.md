# GOOGLE.GS — Google Scholar MCP

Automate Google Scholar searches, citation management, author discovery,
and library operations via CDMCP session management and visual overlays.

## Prerequisites

- Chrome with `--remote-debugging-port=9222`
- GOOGLE.CDMCP tool installed
- Logged into Google account in Chrome

## Features

### Search & Navigation
```bash
GS search large language model reasoning           # Search papers
GS search transformers --year-from 2023             # With year filter
GS results                                          # Re-read current results
GS next                                             # Next page
GS prev                                             # Previous page
GS filter --time 2025                               # Filter: since 2025
GS filter --sort date                               # Sort by date
```

### Per-Result Actions
```bash
GS open --index 0          # Open paper link
GS save --index 0          # Save to Google Scholar library
GS cite --index 0          # Get citation (MLA, APA, Chicago, Harvard, Vancouver + BibTeX/EndNote/RefMan)
GS cited-by --index 0      # Papers citing this paper
GS pdf --index 0           # Get PDF URL
```

### Profile & Library
```bash
GS profile                 # Open your Scholar profile (name, affiliation, stats)
GS library                 # View saved papers
GS author Geoffrey Hinton  # Search for author profiles
```

### Session & State
```bash
GS boot                    # Boot Scholar session in dedicated window
GS state                   # Get Turing machine state + page info
GS screenshot --output /tmp/shot.png
```

## Visual Effects

All operations use CDMCP MCP interaction interfaces:
- **Badge**: Blue "GS [session_id]" in top-right corner
- **Lock overlay**: "Locked by Terminal Tool 'GOOGLE.GS', Click to unlock"
- **MCP counter**: Bottom-left timestamp + operation count
- **Element highlight**: Orange outline on target elements during interaction

## State Machine

```
UNINITIALIZED → BOOTING → IDLE
IDLE → SEARCHING → IDLE
IDLE → VIEWING_PAPER / VIEWING_PROFILE / VIEWING_CITATIONS
Any → ERROR → RECOVERING → IDLE
```

State persists in `data/state/gs_<session>.json`.

## API Usage (for other tools)

```python
import importlib.util
spec = importlib.util.spec_from_file_location("gs_api", "<path>/logic/chrome/api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

api.boot_session()
r = api.search("neural network")
print(r["results"][0]["title"])

c = api.cite_paper(index=0)
print(c["citations"]["format_0"])  # MLA citation
```

## Testing

```bash
TOOL test GOOGLE.GS
python3 test/test_00_help.py    # Help flag
python3 test/test_01_search.py  # Live search + cite + PDF
```
