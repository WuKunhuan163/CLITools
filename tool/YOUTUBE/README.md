# YOUTUBE -- YouTube Automation via CDMCP

Search videos, control playback, manage engagement (like/subscribe/comment), extract transcripts, navigate YouTube Studio, find live streams, manage settings, and explore YouTube Premium -- all via Chrome DevTools Protocol.

## Prerequisites

- Chrome/Chromium running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- Dependency: `GOOGLE.CDMCP`

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Session & Status
```bash
YOUTUBE --mcp-boot                                   # Boot YouTube session in dedicated window
YOUTUBE --mcp-session                                # Show session and state machine status
YOUTUBE --mcp-recover                                # Recover from error state
YOUTUBE --mcp-status                                 # Check authentication state
YOUTUBE --mcp-page                                   # Show current YouTube page info
YOUTUBE --mcp-login                                  # Navigate to Google sign-in
YOUTUBE --mcp-state                                  # Get comprehensive MCP state (player + page)
YOUTUBE --mcp-layout                                 # Identify home page layout areas
```

### Navigation
```bash
YOUTUBE --mcp-navigate home                          # Go to YouTube home
YOUTUBE --mcp-navigate shorts                        # Go to Shorts
YOUTUBE --mcp-navigate subscriptions                 # Go to Subscriptions
YOUTUBE --mcp-navigate history                       # Go to History
YOUTUBE --mcp-navigate playlists                     # Go to Playlists
YOUTUBE --mcp-navigate watch_later                   # Go to Watch Later
YOUTUBE --mcp-navigate liked                         # Go to Liked Videos
YOUTUBE --mcp-navigate trending                      # Go to Trending
YOUTUBE --mcp-navigate <URL>                         # Navigate to any URL
YOUTUBE --mcp-open <video_id_or_url>                 # Open a specific video
YOUTUBE --mcp-channel                                # Navigate to current video's channel page
YOUTUBE --mcp-back                                   # Go back to previous page
```

### Search & Info
```bash
YOUTUBE --mcp-search "query" --limit 10              # Search for videos
YOUTUBE --mcp-filter-search "query" --type video     # Search with type filter
YOUTUBE --mcp-info [url]                             # Get video details
YOUTUBE --mcp-screenshot [--output path]             # Capture current page
YOUTUBE --mcp-transcript [url]                       # Extract transcript from browser panel
YOUTUBE --mcp-subtitles <video_id> [--save path]     # Fetch subtitles with language info
```

### Playback Controls
```bash
YOUTUBE --mcp-play                                   # Play current video
YOUTUBE --mcp-pause                                  # Pause current video
YOUTUBE --mcp-seek 90                                # Seek to 90 seconds
YOUTUBE --mcp-seek 1:30                              # Seek to 1m30s
YOUTUBE --mcp-seek 50%                               # Seek to 50%
YOUTUBE --mcp-seek +10                               # Forward 10 seconds
YOUTUBE --mcp-volume 75                              # Set volume to 75%
YOUTUBE --mcp-volume --mute                          # Mute audio
YOUTUBE --mcp-speed 1.5                              # Set playback speed to 1.5x
YOUTUBE --mcp-quality 1080p                          # Set video quality
YOUTUBE --mcp-captions --on                          # Enable captions
YOUTUBE --mcp-fullscreen                             # Toggle fullscreen
YOUTUBE --mcp-theater                                # Toggle theater mode
YOUTUBE --mcp-autoplay --on                          # Enable autoplay
YOUTUBE --mcp-pip                                    # Toggle picture-in-picture
YOUTUBE --mcp-apply-settings --quality 720p --speed 1.25 --captions
```

### Chapters
```bash
YOUTUBE --mcp-chapters                               # List video chapters
YOUTUBE --mcp-seek-chapter --index 5                 # Jump to chapter by index
```

### Engagement
```bash
YOUTUBE --mcp-like                                   # Like current video
YOUTUBE --mcp-dislike                                # Dislike current video
YOUTUBE --mcp-subscribe                              # Subscribe/unsubscribe to channel
YOUTUBE --mcp-share                                  # Open share dialog, get share URL
YOUTUBE --mcp-save --playlist "Watch later"          # Save to playlist
YOUTUBE --mcp-comment "Great video!"                 # Add a comment
```

### Recommendations & Comments
```bash
YOUTUBE --mcp-next                                   # Navigate to next recommended video
YOUTUBE --mcp-recommendations --limit 10             # List recommended videos
YOUTUBE --mcp-comments --limit 10                    # Extract top comments
YOUTUBE --mcp-expand-description                     # Expand video description text
```

### Watch History
```bash
YOUTUBE --mcp-history --limit 10                     # View watch history items
YOUTUBE --mcp-delete-history --index 0               # Delete a watch history item
```

### Live Streams
```bash
YOUTUBE --mcp-live-streams --category "tech"         # Find live streams by category
YOUTUBE --mcp-live-stats                             # Get live stream statistics
```

### YouTube Studio
```bash
YOUTUBE --mcp-studio dashboard                       # Navigate to Studio dashboard
YOUTUBE --mcp-studio content                         # Navigate to content management
YOUTUBE --mcp-studio analytics                       # Navigate to analytics
YOUTUBE --mcp-studio comments                        # Navigate to comments management
```

### Playlists & Settings
```bash
YOUTUBE --mcp-create-playlist "My Playlist"          # Create a new playlist
YOUTUBE --mcp-settings account                       # Navigate to account settings
YOUTUBE --mcp-settings notifications                 # Navigate to notification settings
YOUTUBE --mcp-premium                                # View YouTube Premium benefits
```

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Features

- **Navigation & Layout**: Home page layout identification, section navigation (Home, Explore, Shorts, Subscriptions, History, Library, Studio)
- **Playback Control**: Full player control (play/pause/seek/volume/speed/quality/captions/fullscreen/theater/PiP)
- **Chapter Navigation**: Extract chapter markers and jump to chapters by index
- **Engagement**: Like/dislike, subscribe, share, save to playlists, post comments
- **Search & Discovery**: Structured search results, filtered search, recommendations, next-video navigation
- **Live Streams**: Find live streams by category, view real-time statistics
- **YouTube Studio**: Navigate to any Studio section (dashboard, content, analytics, comments)
- **Transcript / Subtitles**: Opens built-in transcript panel, reads segments with timestamps
- **Watch History**: View and manage watch history items
- **State Reporting**: Comprehensive MCP state (URL, player state, auth, recommendations)
- **Session Management**: CDMCP sessions with idle/absolute timeouts and auto-recovery

## Dependencies

- GOOGLE.CDMCP (session management, overlays, interaction interfaces)
- websocket-client
