# YOUTUBE Logic — Technical Reference

## Architecture

Advanced CDMCP tool with session manager + state machine:
```
boot_session() -> CDMCP session
  -> YouTubeState FSM tracks lifecycle
  -> chrome/api.py methods control playback, navigation, data extraction
```

## chrome/api.py

Extensive API covering:
- **Session**: `boot_session()`, `get_session_status()`, `get_mcp_state()`
- **Auth**: `get_auth_state()`, `login()`
- **Navigation**: `navigate()`, `open_video()`, `go_back()`, `navigate_to_channel()`, `navigate_studio()`, `navigate_settings()`, `navigate_premium()`
- **Playback**: `play()`, `pause()`, `seek()`, `volume()`, `speed()`, `quality()`, `captions()`, `fullscreen()`, `theater()`, `autoplay()`, `pip()`
- **Search**: `search_videos()`, `search_with_filters()`
- **Video data**: `get_video_info()`, `get_transcript()`, `fetch_subtitles_api()`, `get_chapters()`, `seek_to_chapter()`, `get_comments()`, `expand_description()`
- **Social**: `like()`, `dislike()`, `subscribe()`, `share()`, `save()`, `comment()`
- **Browse**: `get_recommendations()`, `get_home_layout()`, `get_watch_history()`, `delete_history_item()`, `next_video()`
- **Live**: `find_live_streams()`, `get_live_stats()`
- **Playlists**: `create_playlist()`
- **Premium**: `get_premium_benefits()`
- **Other**: `take_screenshot()`, `apply_default_settings()`

## chrome/state_machine.py

Session lifecycle FSM with crash recovery:
- Persists state to disk for recovery after tab closure
- Sub-machine for transcript panel operations
- Multiple state machines can coexist (one per session)

## subtitle/

Transcript/subtitle extraction utilities for video content.

## Gotchas

1. **Session-based**: Uses `boot_session()`, not `find_youtube_tab()`.
2. **Many playback methods**: Each method controls a specific YouTube player feature via CDP DOM manipulation.
3. **Subtitle API**: `fetch_subtitles_api()` may use YouTube's internal `timedtext` API which can change without notice.
