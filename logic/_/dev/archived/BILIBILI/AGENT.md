# BILIBILI -- Agent Reference

## Quick Start
```
BILIBILI boot                                     # Boot session
BILIBILI state                                    # Full MCP state
BILIBILI layout                                   # Identify home page areas
BILIBILI search "Python教程" --limit 5            # Search videos
BILIBILI open BV1xHn9z8EPX                        # Open by BV ID
BILIBILI info                                     # Current video details
BILIBILI play                                     # Play video
BILIBILI auto-speed                               # Auto-adjust speed (tutorial=1.25x)
BILIBILI like                                     # Like video
BILIBILI follow                                   # Toggle follow UP
BILIBILI screenshot --output /tmp/bl.png          # Screenshot
```

## Navigation Targets
`home`, `bangumi`, `live`, `anime`, `history`, `favorites`, `dynamics`, `trending`, `ranking`, `tech`, `science`, `game`, `music`, `dance`, `food`, `car`, `fashion`, `sports`, `settings`, or any URL.

## API Functions

### Session & Status
- `boot_session()` -- Boot CDMCP session
- `get_session_status()` -- Returns `{state, session_alive, cdp_available}`
- `get_mcp_state()` -- Comprehensive state (player, metadata, auth, danmaku)
- `get_auth_state()` -- Returns `{authenticated, username}`
- `get_page_info()` -- Returns `{url, title, section}`
- `get_home_layout()` -- Returns `{areas, nav_tabs, video_count}`

### Navigation
- `navigate(target)` -- Navigate to section or URL
- `open_video(bvid_or_url)` -- Open video by BV ID or URL
- `go_back()` -- Navigate back
- `navigate_to_uploader()` -- Go to UP's page
- `navigate_personal()` -- Go to personal space

### Search & Discovery
- `search_videos(query, limit)` -- Returns video results
- `search_with_filters(query, duration, sort_by, tids, limit)` -- Filtered search
- `get_video_info(video_url)` -- Returns video metadata
- `get_trending(limit)` -- Trending videos
- `get_history(limit)` -- Watch history
- `get_recommendations(limit)` -- Recommended videos
- `get_comments(limit)` -- Comments (handles Shadow DOM)
- `next_video()` -- Next recommended video

### Playback
- `play()`, `pause()` -- Play/pause control
- `seek(target)` -- Seek: `"90"`, `"1:30"`, `"50%"`, `"+10"`, `"-10"`
- `volume(level, mute)` -- Set volume 0-100, mute/unmute
- `speed(rate)` -- Set speed 0.5-2.0
- `auto_speed()` -- Auto-adjust based on content type
- `quality(level)` -- Set quality
- `fullscreen()`, `widescreen()`, `pip()` -- Display modes

### Chapters
- `get_chapters()` -- List chapter markers
- `seek_to_chapter(index)` -- Seek to chapter

### Subtitles
- `get_subtitles()` -- Check subtitle availability
- `toggle_subtitles(on)` -- Toggle subtitles on/off

### Danmaku (Advanced)
- `danmaku(toggle)` -- Toggle danmaku on/off
- `send_danmaku(text)` -- Send danmaku
- `get_danmaku_settings()` -- Read display settings
- `set_danmaku_filter(keyword)` -- Add block keyword
- `set_danmaku_opacity(opacity)` -- Set opacity 0-100

### Engagement
- `like()`, `coin(amount)`, `favorite()`, `triple()`, `share()`, `follow()`
- `comment(text)` -- Post comment
- `batch_reply_comments(reply_text, count)` -- Batch reply to comments

### Watch Later
- `add_to_watchlater()` -- Add current video
- `get_watchlater(limit)` -- List Watch Later
- `play_watchlater()` -- Start continuous playback

### Live Streaming
- `navigate_live(category)` -- Go to Bilibili Live
- `enter_live_room(room_id)` -- Enter live room (by ID or first available)
- `get_live_info()` -- Room info (title, streamer, viewers, area)
- `send_live_danmaku(text)` -- Send live danmaku
- `get_live_stats()` -- Live statistics
- `get_live_replays(limit)` -- Past live replays

### Content Creation
- `navigate_creative_center(section)` -- Sections: home, upload, content, article, data, fans
- `create_article_draft(title, content)` -- Create article draft
- `get_creative_inspiration(category)` -- Trending topics for creators
- `get_data_center(time_range)` -- Data center metrics
- `manage_favorites(action, name)` -- List/create favorite folders

### Community
- `post_dynamic(text, poll_options)` -- Post dynamic with optional poll
- `navigate_fan_medal()` -- Fan medal management
- `navigate_topic_challenge(query)` -- Topic challenges

### Settings & Privacy
- `navigate_privacy_settings()` -- Privacy settings page
- `set_privacy()` -- Read privacy settings
- `navigate_notification_settings()` -- Notification settings page
- `set_notifications()` -- Read notification settings
- `navigate_vip_page()` -- VIP/大会员 page (no purchase)
- `get_vip_benefits()` -- Read VIP benefits

## Workflow Patterns

### Watch & Interact
```
BILIBILI open BV_ID -> BILIBILI state -> BILIBILI like -> BILIBILI comment "text"
```

### Search & Browse
```
BILIBILI search "topic" -> BILIBILI open BV_ID -> BILIBILI recommendations
```

### Filtered Search Workflow (Task 20)
```
BILIBILI filter-search "topic" --duration 10-30 --sort views -> BILIBILI open BV_ID -> BILIBILI chapters -> BILIBILI creative article
```

### Channel Exploration
```
BILIBILI open BV_ID -> BILIBILI uploader -> BILIBILI follow -> BILIBILI back
```

### Full Engagement (三连)
```
BILIBILI open BV_ID -> BILIBILI triple -> BILIBILI comment "text" -> BILIBILI share
```

### Watch Later Workflow
```
BILIBILI open BV_ID -> BILIBILI watchlater-add -> BILIBILI search "more" -> BILIBILI watchlater-add -> BILIBILI watchlater-play
```

### Live Streaming
```
BILIBILI live --category tech -> BILIBILI live-enter -> BILIBILI live-info -> BILIBILI live-danmaku "text" -> BILIBILI live-stats
```

### Content Creation
```
BILIBILI creative article -> BILIBILI article-draft "Title" --content "Body" -> BILIBILI data-center
```

### Settings & Privacy
```
BILIBILI privacy-settings -> BILIBILI privacy -> BILIBILI notification-settings -> BILIBILI notifications
```

### VIP Benefits (View Only)
```
BILIBILI vip-page -> BILIBILI vip-benefits -> BILIBILI back
```

## Key Selectors
- Play/Pause: `.bpx-player-ctrl-play` or keyboard space
- Volume: `.bpx-player-ctrl-volume`
- Quality: `.bpx-player-ctrl-quality`
- Danmaku toggle: `.bui-danmaku-switch input`
- Danmaku input: `.bpx-player-dm-input`
- Like: `.video-like`
- Coin: `.video-coin`
- Favorite: `.video-fav`
- Share: `.video-share`
- Follow: `.bi-follow, .follow-btn`
- Comment input: `.reply-box-textarea`
- UP name: `.up-name, .up-info--detail a`
- Live chat: `#chat-control-panel-vm textarea`
- Live rooms: `a[href*="live.bilibili.com/"]`
- VIP benefits: `.benefit-item-wrapper`
- Data center cards: `.data-card, .overview-card`
