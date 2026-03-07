"""YouTube operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP session management for tab lifecycle and the Turing machine
state system for robust error handling and recovery.

Operations:
  - Auth state: check login status
  - Search: search for videos and return results
  - Video info: get title, channel, views, description
  - Screenshot: capture the current page
  - Transcript: extract subtitles from a video page
  - Session: boot / status / recover
  - Playback: play, pause, seek, volume, speed, quality, captions
  - Engagement: like, dislike, subscribe, share, save, comment
  - Navigation: home, shorts, subscriptions, history, playlists, video URL
  - State: comprehensive player + page state
  - Recommendations: list recommended videos / get comments
"""

import json
import re
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, List

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab, open_tab, list_tabs,
    capture_screenshot,
    real_click, insert_text,
)

from tool.YOUTUBE.logic.chrome.state_machine import (
    YouTubeStateMachine, YTState, TranscriptState, get_machine,
)

YOUTUBE_URL_PATTERN = "youtube.com"
YOUTUBE_HOME = "https://www.youtube.com"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _TOOL_DIR / "data"

_CDMCP_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "GOOGLE.CDMCP"
_OVERLAY_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_INTERACT_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "interact.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_overlay():
    return _load_module("cdmcp_overlay", _OVERLAY_PATH)


def _load_session_mgr():
    return _load_module("cdmcp_session_mgr", _SESSION_MGR_PATH)


def _load_interact():
    return _load_module("cdmcp_interact", _INTERACT_PATH)


# ---------------------------------------------------------------------------
# Session-aware tab management
# ---------------------------------------------------------------------------

_yt_session = None  # CDMCPSession instance
_session_name = "youtube"


