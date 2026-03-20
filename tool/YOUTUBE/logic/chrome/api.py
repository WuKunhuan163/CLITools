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
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    capture_screenshot,
)

from tool.YOUTUBE.logic.utils.chrome.state_machine import (
    YTState, TranscriptState, get_machine,
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
        session.touch()

        # Health check: detect stale tabs where content stops rendering
        try:
            url = cdp.evaluate("window.location.href") or ""
            if "youtube.com" in str(url) and url != YOUTUBE_HOME + "/":
                html_len = cdp.evaluate("document.documentElement.innerHTML.length")
                text_len = cdp.evaluate(
                    "(document.querySelector('ytd-app')||{}).innerText?.length||0")
                if html_len and int(html_len) > 50000 and (not text_len or int(text_len) == 0):
                    # Tab has HTML but no rendered text — stale tab
                    cdp.evaluate("window.location.reload(true)")
                    time.sleep(3)
                    for _ in range(10):
                        text_len = cdp.evaluate(
                            "(document.querySelector('ytd-app')||{}).innerText?.length||0")
                        if text_len and int(text_len) > 0:
                            break
                        time.sleep(1)
        except Exception:
            pass

        _reapply_overlays_if_needed(cdp, session, port)
        return cdp

    return None


def _reapply_overlays_if_needed(cdp: CDPSession, session, port: int = CDP_PORT):
    """Re-apply overlays after a tab recovery (badge may have been lost)."""
    try:
        has_badge = cdp.evaluate(f"!!document.getElementById('{_load_overlay().CDMCP_BADGE_ID}')")
        if not has_badge:
            overlay = _load_overlay()
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

        import urllib.parse
        encoded_q = urllib.parse.quote_plus(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_q}"

        interact.mcp_navigate(session, search_url, tool_name="YouTube")

        # Poll for search results to render (YouTube SPA can be slow)
        for _wait in range(20):
            time.sleep(1)
            n = session.evaluate(
                "document.querySelectorAll('ytd-video-renderer').length")
            if n and int(n) > 0:
                break

        machine.set_url(search_url)
        machine.transition(YTState.SEARCHING)

        js_limit = int(limit)
        js_query = json.dumps(query)
        r = session.evaluate(f"""
            (function() {{
                try {{
                    var qStr = {js_query};
                    var maxResults = {js_limit};
                    var items = document.querySelectorAll('ytd-video-renderer');
                    if (items.length === 0) items = document.querySelectorAll('ytd-rich-item-renderer');
                    var results = [];
                    for (var i = 0; i < Math.min(items.length, maxResults); i++) {{
                        var item = items[i];
                        var titleEl = item.querySelector('#video-title, a#video-title-link');
                        var channelEl = item.querySelector('#channel-name a, .ytd-channel-name a, #text.ytd-channel-name');
                        var viewsEl = item.querySelector('#metadata-line span:first-child, .inline-metadata-item');
                        var timeEl = item.querySelector('#time-status span, ytd-thumbnail-overlay-time-status-renderer span');
                        var href = titleEl ? (titleEl.getAttribute('href') || '') : '';
                        var videoId = '';
                        var m = href.match(/[?&]v=([^&]+)/);
                        if (m) videoId = m[1];
                        if (!videoId) {{
                            var s = href.match(/\\/shorts\\/([^?&]+)/);
                            if (s) videoId = s[1];
                        }}
                        var fullUrl = videoId
                            ? (href.includes('/shorts/') ? 'https://www.youtube.com/shorts/' + videoId
                               : 'https://www.youtube.com/watch?v=' + videoId)
                            : (href.startsWith('/') ? 'https://www.youtube.com' + href : href);
                        results.push({{
                            title: titleEl ? titleEl.textContent.trim().substring(0, 120) : '',
                            channel: channelEl ? channelEl.textContent.trim() : '',
                            views: viewsEl ? viewsEl.textContent.trim() : '',
                            duration: timeEl ? timeEl.textContent.trim() : '',
                            url: fullUrl,
                            videoId: videoId
                        }});
                    }}
                    return JSON.stringify({{ok: true, query: qStr, count: results.length, results: results}});
                }} catch(e) {{
                    return JSON.stringify({{ok: false, error: e.toString()}});
                }}
            }})()
        """)
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

        if video_url:
            machine.transition(YTState.NAVIGATING, {"action": "video", "url": video_url})

            cur_url = session.evaluate("window.location.href") or ""
            video_id = ""
            vid_match = re.search(r'[?&]v=([^&]+)', video_url)
            if vid_match:
                video_id = vid_match.group(1)

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

            for _ in range(12):
                time.sleep(1)
                ready = session.evaluate("""
                    (function() {
                        var url = window.location.href;
                        if (!url.includes('/watch')) return 'not_video';
                        var ch = document.querySelector('#channel-name a, ytd-channel-name a');
                        return ch && ch.textContent.trim() ? 'ready' : 'loading';
                    })()
                """)
                if ready == "ready":
                    break
            machine.set_url(video_url)
            machine.transition(YTState.WATCHING)
        else:
            # When no URL given, wait briefly for metadata to be available
            for _ in range(5):
                has_meta = session.evaluate("""
                    (function() {
                        var ch = document.querySelector('#channel-name a, ytd-channel-name a');
                        return ch && ch.textContent.trim() ? 'yes' : 'no';
                    })()
                """)
                if has_meta == "yes":
                    break
                time.sleep(1)

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
                        desc: descEl ? descEl.textContent.trim().substring(0, 500) : '',
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

        # Wait for description expand button to be available
        for _ in range(10):
            has_expand = session.evaluate(
                "!!document.querySelector('#expand, tp-yt-paper-button#expand, "
                "#description-inline-expander #expand')")
            if has_expand:
                break
            time.sleep(1)

        session.evaluate("""
            (function() {
                var btn = document.querySelector('#expand, tp-yt-paper-button#expand, #description-inline-expander #expand');
                if (btn) btn.click();
            })()
        """)
        time.sleep(1)
        machine.set_transcript_state(TranscriptState.EXPANDED)

        # Wait for "Show transcript" button to appear
        for _ in range(8):
            found = session.evaluate("""
                (function() {
                    var all = document.querySelectorAll('button, ytd-button-renderer');
                    for (var i = 0; i < all.length; i++) {
                        if (all[i].textContent.trim().toLowerCase().includes('show transcript'))
                            return 'yes';
                    }
                    return 'no';
                })()
            """)
            if found == "yes":
                break
            time.sleep(1)

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

        # Force-expand the transcript panel if click didn't open it
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

        for _ in range(10):
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
    "explore": "https://www.youtube.com/feed/explore",
    "library": "https://www.youtube.com/feed/library",
    "studio": "https://studio.youtube.com",
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
    from interface.chrome import dispatch_key
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
        for _ in range(3):
            btn = session.evaluate(
                "document.querySelector('ytd-subscribe-button-renderer button')?.textContent?.trim()")
            if btn:
                break
            time.sleep(1)

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
            # Fallback: direct JS click
            session.evaluate("""
                var btn = document.querySelector('button[aria-label="Share"]');
                if(btn) btn.click();
            """)

        # Poll for share URL input to appear
        url = ""
        for _ in range(8):
            time.sleep(0.5)
            url = session.evaluate("""
                var input = document.querySelector('#share-url');
                input ? (input.value || input.getAttribute('value') || '') : ''
            """) or ""
            if url:
                break

        # Close dialog
        session.evaluate("""
            var close = document.querySelector('[aria-label="Close"], '
                + 'ytd-unified-share-panel-renderer yt-icon-button, '
                + '#share-dialog yt-icon-button');
            if(close) close.click();
        """)

        return {"ok": True, "share_url": str(url),
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

        interact.mcp_click(
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

        # Scroll to load recommendations first
        session.evaluate("window.scrollTo(0, 600)")
        time.sleep(1)

        # Try new-style lockup link first via JS click
        clicked = session.evaluate("""
            (function(){
                var lockups = document.querySelectorAll(
                    'ytd-watch-next-secondary-results-renderer yt-lockup-view-model');
                if (lockups.length > 0) {
                    var a = lockups[0].querySelector('a[href*="watch"]');
                    if (a) { a.click(); return 'ok'; }
                }
                return 'none';
            })()
        """)
        if clicked != "ok":
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
    """List recommended videos from the sidebar or below the player."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        # Scroll to trigger lazy-loading of recommendations
        session.evaluate("window.scrollTo(0, 600)")
        time.sleep(1)

        r = session.evaluate(f"""
            (function(){{
                // Try new yt-lockup-view-model first (2024+ YouTube layout)
                var lockups = document.querySelectorAll(
                    'ytd-watch-next-secondary-results-renderer yt-lockup-view-model');
                if (lockups.length > 0) {{
                    var out = [];
                    for (var i = 0; i < Math.min(lockups.length, {limit}); i++) {{
                        var item = lockups[i];
                        var linkEl = item.querySelector('a[href*="watch"], a[href*="/shorts/"]');
                        var href = linkEl ? linkEl.getAttribute('href') || '' : '';
                        var vid = href.match(/[?&]v=([^&]+)/);
                        var spans = item.querySelectorAll('span');
                        var st = [];
                        for (var j = 0; j < spans.length; j++) {{
                            var t = spans[j].textContent.trim();
                            if (t && t !== '\\u00b7' && t !== '\\u2022') st.push(t);
                        }}
                        var badge = item.querySelector('.yt-badge-shape__text, badge-shape div');
                        out.push({{
                            title: st.length > 0 ? st[0].substring(0, 120) : '',
                            channel: st.length > 1 ? st[1] : '',
                            views: st.length > 2 ? st[2] : '',
                            duration: badge ? badge.textContent.trim() : '',
                            videoId: vid ? vid[1] : '',
                            url: vid ? 'https://www.youtube.com/watch?v=' + vid[1] : ''
                        }});
                    }}
                    return JSON.stringify({{ok: true, count: out.length, results: out}});
                }}
                // Fallback: legacy ytd-compact-video-renderer
                var items = document.querySelectorAll('ytd-compact-video-renderer');
                var out = [];
                for (var i = 0; i < Math.min(items.length, {limit}); i++) {{
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
        result = json.loads(r) if r else {"ok": False}
        if result.get("ok") and result.get("count", 0) > 0:
            return result

        # Second fallback: find watch links from the related/sidebar area
        r2 = session.evaluate(f"""
        (function() {{
            var container = document.querySelector('#secondary') || document;
            var links = container.querySelectorAll('a[href*="/watch"]');
            var seen = {{}};
            var out = [];
            var currentVid = window.location.search.match(/[?&]v=([^&]+)/);
            var currentId = currentVid ? currentVid[1] : '';
            for (var i = 0; i < links.length && out.length < {limit}; i++) {{
                var href = links[i].getAttribute('href') || '';
                var vid = href.match(/[?&]v=([^&]+)/);
                if (!vid || vid[1] === currentId || seen[vid[1]]) continue;
                seen[vid[1]] = true;
                var text = links[i].textContent.trim();
                if (text.length < 5) continue;
                out.push({{
                    title: text.substring(0, 100),
                    videoId: vid[1],
                    url: 'https://www.youtube.com/watch?v=' + vid[1],
                    channel: '', views: '', duration: ''
                }});
            }}
            return JSON.stringify({{ok: true, count: out.length, results: out}});
        }})()
        """)
        return json.loads(r2) if r2 else {"ok": False, "error": "No recommendations found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_comments(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract top comments from the current video page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        interact = _load_interact()

        # Try force-expanding the comments engagement panel first
        session.evaluate("""
            var panel = document.querySelector(
                'ytd-engagement-panel-section-list-renderer'
                + '[target-id="engagement-panel-comments-section"]');
            if (panel) {
                panel.setAttribute('visibility',
                    'ENGAGEMENT_PANEL_VISIBILITY_EXPANDED');
                panel.style.display = '';
            }
        """)

        # Scroll to trigger comment section lazy-loading
        for _scroll in range(6):
            interact.mcp_scroll(session, "down", 500)
            time.sleep(1.5)
            n = session.evaluate(
                "document.querySelectorAll('ytd-comment-thread-renderer').length")
            if n and int(n) > 0:
                break

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


def go_back(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate back to the previous page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        session.evaluate("window.history.back()")
        time.sleep(2)
        url = session.evaluate("window.location.href") or ""
        machine = get_machine(_session_name)
        machine.set_url(str(url))
        if "/watch" in str(url):
            machine.transition(YTState.WATCHING)
        elif "/results" in str(url):
            machine.transition(YTState.SEARCHING)
        else:
            machine.transition(YTState.IDLE)
        return {"ok": True, "url": str(url)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_home_layout(port: int = CDP_PORT) -> Dict[str, Any]:
    """Identify the core layout areas of the YouTube home page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        layout = session.evaluate("""
        (function() {
            var out = {};
            out.url = window.location.href;
            out.title = document.title;

            var topbar = document.querySelector('ytd-masthead');
            out.topbar = !!topbar;
            var searchBox = document.querySelector('input#search');
            out.search_box = !!searchBox;
            var avatar = document.querySelector('#avatar-btn');
            out.user_avatar = !!avatar;

            var guide = document.querySelector('tp-yt-app-drawer, ytd-mini-guide-renderer');
            out.sidebar = !!guide;

            var chips = document.querySelectorAll('yt-chip-cloud-chip-renderer, ytd-feed-filter-chip-bar-renderer yt-chip-cloud-chip-renderer');
            out.category_chips = [];
            for (var i = 0; i < Math.min(chips.length, 10); i++) {
                out.category_chips.push(chips[i].textContent.trim());
            }

            var videos = document.querySelectorAll('ytd-rich-item-renderer');
            out.video_count = videos.length;

            var sections = [];
            if (out.topbar) sections.push('Top navigation bar (search, logo, user avatar)');
            if (out.sidebar) sections.push('Left sidebar (Home, Shorts, Subscriptions, Library)');
            if (out.category_chips.length > 0) sections.push('Category chip bar (' + out.category_chips.slice(0,5).join(', ') + ')');
            if (out.video_count > 0) sections.push('Video feed (' + out.video_count + ' videos visible)');
            out.areas = sections;

            return JSON.stringify(out);
        })()
        """)
        result = json.loads(layout) if layout else {}
        result["ok"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_to_channel(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click on the channel name of the current video to open channel page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        chan_info = session.evaluate("""
        (function() {
            var link = document.querySelector('#channel-name a, ytd-channel-name a');
            if (link) {
                var name = link.textContent.trim();
                link.click();
                return JSON.stringify({name: name, ok: true});
            }
            var chanLink = document.querySelector('ytd-video-owner-renderer a');
            if (chanLink) {
                var name = chanLink.textContent.trim();
                chanLink.click();
                return JSON.stringify({name: name, ok: true});
            }
            return JSON.stringify({ok: false});
        })()
        """)
        result = json.loads(chan_info) if chan_info else {"ok": False}
        if result.get("ok"):
            time.sleep(3)
            url = session.evaluate("window.location.href") or ""
            machine = get_machine(_session_name)
            machine.set_url(str(url))
            machine.transition(YTState.IDLE)
            return {"ok": True, "channel": result.get("name", ""), "url": str(url)}
        return {"ok": False, "error": "Channel link not found on current page"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_watch_history(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get items from watch history page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        url = session.evaluate("window.location.href") or ""
        if "/feed/history" not in str(url):
            navigate("history", port)
            time.sleep(3)

        for _ in range(3):
            session.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.5)

        history = session.evaluate(f"""
        (function() {{
            var items = document.querySelectorAll('yt-lockup-view-model');
            if (items.length === 0) items = document.querySelectorAll('ytd-video-renderer');
            var result = [];
            for (var i = 0; i < Math.min(items.length, {limit}); i++) {{
                var titleEl = items[i].querySelector('h3, #video-title, a#video-title-link');
                var channelEl = items[i].querySelector('#channel-name a, .ytd-channel-name a, [class*="channel"]');
                var linkEl = items[i].querySelector('a[href*="/watch"]');
                result.push({{
                    title: titleEl ? titleEl.textContent.trim() : items[i].textContent.trim().substring(0, 80),
                    url: linkEl ? linkEl.getAttribute('href') || '' : '',
                    channel: channelEl ? channelEl.textContent.trim() : '',
                    index: i
                }});
            }}
            return JSON.stringify(result);
        }})()
        """)
        items = json.loads(history) if history else []
        return {"ok": True, "items": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_history_item(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete a watch history item by index (0-based)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        result = session.evaluate(f"""
        (function() {{
            var items = document.querySelectorAll('yt-lockup-view-model');
            if (items.length === 0) items = document.querySelectorAll('ytd-video-renderer');
            if ({index} >= items.length) return JSON.stringify({{ok: false, error: 'Index out of range (' + items.length + ' items)'}});
            var item = items[{index}];
            var titleEl = item.querySelector('h3, #video-title');
            var titleText = titleEl ? titleEl.textContent.trim() : item.textContent.trim().substring(0, 60);

            var menuBtn = item.querySelector('button[aria-label*="Action"], button[aria-label*="action"], #menu button, yt-icon-button#button, button.yt-spec-button-shape-next');
            if (!menuBtn) {{
                var btns = item.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {{
                    if (btns[i].querySelector('yt-icon, svg') && btns[i].getBoundingClientRect().width < 50) {{
                        menuBtn = btns[i]; break;
                    }}
                }}
            }}
            if (menuBtn) {{
                menuBtn.click();
                return JSON.stringify({{ok: true, title: titleText, phase: 'menu_opened'}});
            }}
            return JSON.stringify({{ok: false, error: 'Menu button not found'}});
        }})()
        """)
        r = json.loads(result) if result else {"ok": False}
        if not r.get("ok"):
            return r

        time.sleep(1)

        remove = session.evaluate("""
        (function() {
            var items = document.querySelectorAll('tp-yt-paper-listbox ytd-menu-service-item-renderer, ytd-menu-popup-renderer tp-yt-paper-item, [role="menuitem"], ytd-menu-service-item-renderer');
            for (var i = 0; i < items.length; i++) {
                var text = items[i].textContent.trim().toLowerCase();
                if (text.includes('remove') || text.includes('delete')) {
                    items[i].click();
                    return 'removed';
                }
            }
            return 'not_found';
        })()
        """)
        if remove == "removed":
            return {"ok": True, "action": "deleted", "title": r.get("title", ""), "index": index}
        return {"ok": False, "error": "Remove option not found in menu"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced functions for 20 advanced YouTube tasks
# ---------------------------------------------------------------------------

def get_chapters(port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract chapter markers from the current video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        chapters = session.evaluate("""
        (function() {
            var items = document.querySelectorAll('ytd-macro-markers-list-item-renderer');
            var result = [];
            for (var i = 0; i < items.length; i++) {
                var title = items[i].querySelector('h4, #details h4');
                var time = items[i].querySelector('#time, .macro-markers');
                result.push({
                    index: i,
                    title: title ? title.textContent.trim() : '',
                    time: time ? time.textContent.trim() : ''
                });
            }
            if (result.length === 0) {
                var descChapters = document.querySelectorAll('ytd-structured-description-content-renderer a[href*="&t="]');
                for (var i = 0; i < descChapters.length; i++) {
                    var text = descChapters[i].textContent.trim();
                    var href = descChapters[i].getAttribute('href') || '';
                    var match = href.match(/[&?]t=(\\d+)/);
                    result.push({index: i, title: text, time: match ? match[1] + 's' : ''});
                }
            }
            return JSON.stringify(result);
        })()
        """)
        items = json.loads(chapters) if chapters else []
        return {"ok": True, "chapters": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def seek_to_chapter(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    """Jump to a specific chapter by index."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        result = session.evaluate(f"""
        (function() {{
            var items = document.querySelectorAll('ytd-macro-markers-list-item-renderer');
            if ({index} < items.length) {{
                items[{index}].click();
                var title = items[{index}].querySelector('h4');
                return JSON.stringify({{ok: true, title: title ? title.textContent.trim() : '', index: {index}}});
            }}
            return JSON.stringify({{ok: false, error: 'Chapter index out of range'}});
        }})()
        """)
        return json.loads(result) if result else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def apply_default_settings(quality_level: str = "720p", speed_rate: float = 1.0,
                           captions_on: bool = False, port: int = CDP_PORT) -> Dict[str, Any]:
    """Apply a combination of playback settings (quality, speed, captions)."""
    results = {}
    if quality_level:
        results["quality"] = quality(quality_level, port)
    if speed_rate != 1.0:
        results["speed"] = speed(speed_rate, port)
    results["captions"] = captions(captions_on, port)
    return {"ok": True, "action": "apply_default_settings", "results": results}


def find_live_streams(category: str = "", limit: int = 5,
                      port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to live streams and list available ones."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        url = f"https://www.youtube.com/results?search_query={category}+live&sp=EgJAAQ%253D%253D" if category else "https://www.youtube.com/results?search_query=live&sp=EgJAAQ%253D%253D"
        interact = _load_interact()
        interact.mcp_navigate(session, url, tool_name="YouTube")
        time.sleep(3)

        for _ in range(3):
            session.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.5)

        streams = session.evaluate(f"""
        (function() {{
            var items = document.querySelectorAll('ytd-video-renderer');
            var result = [];
            for (var i = 0; i < Math.min(items.length, {limit}); i++) {{
                var title = items[i].querySelector('#video-title');
                var channel = items[i].querySelector('#channel-name a');
                var viewers = items[i].querySelector('#metadata-line span');
                var thumb = items[i].querySelector('a#thumbnail');
                result.push({{
                    title: title ? title.textContent.trim() : '',
                    channel: channel ? channel.textContent.trim() : '',
                    viewers: viewers ? viewers.textContent.trim() : '',
                    url: thumb ? thumb.getAttribute('href') || '' : ''
                }});
            }}
            return JSON.stringify(result);
        }})()
        """)
        items = json.loads(streams) if streams else []
        machine = get_machine(_session_name)
        machine.transition(YTState.SEARCHING)
        return {"ok": True, "streams": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_live_stats(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get live stream statistics (viewer count, likes, etc.)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        stats = session.evaluate("""
        (function() {
            var out = {};
            var viewCount = document.querySelector('.view-count, #info-strings yt-formatted-string');
            out.viewers = viewCount ? viewCount.textContent.trim() : '';
            var likeBtn = document.querySelector('like-button-view-model button');
            out.likes = likeBtn ? likeBtn.getAttribute('aria-label') || '' : '';
            var chatFrame = document.querySelector('iframe#chatframe');
            out.has_chat = !!chatFrame;
            var title = document.querySelector('h1 yt-formatted-string');
            out.title = title ? title.textContent.trim() : '';
            var channel = document.querySelector('#channel-name a');
            out.channel = channel ? channel.textContent.trim() : '';
            return JSON.stringify(out);
        })()
        """)
        result = json.loads(stats) if stats else {}
        result["ok"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_studio(section: str = "content", port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a YouTube Studio section."""
    _STUDIO_SECTIONS = {
        "dashboard": "https://studio.youtube.com",
        "content": "https://studio.youtube.com/channel/UC/videos",
        "analytics": "https://studio.youtube.com/channel/UC/analytics",
        "comments": "https://studio.youtube.com/channel/UC/comments",
        "playlists": "https://studio.youtube.com/channel/UC/playlists",
        "subtitles": "https://studio.youtube.com/channel/UC/translations",
        "monetization": "https://studio.youtube.com/channel/UC/monetization",
        "customization": "https://studio.youtube.com/channel/UC/editing",
    }
    url = _STUDIO_SECTIONS.get(section.lower(), f"https://studio.youtube.com")
    return navigate(url, port)


def create_playlist(name: str, description: str = "",
                    port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new playlist via the YouTube playlists page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        navigate("playlists", port)
        time.sleep(2)

        result = session.evaluate("""
        (function() {
            var btns = document.querySelectorAll('button, ytd-button-renderer');
            for (var i = 0; i < btns.length; i++) {
                var text = btns[i].textContent.trim().toLowerCase();
                if (text.includes('new playlist') || text.includes('create')) {
                    btns[i].click();
                    return 'clicked';
                }
            }
            return 'not_found';
        })()
        """)
        if result == "clicked":
            time.sleep(1)
            return {"ok": True, "action": "create_playlist_dialog_opened", "name": name}
        return {"ok": False, "error": "Create playlist button not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_settings(section: str = "account", port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to YouTube settings page."""
    _SETTINGS = {
        "account": "https://www.youtube.com/account",
        "notifications": "https://www.youtube.com/account_notifications",
        "privacy": "https://www.youtube.com/account_privacy",
        "playback": "https://www.youtube.com/account_playback",
        "advanced": "https://www.youtube.com/account_advanced",
    }
    url = _SETTINGS.get(section.lower(), f"https://www.youtube.com/account")
    return navigate(url, port)


def navigate_premium(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to YouTube Premium page to view benefits (no purchase)."""
    return navigate("https://www.youtube.com/premium", port)


def get_premium_benefits(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read YouTube Premium benefit descriptions from the page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}
    try:
        url = session.evaluate("window.location.href") or ""
        if "premium" not in str(url).lower():
            navigate_premium(port)
            time.sleep(3)

        benefits = session.evaluate("""
        (function() {
            var items = document.querySelectorAll('h3, h2, [class*="benefit"], [class*="feature"]');
            var result = [];
            for (var i = 0; i < items.length; i++) {
                var text = items[i].textContent.trim();
                if (text.length > 5 && text.length < 100) result.push(text);
            }
            return JSON.stringify([...new Set(result)].slice(0, 10));
        })()
        """)
        items = json.loads(benefits) if benefits else []
        return {"ok": True, "benefits": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_with_filters(query: str, duration: str = "", sort_by: str = "",
                        filter_type: str = "video", limit: int = 10,
                        port: int = CDP_PORT) -> Dict[str, Any]:
    """Search with advanced filters (duration, sort, type)."""
    sp_parts = []
    if filter_type == "video":
        sp_parts.append("EgIQAQ%3D%3D")
    elif filter_type == "live":
        sp_parts.append("EgJAAQ%3D%3D")
    elif filter_type == "playlist":
        sp_parts.append("EgIQAw%3D%3D")

    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    if sp_parts:
        url += f"&sp={sp_parts[0]}"

    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No YouTube session"}

    interact = _load_interact()
    interact.mcp_navigate(session, url, tool_name="YouTube")
    time.sleep(3)

    return search_videos(query, limit, port)
