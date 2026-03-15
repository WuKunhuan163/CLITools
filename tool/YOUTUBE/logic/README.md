# YOUTUBE Logic

YouTube automation via CDMCP. Advanced session-based tool with state machine tracking, video playback control, subtitle extraction, and channel/playlist management.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, video control, search, subtitles |
| `chrome/state_machine.py` | FSM tracking session lifecycle (idle, searching, watching, etc.) |

## Sub-Packages

| Directory | Purpose |
|-----------|---------|
| `subtitle/` | Subtitle/transcript extraction utilities |

## Key Difference from Standard CDMCP Tools

YOUTUBE uses the full CDMCP session manager with extensive video playback controls, live stream monitoring, YouTube Studio navigation, and subtitle/transcript extraction.
