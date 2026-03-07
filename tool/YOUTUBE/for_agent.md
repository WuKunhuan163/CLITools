# YOUTUBE — Agent Reference

## Quick Start
```
YOUTUBE status                                      # Auth state
YOUTUBE search "machine learning tutorial" --limit 5 # Search
YOUTUBE info https://www.youtube.com/watch?v=VIDEO_ID # Video details
YOUTUBE transcript                                   # Transcript of current video
YOUTUBE subtitles VIDEO_ID --save /tmp/subs.txt      # Save subtitles to file
YOUTUBE screenshot --output /tmp/yt.png              # Screenshot
```

## API Functions
- `search_videos(query, limit)` — Returns `{results: [{title, channel, views, duration, url, videoId}]}`
- `get_video_info(video_url)` — Returns `{title, channel, views, subscribers, date, description, likes, videoId}`
- `get_transcript(video_url)` — Returns `{segments, lines: [{timestamp, text}], fullText}`
- `fetch_subtitles_api(video_id)` — Same as transcript + `{availableLanguages, language, languageName}`
- `take_screenshot(output_path)` — Returns `{path, size}`
- `get_auth_state()` — Returns `{authenticated, channelName, title}`
- `login()` — Navigates to Google sign-in

## Workflow Pattern
1. `YOUTUBE status` — check if authenticated
2. `YOUTUBE search "query"` — find videos
3. `YOUTUBE info URL` — get details
4. `YOUTUBE transcript URL` — extract subtitles
5. `YOUTUBE screenshot` — capture visual state
