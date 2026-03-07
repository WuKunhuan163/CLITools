# YOUTUBE — YouTube Automation via CDMCP

Search videos, extract transcripts/subtitles, take screenshots, and manage YouTube via Chrome DevTools Protocol.

## Prerequisites

- Chrome/Chromium running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- Dependency: `GOOGLE.CDMCP`

## Commands

```bash
YOUTUBE status                                    # Check auth state
YOUTUBE login                                     # Navigate to Google sign-in
YOUTUBE search "query" --limit 10                 # Search for videos
YOUTUBE info [url]                                # Get video details (title, channel, views, etc.)
YOUTUBE screenshot [--output path]                # Capture current page
YOUTUBE transcript [url]                          # Extract transcript from browser panel
YOUTUBE subtitles <video_id> [--save path]        # Fetch subtitles with language info
```

## Features

### Search
Returns structured results with title, channel, view count, duration, and video URL/ID.

### Video Info
Extracts title, channel name, subscriber count, views, date, description, and likes from the video page.

### Transcript / Subtitles
Opens YouTube's built-in transcript panel via CDP, reads rendered segments with timestamps. Reports available languages (English, auto-generated, German, Japanese, etc.).

### Screenshot
Full-page screenshot of the current YouTube page, saved as PNG.

### Authentication
Navigates to Google sign-in. Once logged in, all operations work with the authenticated session (subscriptions, playlists, etc.).

## Python API

```python
from tool.YOUTUBE.logic.chrome.api import (
    search_videos, get_video_info, get_transcript,
    fetch_subtitles_api, take_screenshot, get_auth_state, login,
)
```
