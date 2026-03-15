"""YouTube Data API v3 client — stdlib-only, no browser automation.

Provides search, video info, channel info, and caption/subtitle retrieval
using Google's official YouTube Data API. Requires a valid API key.

API key config:
    YOUTUBE config --api-key <YOUR_KEY>
    # or: export YOUTUBE_API_KEY=<key>

Reference: https://developers.google.com/youtube/v3/docs
"""
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree

API_BASE = "https://www.googleapis.com/youtube/v3"

_TOOL_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _TOOL_DIR / "data" / "config.json"


def _load_api_key() -> Optional[str]:
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key
    if _CONFIG_PATH.exists():
        try:
            cfg = json.loads(_CONFIG_PATH.read_text())
            return cfg.get("api_key")
        except Exception:
            pass
    return None


def _api_get(endpoint: str, params: Dict[str, str],
             api_key: Optional[str] = None) -> Dict[str, Any]:
    """Make a GET request to the YouTube Data API."""
    key = api_key or _load_api_key()
    if not key:
        return {"ok": False, "error": "No API key. Run: YOUTUBE config --api-key <key>"}

    params["key"] = key
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{endpoint}?{qs}"

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "data": data}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}", "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_videos(query: str, limit: int = 10,
                  api_key: Optional[str] = None) -> Dict[str, Any]:
    """Search YouTube videos via the Data API.

    Returns: {ok, results: [{title, channel, videoId, url, description, publishedAt}]}
    """
    resp = _api_get("search", {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": str(min(limit, 50)),
        "order": "relevance",
    }, api_key=api_key)

    if not resp["ok"]:
        return resp

    items = resp["data"].get("items", [])
    results = []
    for item in items:
        snippet = item.get("snippet", {})
        vid = item.get("id", {}).get("videoId", "")
        results.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "videoId": vid,
            "url": f"https://www.youtube.com/watch?v={vid}" if vid else "",
            "description": snippet.get("description", "")[:200],
            "publishedAt": snippet.get("publishedAt", ""),
        })

    return {"ok": True, "results": results, "count": len(results), "query": query}


def get_video_info(video_id: str,
                   api_key: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed video information via the Data API.

    Returns: {ok, title, channel, channelId, views, likes, comments,
              duration, publishedAt, description, tags, videoId}
    """
    resp = _api_get("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": video_id,
    }, api_key=api_key)

    if not resp["ok"]:
        return resp

    items = resp["data"].get("items", [])
    if not items:
        return {"ok": False, "error": f"Video not found: {video_id}"}

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    details = item.get("contentDetails", {})

    return {
        "ok": True,
        "title": snippet.get("title", ""),
        "channel": snippet.get("channelTitle", ""),
        "channelId": snippet.get("channelId", ""),
        "views": stats.get("viewCount", "0"),
        "likes": stats.get("likeCount", "0"),
        "comments": stats.get("commentCount", "0"),
        "duration": _parse_duration(details.get("duration", "")),
        "publishedAt": snippet.get("publishedAt", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", [])[:10],
        "videoId": video_id,
    }


def get_channel_info(channel_id: str,
                     api_key: Optional[str] = None) -> Dict[str, Any]:
    """Get channel information."""
    resp = _api_get("channels", {
        "part": "snippet,statistics",
        "id": channel_id,
    }, api_key=api_key)

    if not resp["ok"]:
        return resp

    items = resp["data"].get("items", [])
    if not items:
        return {"ok": False, "error": f"Channel not found: {channel_id}"}

    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    return {
        "ok": True,
        "title": snippet.get("title", ""),
        "description": snippet.get("description", "")[:300],
        "subscribers": stats.get("subscriberCount", "0"),
        "videos": stats.get("videoCount", "0"),
        "views": stats.get("viewCount", "0"),
        "channelId": channel_id,
    }


def get_video_comments(video_id: str, limit: int = 10,
                       api_key: Optional[str] = None) -> Dict[str, Any]:
    """Get top-level comments for a video."""
    resp = _api_get("commentThreads", {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": str(min(limit, 100)),
        "order": "relevance",
        "textFormat": "plainText",
    }, api_key=api_key)

    if not resp["ok"]:
        return resp

    items = resp["data"].get("items", [])
    comments = []
    for item in items:
        top = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comments.append({
            "author": top.get("authorDisplayName", ""),
            "text": top.get("textDisplay", ""),
            "likes": top.get("likeCount", 0),
            "publishedAt": top.get("publishedAt", ""),
        })

    return {"ok": True, "comments": comments, "count": len(comments)}


def fetch_captions(video_id: str) -> Dict[str, Any]:
    """Fetch auto-generated captions via YouTube's timedtext endpoint (no API key needed).

    Returns: {ok, lines: [{timestamp, text}], fullText, segments}
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AITerminalTools/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch page: {e}"}

    caption_url = _extract_caption_url(html)
    if not caption_url:
        return {"ok": False, "error": "No captions found for this video"}

    try:
        with urllib.request.urlopen(caption_url, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch captions: {e}"}

    return _parse_caption_xml(xml_data)


def _extract_caption_url(html: str) -> Optional[str]:
    """Extract the auto-caption track URL from YouTube page HTML."""
    match = re.search(r'"captionTracks":\s*(\[.*?\])', html)
    if not match:
        return None
    try:
        tracks = json.loads(match.group(1))
        for track in tracks:
            url = track.get("baseUrl", "")
            if url:
                return url
    except Exception:
        pass
    return None


def _parse_caption_xml(xml_data: str) -> Dict[str, Any]:
    """Parse YouTube's timedtext XML into structured lines."""
    try:
        root = ElementTree.fromstring(xml_data)
    except Exception as e:
        return {"ok": False, "error": f"Failed to parse caption XML: {e}"}

    lines = []
    full_text_parts = []
    for elem in root.findall(".//text"):
        start = float(elem.get("start", "0"))
        dur = float(elem.get("dur", "0"))
        text = (elem.text or "").strip()
        if text:
            mins, secs = divmod(int(start), 60)
            timestamp = f"{mins}:{secs:02d}"
            lines.append({"timestamp": timestamp, "start": start, "duration": dur, "text": text})
            full_text_parts.append(text)

    return {
        "ok": True,
        "lines": lines,
        "fullText": " ".join(full_text_parts),
        "segments": len(lines),
    }


def _parse_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M10S) to human-readable."""
    if not iso_duration:
        return ""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not m:
        return iso_duration
    h, mins, s = m.groups()
    parts = []
    if h:
        parts.append(f"{h}h")
    if mins:
        parts.append(f"{mins}m")
    if s:
        parts.append(f"{s}s")
    return "".join(parts) or "0s"


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a URL or return the ID if already bare."""
    if len(url_or_id) == 11 and re.match(r"^[\w-]+$", url_or_id):
        return url_or_id
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    return url_or_id
