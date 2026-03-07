# YOUTUBE -- Agent Reference

## Quick Start
```
YOUTUBE boot                                       # Boot session
YOUTUBE state                                      # Full MCP state
YOUTUBE layout                                     # Identify home page areas
YOUTUBE search "machine learning" --limit 5        # Search videos
YOUTUBE open dQw4w9WgXcQ                           # Open by video ID
YOUTUBE info                                       # Current video details
YOUTUBE play                                       # Play video
YOUTUBE pause                                      # Pause video
YOUTUBE seek 1:30                                  # Seek to 1m30s
YOUTUBE chapters                                   # List video chapters
YOUTUBE seek-chapter --index 3                     # Jump to chapter 3
YOUTUBE like                                       # Like video
YOUTUBE subscribe                                  # Toggle subscribe
YOUTUBE channel                                    # Go to video's channel page
YOUTUBE back                                       # Go back to previous page
YOUTUBE transcript                                 # Extract transcript
YOUTUBE screenshot --output /tmp/yt.png            # Screenshot
```

## Navigation Targets
`home`, `shorts`, `subscriptions`, `history`, `playlists`, `watch_later`, `liked`, `trending`, `explore`, `library`, `studio`, or any URL.

## API Functions

### Session & Status
- `boot_session()` -- Boot CDMCP session, returns `{ok, action, state}`
- `get_session_status()` -- Returns `{state, transcript_state, session_alive, cdp_available}`
- `get_mcp_state()` -- Returns comprehensive state: `{url, section, video_title, channel, player:{paused,currentTime,duration,volume,muted,playbackRate,progress_pct}, captions, authenticated, recommendation_count, machine_state}`
- `get_auth_state()` -- Returns `{authenticated, channelName, title}`
- `get_page_info()` -- Returns `{url, title, section}`
- `get_home_layout()` -- Returns `{areas, category_chips, video_count, topbar, sidebar, search_box}`

### Navigation
- `navigate(target)` -- Navigate to section name or URL, returns `{ok, url, target}`
- `open_video(video_url)` -- Open video by URL or ID
- `login()` -- Navigate to Google sign-in
- `go_back()` -- Navigate back to previous page
- `navigate_to_channel()` -- Click channel name on video page to go to channel

### Search & Info
- `search_videos(query, limit)` -- Returns `{results:[{title,channel,views,duration,url,videoId}]}`
- `search_with_filters(query, duration, sort_by, filter_type, limit)` -- Filtered search (type: video/live/playlist)
- `get_video_info(video_url)` -- Returns `{title,channel,views,subscribers,date,description,likes,videoId}`
- `take_screenshot(output_path)` -- Returns `{path, size}`
- `get_transcript(video_url)` -- Returns `{segments,lines:[{timestamp,text}],fullText}`
- `fetch_subtitles_api(video_id)` -- Same + `{availableLanguages,language,languageName}`

### Playback Controls
- `play()` -- Play current video
- `pause()` -- Pause current video
- `seek(target)` -- Seek: `"90"`, `"1:30"`, `"50%"`, `"+10"`, `"-10"`
- `volume(level, mute)` -- Set volume 0-100 and/or mute state
- `speed(rate)` -- Set playback speed 0.25-2.0
- `quality(level)` -- Set quality: `"1080p"`, `"720p"`, etc.
- `captions(toggle)` -- Toggle subtitles True/False
- `fullscreen()` -- Toggle fullscreen
- `theater()` -- Toggle theater mode
- `autoplay(toggle)` -- Toggle autoplay True/False
- `pip()` -- Toggle picture-in-picture
- `apply_default_settings(quality_level, speed_rate, captions_on)` -- Apply combo settings

### Chapters
- `get_chapters()` -- Returns `{chapters:[{index, title, time}], count}`
- `seek_to_chapter(index)` -- Jump to chapter by index

### Engagement
- `like()` -- Like current video
- `dislike()` -- Dislike current video
- `subscribe()` -- Toggle subscribe to channel (waits for button load)
- `share()` -- Open share dialog, returns `{share_url}`
- `save(playlist)` -- Save to playlist (default "Watch later")
- `comment(text)` -- Post a comment

