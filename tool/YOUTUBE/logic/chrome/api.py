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
"""

import json
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional

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
    """Boot a new YouTube CDMCP session in a dedicated window.

    Opens with a welcome page first, pins the tab, applies overlays,
    then navigates to YouTube.
    """
    global _yt_session
    machine = get_machine(_session_name)
    sm = _load_session_mgr()
    overlay = _load_overlay()

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

    # Start CDMCP server so we can show the welcome page
    server_mod_path = _CDMCP_TOOL_DIR / "logic" / "cdp" / "server.py"
    server_mod = _load_module("cdmcp_server", server_mod_path)
    server_url, _ = server_mod.start_server()
    session = sm.create_session(_session_name, timeout_sec=86400, port=port)
    sid_short = session.session_id[:8]
    created_ts = int(session.created_at)
    welcome_url = (
        f"{server_url}/welcome?session_id={sid_short}"
        f"&port={port}&timeout_sec=86400&created_at={created_ts}"
    )

    # Boot with welcome page (opens in new window)
    boot_result = session.boot(welcome_url, new_window=True)

    if not boot_result.get("ok"):
        machine.transition(YTState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _yt_session = session
    time.sleep(0.8)

    # Pin immediately, then overlays (no lock for YouTube)
    cdp = session.get_cdp()
    if cdp:
        tab_id = session.lifetime_tab_id
        if tab_id:
            overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
            overlay.activate_tab(tab_id, port)
        overlay.inject_favicon(cdp, svg_color="#ff0000", letter="Y")
        overlay.inject_badge(cdp, text="YouTube MCP", color="#ff0000")
        overlay.inject_focus(cdp, color="#ff0000")
        # No lock for YouTube — user needs to interact freely

    # Show welcome for 2 seconds, then navigate to YouTube
    time.sleep(2)
    cdp = session.get_cdp()
    if cdp:
        cdp.evaluate(f"window.location.href = {json.dumps(YOUTUBE_HOME)}")
        for _ in range(6):
            time.sleep(1)
            cur = cdp.evaluate("window.location.href") or ""
            if "youtube.com" in str(cur):
                break

    # Update lifetime URL so recovery goes to YouTube
    session.lifetime_tab_url = YOUTUBE_HOME

    machine.transition(YTState.IDLE)
    machine.set_url(YOUTUBE_HOME)

    return {"ok": True, "action": "booted", **machine.to_dict(), **boot_result}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Ensure we have a live YouTube session. Boot if needed, recover if broken."""
    global _yt_session
    machine = get_machine(_session_name)

    session = _get_or_create_session(port)
    if session:
        cdp = session.get_cdp()
        if cdp:
            _reapply_overlays_if_needed(cdp, session, port)
            return cdp

    if machine.state in (YTState.UNINITIALIZED,):
        result = boot_session(port)
        if result.get("ok"):
            session = _get_or_create_session(port)
            if session:
                return session.get_cdp()
        return None

    if machine.state == YTState.ERROR or not session:
        result = _recover(port)
        if result.get("ok"):
            session = _get_or_create_session(port)
            if session:
                return session.get_cdp()
        return None

    # Fallback: state machine thinks we're active but session is gone — reboot
    result = boot_session(port)
    if result.get("ok"):
        session = _get_or_create_session(port)
        if session:
            return session.get_cdp()
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

        # Type in search box with visual effect
        search_typed = interact.mcp_type(
            session, 'input#search, input[name="search_query"]', query,
            label=f"Search: {query}", char_delay=0.04, clear_first=True,
        )

        if search_typed.get("ok"):
            time.sleep(0.3)
            # Click search button
            interact.mcp_click(
                session, '#search-icon-legacy, button[aria-label="Search"]',
                label="Search", dwell=0.5,
            )
            time.sleep(3)
        else:
            safe_q = query.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
            session.evaluate(f"window.location.href = 'https://www.youtube.com/results?search_query={safe_q}'")
            time.sleep(4)

        machine.set_url(f"https://www.youtube.com/results?search_query={safe_q}")
        machine.transition(YTState.SEARCHING)

        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll('ytd-video-renderer, ytd-rich-item-renderer');
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
