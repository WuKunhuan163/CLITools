# YOUTUBE — YouTube Automation via CDMCP

Search videos, control playback, manage engagement (like/subscribe/comment), extract transcripts, and navigate YouTube via Chrome DevTools Protocol.

## Prerequisites

- Chrome/Chromium running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- Dependency: `GOOGLE.CDMCP`

## Commands

### Session & Status
```bash
YOUTUBE boot                                     # Boot YouTube session in dedicated window
YOUTUBE session                                  # Show session and state machine status
YOUTUBE recover                                  # Recover from error state
YOUTUBE status                                   # Check authentication state
YOUTUBE page                                     # Show current YouTube page info
YOUTUBE login                                    # Navigate to Google sign-in
YOUTUBE state                                    # Get comprehensive MCP state (player + page)
```

### Navigation
```bash
YOUTUBE navigate home                            # Go to YouTube home
YOUTUBE navigate shorts                          # Go to Shorts
YOUTUBE navigate subscriptions                   # Go to Subscriptions
YOUTUBE navigate history                         # Go to History
YOUTUBE navigate playlists                       # Go to Playlists
YOUTUBE navigate watch_later                     # Go to Watch Later
YOUTUBE navigate liked                           # Go to Liked Videos
YOUTUBE navigate trending                        # Go to Trending
YOUTUBE navigate <URL>                           # Navigate to any URL
YOUTUBE open <video_id_or_url>                   # Open a specific video
```

### Search & Info
```bash
YOUTUBE search "query" --limit 10                # Search for videos
YOUTUBE info [url]                               # Get video details (title, channel, views, etc.)
YOUTUBE screenshot [--output path]               # Capture current page
YOUTUBE transcript [url]                         # Extract transcript from browser panel
YOUTUBE subtitles <video_id> [--save path]       # Fetch subtitles with language info
```

### Playback Controls
```bash
YOUTUBE play                                     # Play current video
YOUTUBE pause                                    # Pause current video
YOUTUBE seek 90                                  # Seek to 90 seconds
YOUTUBE seek 1:30                                # Seek to 1m30s
YOUTUBE seek 50%                                 # Seek to 50%
YOUTUBE seek +10                                 # Forward 10 seconds
YOUTUBE seek -10                                 # Rewind 10 seconds
YOUTUBE volume 75                                # Set volume to 75%
YOUTUBE volume --mute                            # Mute audio
YOUTUBE volume --unmute                          # Unmute audio
YOUTUBE speed 1.5                                # Set playback speed to 1.5x
YOUTUBE quality 1080p                            # Set video quality
YOUTUBE quality                                  # List available qualities
YOUTUBE captions --on                            # Enable captions
YOUTUBE captions --off                           # Disable captions
YOUTUBE fullscreen                               # Toggle fullscreen
YOUTUBE theater                                  # Toggle theater mode
YOUTUBE autoplay --on                            # Enable autoplay
YOUTUBE autoplay --off                           # Disable autoplay
YOUTUBE pip                                      # Toggle picture-in-picture
```

### Engagement
```bash
YOUTUBE like                                     # Like current video
YOUTUBE dislike                                  # Dislike current video
YOUTUBE subscribe                                # Subscribe/unsubscribe to channel
YOUTUBE share                                    # Open share dialog, get share URL
YOUTUBE save --playlist "Watch later"            # Save to playlist
YOUTUBE comment "Great video!"                   # Add a comment
```

### Recommendations & Comments
```bash
YOUTUBE next                                     # Navigate to next recommended video
YOUTUBE recommendations --limit 10               # List recommended videos
YOUTUBE comments --limit 10                      # Extract top comments
YOUTUBE expand-description                       # Expand video description text
```

## Features

### Playback Control
Full video player control: play/pause, seek (absolute, relative, percentage, mm:ss), volume, speed (0.25-2.0), quality selection, captions toggle, fullscreen/theater/PiP modes.

### Engagement
Like/dislike videos, subscribe/unsubscribe to channels, share (extracts share URL), save to playlists, and post comments — all with MCP visual effects.

### Search & Discovery
Structured search results with title, channel, views, duration, and video URL/ID. Recommendation sidebar extraction and next-video navigation.

### Transcript / Subtitles
Opens YouTube's built-in transcript panel via CDP, reads rendered segments with timestamps. Reports available languages.

### State Reporting
`YOUTUBE state` provides comprehensive information: current URL, page section, video title/channel, player state (playing/paused/time/duration/volume/speed), captions state, authentication, recommendation count, and Turing machine state.

### Session Management
Uses CDMCP sessions with idle timeout (default 1h) and absolute timeout (default 24h). Automatic recovery on tab/window loss.

## Python API

```python
from tool.YOUTUBE.logic.chrome.api import (
    # Session
    boot_session, get_session_status, get_mcp_state,
    # Navigation
    navigate, open_video,
    # Search & Info
    search_videos, get_video_info, get_transcript,
    fetch_subtitles_api, take_screenshot, get_auth_state, login,
    # Playback
    play, pause, seek, volume, speed, quality, captions,
    fullscreen, theater, autoplay, pip,
    # Engagement
    like, dislike, subscribe, share, save, comment,
    # Discovery
    next_video, get_recommendations, get_comments, expand_description,
)
```
