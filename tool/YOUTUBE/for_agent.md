# YOUTUBE -- Agent Reference

YouTube tool with **API-first** design: data retrieval (search, info, comments, subtitles) uses YouTube Data API v3; browser automation (playback, navigation, engagement) uses CDMCP.

## Setup

```bash
YOUTUBE config --api-key <YOUR_YOUTUBE_DATA_API_V3_KEY>
```

Get a key at: https://console.cloud.google.com/apis/credentials

## API Commands (no browser needed)

```bash
YOUTUBE search "machine learning" --limit 5     # Search videos via API
YOUTUBE info VIDEO_URL_OR_ID                     # Video details via API
YOUTUBE subtitles VIDEO_ID                       # Fetch captions (no API key needed)
YOUTUBE subtitles VIDEO_ID --save /tmp/subs.txt  # Save transcript to file
YOUTUBE config                                   # Check API key status
```

## Browser Commands (requires CDMCP session)

```bash
YOUTUBE boot                          # Boot CDMCP session
YOUTUBE state                         # Full MCP state
YOUTUBE open VIDEO_URL_OR_ID          # Open video in browser
YOUTUBE play / pause                  # Playback control
YOUTUBE seek 1:30                     # Seek to position
YOUTUBE volume 80                     # Set volume
YOUTUBE speed 1.5                     # Playback speed
YOUTUBE like / subscribe              # Engagement
YOUTUBE comments --limit 10           # Comments (API first, CDMCP fallback)
YOUTUBE recommendations --limit 5     # Recommended videos
YOUTUBE screenshot --output /tmp/y.png
```

## Workflow: Search & Analyze (API only)

```bash
YOUTUBE search "Python tutorial" --limit 5
YOUTUBE info dQw4w9WgXcQ
YOUTUBE subtitles dQw4w9WgXcQ --save /tmp/transcript.txt
```

## Workflow: Interactive Watch

```bash
YOUTUBE boot
YOUTUBE search "topic" --limit 10
YOUTUBE open VIDEO_URL
YOUTUBE chapters
YOUTUBE seek-chapter --index 3
YOUTUBE speed 1.25
```

## Fallback Behavior

API commands automatically fall back to CDMCP if the API key is not configured or the API call fails. This ensures the tool works in all configurations.

## Navigation Targets

`home`, `shorts`, `subscriptions`, `history`, `playlists`, `watch_later`, `liked`, `trending`, `explore`, `library`, `studio`, or any URL.

## ToS Compliance

YouTube Data API v3 is the official Google API for YouTube data access. Browser automation via CDMCP is used only for interactive playback control that has no API equivalent.
