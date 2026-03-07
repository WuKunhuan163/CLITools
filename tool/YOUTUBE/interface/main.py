"""YOUTUBE Tool Interface — YouTube automation via CDMCP.

Exposes YouTube operations for other tools:
  - get_auth_state() — check login status
  - search_videos(query) — search and return results
  - get_video_info(url) — video metadata
  - take_screenshot(path) — capture page
  - get_transcript(url) — browser-based transcript extraction
  - fetch_subtitles_api(video_id) — API-based subtitle fetching
  - login() — navigate to sign-in
"""

from tool.YOUTUBE.logic.chrome.api import (  # noqa: F401
    get_auth_state,
    get_page_info,
    search_videos,
    get_video_info,
    take_screenshot,
    get_transcript,
    fetch_subtitles_api,
    login,
)
