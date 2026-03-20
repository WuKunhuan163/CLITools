"""YOUTUBE Tool Interface — YouTube via API + CDMCP.

API-based (no browser needed):
  - api_search_videos(query) — search via YouTube Data API v3
  - api_get_video_info(video_id) — video metadata via API
  - api_get_comments(video_id) — comments via API
  - api_fetch_captions(video_id) — subtitles (no API key needed)
  - extract_video_id(url_or_id) — extract video ID from URL

CDMCP-based (browser automation):
  - get_auth_state() — check login status
  - search_videos(query) — search via browser
  - get_video_info(url) — video metadata via browser
  - take_screenshot(path) — capture page
  - get_transcript(url) — browser-based transcript extraction
  - fetch_subtitles_api(video_id) — API-based subtitle fetching
  - login() — navigate to sign-in
"""

from tool.YOUTUBE.logic.youtube_api import (  # noqa: F401
    search_videos as api_search_videos,
    get_video_info as api_get_video_info,
    get_video_comments as api_get_comments,
    fetch_captions as api_fetch_captions,
    extract_video_id,
)

from tool.YOUTUBE.logic.utils.chrome.api import (  # noqa: F401
    get_auth_state,
    get_page_info,
    search_videos,
    get_video_info,
    take_screenshot,
    get_transcript,
    fetch_subtitles_api,
    login,
)