### Discovery
- `next_video()` -- Navigate to next recommended video
- `get_recommendations(limit)` -- Returns `{results:[{title,channel,views,duration,videoId,url}]}` (supports modern + legacy DOM)
- `get_comments(limit)` -- Returns `{comments:[{author,text,likes,time,reply_count}]}`
- `expand_description()` -- Returns `{description}`

### History
- `get_watch_history(limit)` -- Returns `{items:[{title,url,channel,index}], count}` (uses `yt-lockup-view-model` with fallback)
- `delete_history_item(index)` -- Delete watch history item by 0-based index

### Live Streams
- `find_live_streams(category, limit)` -- Returns `{streams:[{title,channel,viewers,url}], count}`
- `get_live_stats()` -- Returns `{title, channel, viewers, likes, has_chat}`

### YouTube Studio
- `navigate_studio(section)` -- Navigate to Studio section: dashboard/content/analytics/comments/playlists/subtitles/monetization/customization
- `create_playlist(name)` -- Open create playlist dialog

### Settings & Premium
- `navigate_settings(section)` -- Navigate to settings: account/notifications/privacy/playback/advanced
- `navigate_premium()` -- Navigate to Premium page (view only)
- `get_premium_benefits()` -- Read benefit descriptions from Premium page

## Workflow Patterns

### Watch & Analyze
```
YOUTUBE open VIDEO_ID -> YOUTUBE state -> YOUTUBE transcript -> YOUTUBE comments
```

### Chapter-Based Learning
```
YOUTUBE open TUTORIAL_VIDEO -> YOUTUBE chapters -> YOUTUBE seek-chapter --index 3 -> YOUTUBE speed 1.5
```

### Search & Discover
```
YOUTUBE search "topic" -> YOUTUBE open RESULT_URL -> YOUTUBE recommendations
```

### Advanced Filtered Search
```
YOUTUBE filter-search "Python automation" --type video --limit 10
```

### Navigate & Explore
```
YOUTUBE navigate home -> YOUTUBE layout -> YOUTUBE navigate explore -> YOUTUBE back
```

### Channel Exploration
```
YOUTUBE open VIDEO -> YOUTUBE channel -> YOUTUBE back
```

### Engagement
```
YOUTUBE open VIDEO -> YOUTUBE like -> YOUTUBE subscribe -> YOUTUBE save -> YOUTUBE share
```

### Playback Control
```
YOUTUBE play -> YOUTUBE seek 50% -> YOUTUBE speed 1.5 -> YOUTUBE volume 80
```

### Custom Settings
```
YOUTUBE apply-settings --quality 1080p --speed 1.25 --captions
```

### Live Streams
```
YOUTUBE live-streams --category "tech" -> YOUTUBE open STREAM_URL -> YOUTUBE live-stats
```

### YouTube Studio
```
YOUTUBE studio dashboard -> YOUTUBE studio analytics -> YOUTUBE studio content
```

### History Management
```
YOUTUBE navigate history -> YOUTUBE history --limit 10 -> YOUTUBE delete-history --index 0
```

### Settings
```
YOUTUBE settings privacy -> YOUTUBE settings notifications
```

### Premium (View Only)
```
YOUTUBE premium
```

### Comprehensive Workflow
```
YOUTUBE search "topic" --limit 10
YOUTUBE open TOP_VIDEO_URL
YOUTUBE chapters
YOUTUBE apply-settings --quality 720p --speed 1.25 --captions
YOUTUBE info
YOUTUBE expand-description
YOUTUBE recommendations --limit 5
YOUTUBE studio dashboard
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
- History items: `yt-lockup-view-model` (modern), `ytd-video-renderer` (legacy)
- Recommendations: `a[href*="/watch"]` in `#secondary` (fallback)
- Chapters: `ytd-macro-markers-list-item-renderer`
- Live chat: `iframe#chatframe`
