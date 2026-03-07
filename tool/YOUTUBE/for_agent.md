# YOUTUBE — Agent Reference

## Quick Start
```
YOUTUBE boot                                       # Boot session
YOUTUBE state                                      # Full MCP state
YOUTUBE search "machine learning" --limit 5        # Search videos
YOUTUBE open dQw4w9WgXcQ                           # Open by video ID
YOUTUBE info                                       # Current video details
YOUTUBE play                                       # Play video
YOUTUBE pause                                      # Pause video
YOUTUBE seek 1:30                                  # Seek to 1m30s
YOUTUBE like                                       # Like video
YOUTUBE subscribe                                  # Toggle subscribe
YOUTUBE transcript                                 # Extract transcript
YOUTUBE screenshot --output /tmp/yt.png            # Screenshot
```

## Navigation Targets
`home`, `shorts`, `subscriptions`, `history`, `playlists`, `watch_later`, `liked`, `trending`, `library`, or any URL.

## API Functions

### Session & Status
- `boot_session()` — Boot CDMCP session, returns `{ok, action, state}`
- `get_session_status()` — Returns `{state, transcript_state, session_alive, cdp_available}`
- `get_mcp_state()` — Returns comprehensive state: `{url, section, video_title, channel, player:{paused,currentTime,duration,volume,muted,playbackRate,progress_pct}, captions, authenticated, recommendation_count, machine_state}`
- `get_auth_state()` — Returns `{authenticated, channelName, title}`
- `get_page_info()` — Returns `{url, title, section}`

### Navigation
- `navigate(target)` — Navigate to section name or URL, returns `{ok, url, target}`
- `open_video(video_url)` — Open video by URL or ID
- `login()` — Navigate to Google sign-in

### Search & Info
- `search_videos(query, limit)` — Returns `{results:[{title,channel,views,duration,url,videoId}]}`
- `get_video_info(video_url)` — Returns `{title,channel,views,subscribers,date,description,likes,videoId}`
- `take_screenshot(output_path)` — Returns `{path, size}`
- `get_transcript(video_url)` — Returns `{segments,lines:[{timestamp,text}],fullText}`
- `fetch_subtitles_api(video_id)` — Same + `{availableLanguages,language,languageName}`

### Playback Controls
- `play()` — Play current video
- `pause()` — Pause current video
- `seek(target)` — Seek: `"90"`, `"1:30"`, `"50%"`, `"+10"`, `"-10"`
- `volume(level, mute)` — Set volume 0-100 and/or mute state
- `speed(rate)` — Set playback speed 0.25-2.0
- `quality(level)` — Set quality: `"1080p"`, `"720p"`, etc.
- `captions(toggle)` — Toggle subtitles True/False
- `fullscreen()` — Toggle fullscreen
- `theater()` — Toggle theater mode
- `autoplay(toggle)` — Toggle autoplay True/False
- `pip()` — Toggle picture-in-picture

### Engagement
- `like()` — Like current video
- `dislike()` — Dislike current video
- `subscribe()` — Toggle subscribe to channel
- `share()` — Open share dialog, returns `{share_url}`
- `save(playlist)` — Save to playlist (default "Watch later")
- `comment(text)` — Post a comment

### Discovery
- `next_video()` — Navigate to next recommended video
- `get_recommendations(limit)` — Returns `{results:[{title,channel,views,duration,videoId,url}]}`
- `get_comments(limit)` — Returns `{comments:[{author,text,likes,time,reply_count}]}`
- `expand_description()` — Returns `{description}`

## Workflow Patterns

### Watch & Analyze
```
YOUTUBE open VIDEO_ID → YOUTUBE state → YOUTUBE transcript → YOUTUBE comments
```

### Search & Discover
```
YOUTUBE search "topic" → YOUTUBE open RESULT_URL → YOUTUBE recommendations
```

### Engagement
```
YOUTUBE open VIDEO → YOUTUBE like → YOUTUBE subscribe → YOUTUBE save → YOUTUBE share
```

### Playback Control
```
YOUTUBE play → YOUTUBE seek 50% → YOUTUBE speed 1.5 → YOUTUBE volume 80
```

## Key Selectors (for CDMCP interact)
- Search input: `input#search`
- Play/Pause: `.ytp-play-button`
- Volume: `.ytp-mute-button`, `.ytp-volume-panel`
- Progress: `.ytp-progress-bar`
- Settings: `.ytp-settings-button`
- Fullscreen: `.ytp-fullscreen-button`
- Like: `like-button-view-model button`
- Subscribe: `ytd-subscribe-button-renderer button`
- Comment: `#simplebox-placeholder`
