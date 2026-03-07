# BILIBILI

Bilibili video platform automation via CDMCP (Chrome DevTools MCP).

## Overview

Automates Bilibili (bilibili.com) through a dedicated CDMCP session window. Supports video playback control, search, engagement (like/coin/favorite/triple), danmaku, navigation, content sections, personal space, settings, live streaming, content creation, and content discovery.

## MCP Commands

All MCP commands use the `--mcp-` prefix.

### Session & Status
- `BILIBILI --mcp-boot` -- Boot Bilibili session in dedicated Chrome window.
- `BILIBILI --mcp-session` -- Show session and state machine status.
- `BILIBILI --mcp-recover` -- Recover from error state.
- `BILIBILI --mcp-status` -- Check authentication state.
- `BILIBILI --mcp-page` -- Show current page info.
- `BILIBILI --mcp-state` -- Get comprehensive MCP state.
- `BILIBILI --mcp-layout` -- Identify home page layout areas.

### Navigation
- `BILIBILI --mcp-navigate <target>` -- Navigate to a section or URL.
- `BILIBILI --mcp-open <BV_ID_or_URL>` -- Open a specific video.
- `BILIBILI --mcp-back` -- Navigate back to previous page.
- `BILIBILI --mcp-uploader` -- Navigate to current video's UP page.
- `BILIBILI --mcp-personal` -- Navigate to personal space.

#### Navigation Targets
`home`, `bangumi`, `live`, `anime`, `history`, `favorites`, `dynamics`, `trending`, `ranking`, `tech`, `science`, `game`, `music`, `dance`, `food`, `car`, `fashion`, `sports`, `settings`, or any URL.

### Search & Discovery
- `BILIBILI --mcp-search <query> [--limit N]` -- Search for videos.
- `BILIBILI --mcp-filter-search <query> [--duration X] [--sort Y] [--limit N]` -- Search with filters.
- `BILIBILI --mcp-trending [--limit N]` -- List trending/popular videos.
- `BILIBILI --mcp-history [--limit N]` -- View watch history.
- `BILIBILI --mcp-recommendations [--limit N]` -- List recommended videos.
- `BILIBILI --mcp-next` -- Play next recommended video.
- `BILIBILI --mcp-comments [--limit N]` -- Extract top comments (handles Shadow DOM).

### Playback Control
- `BILIBILI --mcp-play` / `BILIBILI --mcp-pause` -- Play or pause video.
- `BILIBILI --mcp-seek <target>` -- Seek to position: seconds, `mm:ss`, percentage, or relative.
- `BILIBILI --mcp-volume [level] [--mute] [--unmute]` -- Set volume or mute/unmute.
- `BILIBILI --mcp-speed [rate]` -- Set playback speed (0.5-2.0).
- `BILIBILI --mcp-auto-speed` -- Auto-adjust speed based on content type.
- `BILIBILI --mcp-quality [level]` -- List or set video quality.
- `BILIBILI --mcp-fullscreen` / `BILIBILI --mcp-widescreen` / `BILIBILI --mcp-pip` -- Toggle display modes.

### Chapters
- `BILIBILI --mcp-chapters` -- List video chapter markers.
- `BILIBILI --mcp-seek-chapter <index>` -- Seek to chapter by index.

### Subtitles
- `BILIBILI --mcp-subtitles` -- Check subtitle availability.
- `BILIBILI --mcp-toggle-subtitles [--on|--off]` -- Toggle subtitle display.

### Danmaku
- `BILIBILI --mcp-danmaku [--on|--off]` -- Toggle danmaku display.
- `BILIBILI --mcp-send-danmaku <text>` -- Send a danmaku message.
- `BILIBILI --mcp-danmaku-settings` -- View danmaku display configuration.
- `BILIBILI --mcp-danmaku-filter <keyword>` -- Add keyword to block list.
- `BILIBILI --mcp-danmaku-opacity <0-100>` -- Set danmaku opacity.

### Engagement
- `BILIBILI --mcp-like` -- Like current video.
- `BILIBILI --mcp-coin [--amount 1|2]` -- Throw coins.
- `BILIBILI --mcp-favorite` -- Add to favorites.
- `BILIBILI --mcp-triple` -- Triple combo (like + coin + favorite).
- `BILIBILI --mcp-share` -- Share current video.
- `BILIBILI --mcp-follow` -- Follow/unfollow UP.
- `BILIBILI --mcp-comment <text>` -- Post a comment.
- `BILIBILI --mcp-batch-reply <text> [--count N]` -- Batch reply to comments.

### Watch Later
- `BILIBILI --mcp-watchlater-add` -- Add current video to Watch Later.
- `BILIBILI --mcp-watchlater [--limit N]` -- List Watch Later videos.
- `BILIBILI --mcp-watchlater-play` -- Start continuous playback.

### Live Streaming
- `BILIBILI --mcp-live [--category C]` -- Navigate to Bilibili Live.
- `BILIBILI --mcp-live-enter [room_id]` -- Enter a live room.
- `BILIBILI --mcp-live-info` -- Get current live room info.
- `BILIBILI --mcp-live-danmaku <text>` -- Send live room danmaku.
- `BILIBILI --mcp-live-stats` -- Get live stream statistics.
- `BILIBILI --mcp-live-replays [--limit N]` -- Get past live replays.

### Content Creation
- `BILIBILI --mcp-creative [section]` -- Navigate to Creative Center.
- `BILIBILI --mcp-article-draft <title> [--content text]` -- Create article draft.
- `BILIBILI --mcp-inspiration [--category C]` -- Fetch creative inspiration topics.
- `BILIBILI --mcp-data-center` -- View data center overview.

### Favorites Management
- `BILIBILI --mcp-favorites-manage list` -- List favorite folders.
- `BILIBILI --mcp-favorites-manage create --name <name>` -- Create folder.

### Community
- `BILIBILI --mcp-post-dynamic <text> [--poll opt1 opt2 ...]` -- Post dynamic.
- `BILIBILI --mcp-fan-medal` -- Navigate to fan medal page.
- `BILIBILI --mcp-topic-challenge [query]` -- Navigate to topic challenges.

### Settings & Privacy
- `BILIBILI --mcp-privacy-settings` -- Navigate to privacy settings.
- `BILIBILI --mcp-privacy` -- Read privacy settings.
- `BILIBILI --mcp-notification-settings` -- Navigate to notification settings.
- `BILIBILI --mcp-notifications` -- Read notification settings.
- `BILIBILI --mcp-vip-page` -- Navigate to VIP page (no purchase).
- `BILIBILI --mcp-vip-benefits` -- Read VIP benefits.

### Utility
- `BILIBILI --mcp-screenshot [--output path]` -- Capture page screenshot.
- `BILIBILI --mcp-info [url]` -- Get video metadata.

## Built-in Commands

| Command | Description |
|---------|-------------|
| `--setup` | Run tool setup |
| `--test` | Run unit tests |
| `--dev <cmd>` | Developer commands |
| `--rule` | Show AI rules |

## Architecture

- Uses CDMCP session management for dedicated browser window isolation.
- State machine: UNINITIALIZED -> BOOTING -> IDLE <-> NAVIGATING <-> WATCHING / SEARCHING.
- Comment extraction handles Bilibili's nested Shadow DOM.
- Search uses polling for SPA lazy-loaded results.
- All MCP interactions use visual overlays via `interact` module.