def _get_or_create_session(port: int = CDP_PORT):
    """Get or create the YouTube CDMCP session."""
    global _yt_session
    if _yt_session is not None:
        cdp = _yt_session.get_cdp()
        if cdp:
            return _yt_session
        _yt_session = None

    sm = _load_session_mgr()
    existing = sm.get_session(_session_name)
    if existing:
        cdp = existing.get_cdp()
        if cdp:
            _yt_session = existing
            return existing
        sm.close_session(_session_name)

    return None


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a YouTube CDMCP session using the unified CDMCP boot interface."""
    global _yt_session
    machine = get_machine(_session_name)

    if machine.state not in (YTState.UNINITIALIZED, YTState.ERROR):
        existing = _get_or_create_session(port)
        if existing:
            return {"ok": True, "action": "already_booted", **machine.to_dict()}

    if machine.state == YTState.ERROR:
        machine.transition(YTState.RECOVERING)
        if not machine.can_recover():
            machine.reset()
        machine.transition(YTState.UNINITIALIZED)

    machine.transition(YTState.BOOTING, {"url": YOUTUBE_HOME})

    sm = _load_session_mgr()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)

    if not boot_result.get("ok"):
        machine.transition(YTState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _yt_session = boot_result.get("session")

    # Open YouTube in a new tab within the session window
    tab_info = _yt_session.require_tab(
        "youtube", url_pattern="youtube.com",
        open_url=YOUTUBE_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        overlay = _load_overlay()
        yt_cdp = CDPSession(tab_info["ws"])
        overlay.inject_favicon(yt_cdp, svg_color="#ff0000", letter="Y")
        overlay.inject_badge(yt_cdp, text="YouTube MCP", color="#ff0000")
        overlay.inject_focus(yt_cdp, color="#ff0000")

    machine.transition(YTState.IDLE)
    machine.set_url(YOUTUBE_HOME)

    return {"ok": True, "action": "booted", **machine.to_dict()}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Ensure we have a live YouTube tab. Boot session if needed, recover if broken."""
    global _yt_session
    machine = get_machine(_session_name)

    session = _get_or_create_session(port)
    if not session:
        if machine.state in (YTState.UNINITIALIZED,):
            result = boot_session(port)
            if not result.get("ok"):
                return None
            session = _get_or_create_session(port)
        elif machine.state == YTState.ERROR:
            result = _recover(port)
            if not result.get("ok"):
                return None
            session = _get_or_create_session(port)
        else:
            result = boot_session(port)
            if not result.get("ok"):
                return None
            session = _get_or_create_session(port)

    if not session:
        return None

    tab_info = session.require_tab(
        "youtube", url_pattern="youtube.com",
        open_url=YOUTUBE_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        cdp = CDPSession(tab_info["ws"])
        _reapply_overlays_if_needed(cdp, session, port)
        return cdp

    return None


def _reapply_overlays_if_needed(cdp: CDPSession, session, port: int = CDP_PORT):
    """Re-apply overlays after a tab recovery (badge may have been lost)."""
    try:
        has_badge = cdp.evaluate(f"!!document.getElementById('{_load_overlay().CDMCP_BADGE_ID}')")
        if not has_badge:
            overlay = _load_overlay()
            tab_id = session.lifetime_tab_id
            if tab_id:
                overlay.activate_tab(tab_id, port)
            overlay.inject_favicon(cdp, svg_color="#ff0000", letter="Y")
            overlay.inject_badge(cdp, text="YouTube MCP", color="#ff0000")
            overlay.inject_focus(cdp, color="#ff0000")
    except Exception:
        pass


def _recover(port: int = CDP_PORT) -> Dict[str, Any]:
    """Attempt to recover the YouTube session from an error/lost-tab state."""
    machine = get_machine(_session_name)

    if not machine.can_recover():
        machine.reset()
        return boot_session(port)

    if machine.state != YTState.RECOVERING:
        if not machine.transition(YTState.RECOVERING):
            machine.reset()
            return boot_session(port)

    target = machine.get_recovery_target()
    url = target.get("url", YOUTUBE_HOME)
    target_state = target.get("state", YTState.IDLE)

    result = boot_session(port)
    if not result.get("ok"):
        return result

    if url != YOUTUBE_HOME:
        cdp = _ensure_session(port)
        if cdp:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(3)
            machine.set_url(url)
            if target_state == YTState.WATCHING:
                machine.transition(YTState.NAVIGATING)
                machine.transition(YTState.WATCHING)
            elif target_state == YTState.SEARCHING:
                machine.transition(YTState.NAVIGATING)
                machine.transition(YTState.SEARCHING)

    return {"ok": True, "action": "recovered", "restored_to": url, **machine.to_dict()}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get full session and state machine status."""
    machine = get_machine(_session_name)
    session = _get_or_create_session(port)

    result = machine.to_dict()
    result["session_alive"] = session is not None
    if session:
        result["session_info"] = session.to_dict()
    result["cdp_available"] = is_chrome_cdp_available(port)
    return result


# ---------------------------------------------------------------------------
# Auth & page info
# ---------------------------------------------------------------------------

def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "No YouTube session"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var avatar = document.querySelector('#avatar-btn img, button#avatar-btn');
                var signInBtn = document.querySelector('a[href*="accounts.google.com/ServiceLogin"]');
                var channelName = '';
                try {
                    var nameEl = document.querySelector('#avatar-btn #img');
                    channelName = nameEl ? nameEl.getAttribute('alt') || '' : '';
                } catch(e) {}
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    authenticated: !!avatar && !signInBtn,
                    channelName: channelName,
                    hasSignInButton: !!signInBtn
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        machine = get_machine(_session_name)
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "authenticated": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var isVideo = url.includes('/watch');
                var isSearch = url.includes('/results');
                var isHome = url === 'https://www.youtube.com/' || url === 'https://www.youtube.com';
                var section = isVideo ? 'video' : (isSearch ? 'search' : (isHome ? 'home' : 'other'));
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    section: section,
                    isVideo: isVideo,
                    isSearch: isSearch
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        machine = get_machine(_session_name)
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_videos(query: str, limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search YouTube for videos with MCP visual interaction effects."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        machine.transition(YTState.NAVIGATING, {"action": "search", "query": query})
        interact = _load_interact()
        overlay = _load_overlay()

        # Navigate to YouTube home first if not there
        cur_url = session.evaluate("window.location.href") or ""
        if "youtube.com" not in str(cur_url):
            session.evaluate(f"window.location.href = {json.dumps(YOUTUBE_HOME)}")
            time.sleep(2)

        safe_q = query.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')

        # Type in search box with visual effect
        search_typed = interact.mcp_type(
            session, 'input#search, input[name="search_query"]', query,
            label=f"Search: {query}", char_delay=0.04, clear_first=True,
        )

        if search_typed.get("ok"):
            time.sleep(0.3)
            interact.mcp_click(
                session, '#search-icon-legacy, button[aria-label="Search"]',
                label="Search", dwell=0.5,
            )
            time.sleep(3)
        else:
            session.evaluate(f"window.location.href = 'https://www.youtube.com/results?search_query={safe_q}'")
            time.sleep(4)

        machine.set_url(f"https://www.youtube.com/results?search_query={safe_q}")
        machine.transition(YTState.SEARCHING)

        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll('ytd-video-renderer');
                    if (items.length === 0) items = document.querySelectorAll('ytd-rich-item-renderer');
                    var results = [];
                    for (var i = 0; i < Math.min(items.length, %d); i++) {
                        var item = items[i];
                        var titleEl = item.querySelector('#video-title, a#video-title-link');
                        var channelEl = item.querySelector('#channel-name a, .ytd-channel-name a, #text.ytd-channel-name');
                        var viewsEl = item.querySelector('#metadata-line span:first-child, .inline-metadata-item');
                        var timeEl = item.querySelector('#time-status span, ytd-thumbnail-overlay-time-status-renderer span');
                        var href = titleEl ? (titleEl.getAttribute('href') || '') : '';
                        var videoId = '';
                        var m = href.match(/[?&]v=([^&]+)/);
                        if (m) videoId = m[1];
                        results.push({
                            title: titleEl ? titleEl.textContent.trim().substring(0, 120) : '',
                            channel: channelEl ? channelEl.textContent.trim() : '',
                            views: viewsEl ? viewsEl.textContent.trim() : '',
                            duration: timeEl ? timeEl.textContent.trim() : '',
                            url: videoId ? 'https://www.youtube.com/watch?v=' + videoId : href,
                            videoId: videoId
                        });
                    }
                    return JSON.stringify({ok: true, query: '%s', count: results.length, results: results});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """ % (limit, safe_q))
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Video info
# ---------------------------------------------------------------------------

def get_video_info(video_url: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get detailed info about a video with MCP visual navigation effects."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        overlay = _load_overlay()

        if video_url:
            machine.transition(YTState.NAVIGATING, {"action": "video", "url": video_url})

            # If we're on search results, try to click the matching thumbnail
            cur_url = session.evaluate("window.location.href") or ""
            video_id = ""
            import re
            m = re.search(r'[?&]v=([^&]+)', video_url)
            if m:
                video_id = m.group(1)

            clicked_thumb = False
            if "/results" in str(cur_url) and video_id:
                click_r = interact.mcp_click(
                    session, f'a[href*="watch?v={video_id}"]',
                    label=f"Open video: {video_id}", dwell=1.0,
                    color="#ff0000",
                )
                if click_r.get("ok"):
                    clicked_thumb = True
                    time.sleep(2)

            if not clicked_thumb:
                interact.mcp_navigate(session, video_url)

            for _ in range(8):
                time.sleep(1)
                ready = session.evaluate("""
                    (function() {
                        var url = window.location.href;
                        if (!url.includes('/watch')) return 'not_video';
                        var title = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string, h1.title');
                        return title && title.textContent.trim() ? 'ready' : 'loading';
                    })()
                """)
                if ready == "ready":
                    break
            machine.set_url(video_url)
            machine.transition(YTState.WATCHING)

        r = session.evaluate("""
            (function() {
                try {
                    var url = window.location.href;
                    if (!url.includes('/watch')) {
                        return JSON.stringify({ok: false, error: 'Not on a video page'});
                    }
                    var titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, #title h1 yt-formatted-string, h1.title, ytd-watch-metadata h1');
                    var channelEl = document.querySelector('#channel-name a, ytd-channel-name a, #owner #channel-name yt-formatted-string a');
                    var subsEl = document.querySelector('#owner-sub-count, yt-formatted-string#owner-sub-count');
                    var viewsEl = document.querySelector('#info-strings yt-formatted-string, .view-count, ytd-watch-info-text yt-formatted-string span');
                    var dateEl = document.querySelector('#info-strings yt-formatted-string:last-child');
                    var descEl = document.querySelector('#description-inner, ytd-text-inline-expander #plain-snippet-text, #attributed-snippet-text span');
                    var likesEl = document.querySelector('like-button-view-model button .yt-spec-button-shape-next__button-text-content, #top-level-buttons-computed like-button-view-model button span, segmented-like-dislike-button-view-model like-button-view-model toggle-button-view-model button-view-model button .yt-spec-button-shape-next__button-text-content');
                    var vidId = url.match(/[?&]v=([^&]+)/);
                    var title = '';
                    if (titleEl) title = titleEl.textContent.trim();
                    if (!title) {
                        var dt = document.title || '';
                        title = dt.replace(/ - YouTube$/, '').trim();
                    }
                    return JSON.stringify({
                        ok: true,
                        url: url,
                        videoId: vidId ? vidId[1] : '',
                        title: title,
                        channel: channelEl ? channelEl.textContent.trim() : '',
                        subscribers: subsEl ? subsEl.textContent.trim() : '',
                        views: viewsEl ? viewsEl.textContent.trim() : '',
                        date: dateEl ? dateEl.textContent.trim() : '',
                        description: descEl ? descEl.textContent.trim().substring(0, 500) : '',
                        likes: likesEl ? likesEl.textContent.trim() : ''
                    });
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(output_path: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Capture a screenshot of the current YouTube page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        img_bytes = capture_screenshot(session)
        if not img_bytes:
            return {"ok": False, "error": "Screenshot failed"}

        if not output_path:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            output_path = str(_DATA_DIR / f"screenshot_{ts}.png")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        return {"ok": True, "path": output_path, "size": len(img_bytes)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Transcript / Subtitles (via page DOM)
# ---------------------------------------------------------------------------

def get_transcript(video_url: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract transcript/subtitles from a YouTube video page."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        if video_url:
            machine.transition(YTState.NAVIGATING, {"action": "transcript", "url": video_url})
            session.evaluate(f"window.location.href = {json.dumps(video_url)}")
            for _ in range(8):
                time.sleep(1)
                ready = session.evaluate("window.location.href.includes('/watch') ? 'yes' : 'no'")
                if ready == "yes":
                    break
            time.sleep(2)
            machine.set_url(video_url)
            machine.transition(YTState.WATCHING)

        url = session.evaluate("window.location.href") or ""
        if "/watch" not in str(url):
            return {"ok": False, "error": "Not on a video page"}

        machine.transition(YTState.TRANSCRIPT)
        machine.set_transcript_state(TranscriptState.OPENING)

        session.evaluate("""
            (function() {
                var btn = document.querySelector('#expand, tp-yt-paper-button#expand, #description-inline-expander #expand');
                if (btn) btn.click();
            })()
        """)
        time.sleep(1)
        machine.set_transcript_state(TranscriptState.EXPANDED)

        session.evaluate("""
            (function() {
                var all = document.querySelectorAll('button, ytd-button-renderer');
                for (var i = 0; i < all.length; i++) {
                    var t = all[i].textContent.trim().toLowerCase();
                    if (t.includes('show transcript')) {
                        all[i].click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()
        """)
        time.sleep(1)

        session.evaluate("""
            (function() {
                var panel = document.querySelector('ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"]');
                if (panel) {
                    panel.setAttribute('visibility', 'ENGAGEMENT_PANEL_VISIBILITY_EXPANDED');
                    panel.style.display = '';
                }
            })()
        """)

        machine.set_transcript_state(TranscriptState.READING)

        for _ in range(8):
            time.sleep(1)
            count = session.evaluate("document.querySelectorAll('ytd-transcript-segment-renderer').length")
            if count and int(count) > 0:
                break

        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll('ytd-transcript-segment-renderer');
                    if (items.length === 0) {
                        return JSON.stringify({ok: false, error: 'No transcript segments found. Transcript may not be available for this video.'});
                    }
                    var lines = [];
                    items.forEach(function(seg) {
                        var ts = seg.querySelector('.segment-timestamp');
                        var txt = seg.querySelector('.segment-text');
                        lines.push({
                            timestamp: ts ? ts.textContent.trim() : '',
                            text: txt ? txt.textContent.trim() : seg.textContent.trim()
                        });
                    });
                    var fullText = lines.map(function(l) {
                        return (l.timestamp ? l.timestamp + ' ' : '') + l.text;
                    }).join('\\n');
                    return JSON.stringify({
                        ok: true,
                        segments: lines.length,
                        lines: lines,
                        fullText: fullText.substring(0, 50000)
                    });
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)

        machine.set_transcript_state(TranscriptState.DONE)

        result = json.loads(r) if r else {"ok": False, "error": "No response"}
        if result.get("ok"):
            machine.transition(YTState.WATCHING)
        return result
    except Exception as e:
        machine.transition(YTState.ERROR, {"error": str(e)})
        machine.set_transcript_state(TranscriptState.ERROR)
        return {"ok": False, "error": str(e)}


def fetch_subtitles_api(video_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch subtitles for a YouTube video via the browser's transcript panel."""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    result = get_transcript(video_url=video_url, port=port)
    if not result.get("ok"):
        return result

    session = _ensure_session(port)
    if session:
        try:
            lang_raw = session.evaluate("""
                (function() {
                    try {
                        var pr = window.ytInitialPlayerResponse;
                        if (!pr || !pr.captions) return JSON.stringify({tracks: []});
                        var renderer = pr.captions.playerCaptionsTracklistRenderer;
                        if (!renderer) return JSON.stringify({tracks: []});
                        var tracks = (renderer.captionTracks || []).map(function(t) {
                            var name = '';
                            if (t.name && t.name.simpleText) name = t.name.simpleText;
                            else if (t.name && t.name.runs) name = t.name.runs.map(r => r.text).join('');
                            return {code: t.languageCode, name: name, kind: t.kind || ''};
                        });
                        return JSON.stringify({tracks: tracks});
                    } catch(e) {
                        return JSON.stringify({tracks: []});
                    }
                })()
            """)
            lang_data = json.loads(lang_raw) if lang_raw else {"tracks": []}
            result["videoId"] = video_id
            result["availableLanguages"] = lang_data.get("tracks", [])
            for t in lang_data.get("tracks", []):
                if t.get("kind") != "asr":
                    result["language"] = t.get("code", "")
                    result["languageName"] = t.get("name", "")
                    break
        except Exception:
            pass

    result["videoId"] = video_id
    return result


# ---------------------------------------------------------------------------
# Login (navigate to sign-in page)
# ---------------------------------------------------------------------------

def login(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to YouTube's sign-in flow."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        machine.transition(YTState.NAVIGATING, {"action": "login"})
        session.evaluate("window.location.href = 'https://accounts.google.com/ServiceLogin?service=youtube'")
        time.sleep(3)
        url = session.evaluate("window.location.href") or ""
        machine.set_url(str(url))
        machine.transition(YTState.IDLE)
        return {
            "ok": True,
            "url": str(url),
            "action": "Navigated to sign-in page. Complete login in the browser.",
        }
    except Exception as e:
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

_NAV_TARGETS = {
    "home": "https://www.youtube.com",
    "shorts": "https://www.youtube.com/shorts",
    "subscriptions": "https://www.youtube.com/feed/subscriptions",
    "history": "https://www.youtube.com/feed/history",
    "playlists": "https://www.youtube.com/feed/playlists",
    "watch_later": "https://www.youtube.com/playlist?list=WL",
    "liked": "https://www.youtube.com/playlist?list=LL",
    "trending": "https://www.youtube.com/feed/trending",
    "library": "https://www.youtube.com/feed/library",
}


def navigate(target: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a YouTube section or URL.

    target can be a named section (home, shorts, subscriptions, history,
    playlists, watch_later, liked, trending, library) or a full URL.
    """
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        url = _NAV_TARGETS.get(target.lower(), target)
        if not url.startswith("http"):
            return {"ok": False, "error": f"Unknown target: {target}"}

        machine.transition(YTState.NAVIGATING, {"action": "navigate", "target": target})
        interact = _load_interact()
        interact.mcp_navigate(session, url, tool_name="YouTube")
        time.sleep(3)

        actual = session.evaluate("window.location.href") or url
        machine.set_url(str(actual))

        if "/watch" in str(actual):
            machine.transition(YTState.WATCHING)
        elif "/results" in str(actual):
            machine.transition(YTState.SEARCHING)
        else:
            machine.transition(YTState.IDLE)

        return {"ok": True, "url": str(actual), "target": target}
    except Exception as e:
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def open_video(video_url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open a specific video by URL or ID with MCP effects."""
    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url}"
    return navigate(video_url, port)


# ---------------------------------------------------------------------------
# Playback controls — all use keyboard shortcuts for reliability
# ---------------------------------------------------------------------------

def _send_key(session: CDPSession, key: str, code: str = "",
              modifiers: int = 0, text: str = ""):
    """Send a keyboard event to the page."""
    from logic.chrome.session import dispatch_key
    dispatch_key(session, key, code or f"Key{key.upper()}", modifiers, text)


def _player_js(session: CDPSession, js: str) -> Any:
    """Evaluate JS in the context of the video player."""
    return session.evaluate(f"""
        (function(){{
            var v = document.querySelector('video');
            if(!v) return JSON.stringify({{ok: false, error: 'No video element'}});
            {js}
        }})()
    """)


def play(port: int = CDP_PORT) -> Dict[str, Any]:
    """Play the current video (keyboard shortcut k)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        paused = _player_js(session, "return v.paused ? 'yes' : 'no'")
        if paused == "yes":
            interact = _load_interact()
            interact.mcp_click(session, ".ytp-play-button",
                               label="Play", dwell=0.5, color="#ff0000",
                               tool_name="YouTube")
        return {"ok": True, "action": "play", "was_paused": paused == "yes"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pause(port: int = CDP_PORT) -> Dict[str, Any]:
    """Pause the current video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        paused = _player_js(session, "return v.paused ? 'yes' : 'no'")
        if paused == "no":
            interact = _load_interact()
            interact.mcp_click(session, ".ytp-play-button",
                               label="Pause", dwell=0.5, color="#ff0000",
                               tool_name="YouTube")
        return {"ok": True, "action": "pause", "was_playing": paused == "no"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def seek(target: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Seek to a position. target can be seconds (e.g. '90'), mm:ss (e.g. '1:30'),
    percentage (e.g. '50%'), or relative ('+10', '-10')."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        target = target.strip()
        if target.endswith("%"):
            pct = float(target[:-1]) / 100
            r = _player_js(session, f"v.currentTime = v.duration * {pct}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime, duration: v.duration}})")
        elif target.startswith("+") or target.startswith("-"):
            delta = float(target)
            r = _player_js(session, f"v.currentTime += {delta}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        elif ":" in target:
            parts = target.split(":")
            secs = sum(int(p) * (60 ** i) for i, p in enumerate(reversed(parts)))
            r = _player_js(session, f"v.currentTime = {secs}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        else:
            secs = float(target)
            r = _player_js(session, f"v.currentTime = {secs}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        result = json.loads(r) if r else {"ok": False, "error": "No video"}
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def volume(level: Optional[int] = None, mute: Optional[bool] = None,
           port: int = CDP_PORT) -> Dict[str, Any]:
    """Set volume (0-100) and/or mute state. If no args, returns current state."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        if mute is not None:
            _player_js(session, f"v.muted = {'true' if mute else 'false'}")
        if level is not None:
            clamped = max(0, min(100, level))
            _player_js(session, f"v.volume = {clamped / 100}")

        r = _player_js(session,
            "return JSON.stringify({ok:true, volume: Math.round(v.volume*100), muted: v.muted})")
        return json.loads(r) if r else {"ok": False, "error": "No video"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def speed(rate: Optional[float] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set playback speed (0.25-2.0). If no rate, returns current speed."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        if rate is not None:
            clamped = max(0.25, min(2.0, rate))
            _player_js(session, f"v.playbackRate = {clamped}")

        r = _player_js(session,
            "return JSON.stringify({ok:true, speed: v.playbackRate})")
        return json.loads(r) if r else {"ok": False, "error": "No video"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def quality(level: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set or get video quality. Opens settings gear to list/select quality.

    level examples: '1080p', '720p', '480p', '360p', '240p', '144p', 'auto'
    """
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()

        interact.mcp_click(session, ".ytp-settings-button",
                           label="Settings", dwell=0.5, tool_name="YouTube")
        time.sleep(0.8)

        interact.mcp_click(session, ".ytp-menuitem[aria-haspopup='true']:last-child, "
                           ".ytp-panel-menu .ytp-menuitem:last-child",
                           label="Quality", dwell=0.5, tool_name="YouTube")
        time.sleep(0.8)

        items = session.evaluate("""
            (function(){
                var items = document.querySelectorAll('.ytp-quality-menu .ytp-menuitem, '
                    + '.ytp-panel-menu .ytp-menuitem');
                var out = [];
                for(var i=0; i<items.length; i++){
                    var label = items[i].querySelector('.ytp-menuitem-label');
                    var text = label ? label.textContent.trim() : items[i].textContent.trim();
                    out.push(text);
                }
                return JSON.stringify(out);
            })()
        """)
        available = json.loads(items) if items else []

        if level:
            target_text = level.lower().replace("p", "")
            clicked = session.evaluate(f"""
                (function(){{
                    var items = document.querySelectorAll('.ytp-quality-menu .ytp-menuitem, '
                        + '.ytp-panel-menu .ytp-menuitem');
                    for(var i=0; i<items.length; i++){{
                        var t = items[i].textContent.trim().toLowerCase();
                        if(t.includes('{target_text}')){{
                            items[i].click();
                            return 'clicked';
                        }}
                    }}
                    return 'not_found';
                }})()
            """)
            if clicked == "not_found":
                session.evaluate("document.querySelector('.ytp-settings-button')?.click()")
                return {"ok": False, "error": f"Quality '{level}' not found",
                        "available": available}
        else:
            session.evaluate("document.querySelector('.ytp-settings-button')?.click()")

        return {"ok": True, "available": available,
                "selected": level if level else "current"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def captions(toggle: Optional[bool] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle or check subtitles/captions state."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        current = session.evaluate("""
            (function(){
                var btn = document.querySelector('.ytp-subtitles-button');
                if(!btn) return 'unavailable';
                return btn.getAttribute('aria-pressed') === 'true' ? 'on' : 'off';
            })()
        """)
        if current == "unavailable":
            return {"ok": True, "captions": "unavailable"}

        if toggle is not None:
            want_on = toggle
            is_on = current == "on"
            if want_on != is_on:
                interact = _load_interact()
                interact.mcp_click(session, ".ytp-subtitles-button",
                                   label="Captions", dwell=0.5,
                                   tool_name="YouTube")

        current_after = session.evaluate("""
            var btn = document.querySelector('.ytp-subtitles-button');
            btn ? (btn.getAttribute('aria-pressed') === 'true' ? 'on' : 'off') : 'unavailable'
        """)
        return {"ok": True, "captions": current_after}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fullscreen(port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle fullscreen mode."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        interact.mcp_click(session, ".ytp-fullscreen-button",
                           label="Fullscreen", dwell=0.3, tool_name="YouTube")
        return {"ok": True, "action": "fullscreen_toggled"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def theater(port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle theater mode."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        interact.mcp_click(session, ".ytp-size-button",
                           label="Theater mode", dwell=0.3, tool_name="YouTube")
        return {"ok": True, "action": "theater_toggled"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def autoplay(toggle: Optional[bool] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle or check autoplay state."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        current = session.evaluate("""
            var btn = document.querySelector('.ytp-autonav-toggle');
            btn ? (btn.getAttribute('aria-label') || '').toLowerCase() : 'not_found'
        """) or ""
        is_on = "on" in str(current).lower()

        if toggle is not None and toggle != is_on:
            interact = _load_interact()
            interact.mcp_click(session, ".ytp-autonav-toggle",
                               label="Autoplay", dwell=0.5, tool_name="YouTube")

        return {"ok": True, "autoplay": is_on if toggle is None else toggle}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pip(port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle picture-in-picture mode."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        r = _player_js(session, """
            if(document.pictureInPictureElement) {
                document.exitPictureInPicture();
                return JSON.stringify({ok:true, pip: false});
            } else {
                v.requestPictureInPicture();
                return JSON.stringify({ok:true, pip: true});
            }
        """)
        return json.loads(r) if r else {"ok": False, "error": "No video"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Engagement actions (like, subscribe, share, save, comment)
# ---------------------------------------------------------------------------

def like(port: int = CDP_PORT) -> Dict[str, Any]:
    """Like the current video with MCP effects."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        selectors = [
            "like-button-view-model button",
            "#segmented-like-button button",
            "ytd-toggle-button-renderer#like-button button",
        ]
        for sel in selectors:
            r = interact.mcp_click(session, sel, label="Like", dwell=1.0,
                                   color="#065fd4", tool_name="YouTube")
            if r.get("ok"):
                time.sleep(0.5)
                aria = session.evaluate(f"""
                    var b = document.querySelector('{sel}');
                    b ? b.getAttribute('aria-pressed') || b.getAttribute('aria-label') || '' : ''
                """)
                return {"ok": True, "action": "liked", "state": str(aria)[:60]}
        return {"ok": False, "error": "Like button not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def dislike(port: int = CDP_PORT) -> Dict[str, Any]:
    """Dislike the current video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        selectors = [
            "dislike-button-view-model button",
            "#segmented-dislike-button button",
        ]
        for sel in selectors:
            r = interact.mcp_click(session, sel, label="Dislike", dwell=1.0,
                                   color="#065fd4", tool_name="YouTube")
            if r.get("ok"):
                return {"ok": True, "action": "disliked"}
        return {"ok": False, "error": "Dislike button not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def subscribe(port: int = CDP_PORT) -> Dict[str, Any]:
    """Subscribe to the current video's channel."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        r = interact.mcp_click(
            session, "ytd-subscribe-button-renderer button",
            label="Subscribe", dwell=1.0, color="#cc0000", tool_name="YouTube")
        if r.get("ok"):
            time.sleep(0.5)
            text = session.evaluate(
                "document.querySelector('ytd-subscribe-button-renderer button')?.textContent?.trim() || ''")
            return {"ok": True, "action": "subscribe_toggled", "button_text": str(text)}
        return {"ok": False, "error": "Subscribe button not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def share(port: int = CDP_PORT) -> Dict[str, Any]:
    """Open share dialog and extract the share URL."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        r = interact.mcp_click(session, 'button[aria-label="Share"]',
                               label="Share", dwell=0.8, tool_name="YouTube")
        if not r.get("ok"):
            r = interact.mcp_click(
                session,
                'ytd-button-renderer:has(yt-icon) button',
                label="Share", dwell=0.8, tool_name="YouTube")

        time.sleep(1.5)

        url = session.evaluate("""
            (function(){
                var input = document.querySelector('#share-url, ytd-unified-share-panel-renderer input');
                if(input) return input.value || input.getAttribute('value') || '';
                var link = document.querySelector('a.yt-simple-endpoint[href*="youtu.be"]');
                if(link) return link.href;
                return '';
            })()
        """)

        session.evaluate("""
            var close = document.querySelector('ytd-unified-share-panel-renderer yt-icon-button, '
                + '#share-dialog yt-icon-button[aria-label="Close"]');
            if(close) close.click();
        """)

        return {"ok": True, "share_url": str(url) if url else "",
                "action": "share_dialog_opened"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save(playlist: str = "Watch later", port: int = CDP_PORT) -> Dict[str, Any]:
    """Save current video to a playlist (default: Watch later)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        r = interact.mcp_click(
            session, 'button[aria-label="Save to playlist"]',
            label="Save", dwell=0.8, tool_name="YouTube")
        if not r.get("ok"):
            r = interact.mcp_click(session,
                '#flexible-item-buttons ytd-button-renderer:last-child button',
                label="Save", dwell=0.8, tool_name="YouTube")

        time.sleep(1.5)

        if playlist.lower() == "watch later":
            clicked = session.evaluate("""
                (function(){
                    var items = document.querySelectorAll('ytd-playlist-add-to-option-renderer, '
                        + '#playlists tp-yt-paper-checkbox');
                    for(var i=0; i<items.length; i++){
                        if(items[i].textContent.trim().includes('Watch later')){
                            items[i].click();
                            return 'clicked';
                        }
                    }
                    return 'not_found';
                })()
            """)
        else:
            safe_pl = playlist.replace("'", "\\'")
            clicked = session.evaluate(f"""
                (function(){{
                    var items = document.querySelectorAll('ytd-playlist-add-to-option-renderer, '
                        + '#playlists tp-yt-paper-checkbox');
                    for(var i=0; i<items.length; i++){{
                        if(items[i].textContent.trim().includes('{safe_pl}')){{
                            items[i].click();
                            return 'clicked';
                        }}
                    }}
                    return 'not_found';
                }})()
            """)

        time.sleep(0.5)
        session.evaluate("""
            var close = document.querySelector('#close-button button, '
                + 'ytd-add-to-playlist-renderer yt-icon-button');
            if(close) close.click();
        """)

        return {"ok": True, "playlist": playlist,
                "saved": clicked == "clicked"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def comment(text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a comment to the current video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()

        interact.mcp_scroll(session, "down", 400)
        time.sleep(1)

        r = interact.mcp_click(
            session, "#simplebox-placeholder, #placeholder-area",
            label="Comment box", dwell=0.8, color="#065fd4",
            tool_name="YouTube")
        time.sleep(1)

        interact.mcp_type(
            session,
            "#contenteditable-root, #comment-input #contenteditable-root, "
            "div[contenteditable=\"true\"]",
            text, label=f"Comment: {text[:30]}",
            char_delay=0.03, tool_name="YouTube")
        time.sleep(0.5)

        interact.mcp_click(
            session, "#submit-button button, #submit-button ytd-button-renderer button",
            label="Submit comment", dwell=0.8, color="#065fd4",
            tool_name="YouTube")

        return {"ok": True, "action": "commented", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Next video / recommendation interaction
# ---------------------------------------------------------------------------

def next_video(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to the next recommended video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        machine = get_machine(_session_name)
        machine.transition(YTState.NAVIGATING, {"action": "next_video"})

        r = interact.mcp_click(
            session,
            "ytd-compact-video-renderer:first-of-type a#thumbnail",
            label="Next video", dwell=1.0, color="#ff0000",
            tool_name="YouTube")
        if not r.get("ok"):
            r = interact.mcp_click(
                session,
                ".ytp-next-button",
                label="Next", dwell=0.5, tool_name="YouTube")

        time.sleep(3)
        url = session.evaluate("window.location.href") or ""
        machine.set_url(str(url))
        machine.transition(YTState.WATCHING)
        return {"ok": True, "url": str(url)}
    except Exception as e:
        machine = get_machine(_session_name)
        machine.transition(YTState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_recommendations(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """List recommended videos from the sidebar."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('ytd-compact-video-renderer');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var a = el.querySelector('a#thumbnail');
                    var title = el.querySelector('#video-title');
                    var chan = el.querySelector('#channel-name #text, .ytd-channel-name');
                    var views = el.querySelector('#metadata-line span:first-child');
                    var dur = el.querySelector('#overlays span');
                    var href = a ? a.getAttribute('href') || '' : '';
                    var vid = href.match(/v=([^&]+)/);
                    out.push({{
                        title: title ? title.textContent.trim().substring(0, 100) : '',
                        channel: chan ? chan.textContent.trim() : '',
                        views: views ? views.textContent.trim() : '',
                        duration: dur ? dur.textContent.trim() : '',
                        videoId: vid ? vid[1] : '',
                        url: vid ? 'https://www.youtube.com/watch?v=' + vid[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_comments(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract top comments from the current video page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        interact.mcp_scroll(session, "down", 500)
        time.sleep(2)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('ytd-comment-thread-renderer');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var author = el.querySelector('#author-text span, #header-author h3 a span');
                    var text = el.querySelector('#content-text, yt-attributed-string#content-text');
                    var likes = el.querySelector('#vote-count-middle');
                    var time = el.querySelector('#published-time-text a, .published-time-text a');
                    var replies = el.querySelector('#more-replies button, #reply-count-text');
                    out.push({{
                        author: author ? author.textContent.trim() : '',
                        text: text ? text.textContent.trim().substring(0, 300) : '',
                        likes: likes ? likes.textContent.trim() : '0',
                        time: time ? time.textContent.trim() : '',
                        reply_count: replies ? replies.textContent.trim() : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, comments: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Description expand/collapse
# ---------------------------------------------------------------------------

def expand_description(port: int = CDP_PORT) -> Dict[str, Any]:
    """Expand the video description."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()
        r = interact.mcp_click(
            session, "#description-inline-expander #expand, "
            "tp-yt-paper-button#expand, #expand",
            label="Expand description", dwell=0.5, tool_name="YouTube")
        if r.get("ok"):
            time.sleep(0.5)
            desc = session.evaluate("""
                var d = document.querySelector('#description-inner, '
                    + 'ytd-text-inline-expander #plain-snippet-text, '
                    + '#attributed-snippet-text');
                d ? d.textContent.trim().substring(0, 2000) : ''
            """)
            return {"ok": True, "description": str(desc) if desc else ""}
        return r
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Comprehensive MCP state
# ---------------------------------------------------------------------------

def get_mcp_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get comprehensive state of the YouTube page + player."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        machine = get_machine(_session_name)
        r = session.evaluate("""
            (function(){
                var out = {};
                out.url = window.location.href;
                out.title = document.title;
                out.section = out.url.includes('/watch') ? 'video'
                    : out.url.includes('/results') ? 'search'
                    : out.url.includes('/shorts') ? 'shorts'
                    : 'other';

                var v = document.querySelector('video');
                if(v){
                    out.player = {
                        paused: v.paused,
                        currentTime: Math.round(v.currentTime * 10) / 10,
                        duration: Math.round(v.duration * 10) / 10,
                        volume: Math.round(v.volume * 100),
                        muted: v.muted,
                        playbackRate: v.playbackRate,
                        readyState: v.readyState,
                        ended: v.ended,
                        loop: v.loop
                    };
                    out.player.progress_pct = out.player.duration > 0
                        ? Math.round(v.currentTime / v.duration * 1000) / 10 : 0;
                }

                var titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string, h1 yt-formatted-string');
                out.video_title = titleEl ? titleEl.textContent.trim() : '';

                var chanEl = document.querySelector('#channel-name a, ytd-channel-name a');
                out.channel = chanEl ? chanEl.textContent.trim() : '';

                var subBtn = document.querySelector('ytd-subscribe-button-renderer button');
                out.subscribed = subBtn ? subBtn.textContent.trim() : '';

                var likeBtn = document.querySelector('like-button-view-model button');
                out.like_aria = likeBtn ? likeBtn.getAttribute('aria-label') || '' : '';
                out.like_pressed = likeBtn ? likeBtn.getAttribute('aria-pressed') : '';

                var captionBtn = document.querySelector('.ytp-subtitles-button');
                out.captions = captionBtn
                    ? (captionBtn.getAttribute('aria-pressed') === 'true' ? 'on' : 'off') : 'n/a';

                var autoBtn = document.querySelector('.ytp-autonav-toggle');
                out.autoplay = autoBtn ? autoBtn.getAttribute('aria-label') : '';

                var avatar = document.querySelector('#avatar-btn img');
                out.authenticated = !!avatar;

                var recs = document.querySelectorAll('ytd-compact-video-renderer');
                out.recommendation_count = recs.length;

                var comments = document.querySelectorAll('ytd-comment-thread-renderer');
                out.comment_count = comments.length;

                var countEl = document.querySelector('#count yt-formatted-string');
                out.total_comments = countEl ? countEl.textContent.trim() : '';

                return JSON.stringify(out);
            })()
        """)
        state = json.loads(r) if r else {}
        state["machine_state"] = machine.to_dict()
        state["ok"] = True
        return state
    except Exception as e:
        return {"ok": False, "error": str(e)}
