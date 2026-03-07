"""Bilibili operations via CDMCP (Chrome DevTools MCP).

Uses standard CDMCP interfaces (via cdmcp_loader) for:
  - Session management (boot_tool_session / require_tab)
  - Visual overlays (badge, lock, focus, favicon)
  - MCP interaction effects (mcp_click, mcp_type, mcp_navigate)

All tab operations go through CDMCP session.require_tab() to ensure tabs
open in the dedicated session window, not in the user's existing windows.

Operations:
  - Session: boot / status / recover
  - Navigation: home, bangumi, live, history, favorites, dynamics, video URL
  - Playback: play, pause, seek, volume, speed, quality, fullscreen, pip
  - Danmaku: toggle display, send danmaku
  - Engagement: like, coin, favorite, triple (三连), share, follow, comment
  - Info: video details, comments, recommendations, MCP state
  - Search: search videos with MCP effects
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from logic.chrome.session import CDPSession, CDP_PORT, capture_screenshot
from logic.cdmcp_loader import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_interact,
)

from tool.BILIBILI.logic.chrome.state_machine import (
    BiliState, get_machine,
)

BILI_URL_PATTERN = "bilibili.com"
BILI_HOME = "https://www.bilibili.com"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _TOOL_DIR / "data"


def _overlay():
    return load_cdmcp_overlay()


def _sessions():
    return load_cdmcp_sessions()


def _interact():
    return load_cdmcp_interact()


# ---------------------------------------------------------------------------
# Session management — all via CDMCP standard interfaces
# ---------------------------------------------------------------------------

_session = None
_session_name = "bilibili"


def _get_or_create_session(port: int = CDP_PORT):
    """Get existing CDMCP session or return None."""
    global _session
    if _session is not None:
        try:
            cdp = _session.get_cdp()
            if cdp:
                return _session
        except Exception:
            pass
        _session = None
    sm = _sessions()
    existing = sm.get_session(_session_name)
    if existing:
        try:
            cdp = existing.get_cdp()
            if cdp:
                _session = existing
                return existing
        except Exception:
            pass
        sm.close_session(_session_name)
    return None


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot Bilibili in a dedicated CDMCP session window."""
    global _session
    machine = get_machine(_session_name)

    if machine.state not in (BiliState.UNINITIALIZED, BiliState.ERROR):
        existing = _get_or_create_session(port)
        if existing:
            return {"ok": True, "action": "already_booted", **machine.to_dict()}

    if machine.state == BiliState.ERROR:
        machine.transition(BiliState.RECOVERING)
        if not machine.can_recover():
            machine.reset()
        machine.transition(BiliState.UNINITIALIZED)

    machine.transition(BiliState.BOOTING, {"url": BILI_HOME})

    sm = _sessions()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)
    if not boot_result.get("ok"):
        machine.transition(BiliState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _session = boot_result.get("session")

    tab_info = _session.require_tab(
        "bilibili", url_pattern="bilibili.com",
        open_url=BILI_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        ov = _overlay()
        cdp = CDPSession(tab_info["ws"])
        ov.inject_favicon(cdp, svg_color="#00a1d6", letter="B")
        ov.inject_badge(cdp, text="Bilibili MCP", color="#00a1d6")
        ov.inject_focus(cdp, color="#00a1d6")

    machine.transition(BiliState.IDLE)
    machine.set_url(BILI_HOME)
    return {"ok": True, "action": "booted", **machine.to_dict()}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Ensure a live CDMCP session + Bilibili tab exist, return CDPSession."""
    global _session
    session = _get_or_create_session(port)
    if not session:
        result = boot_session(port)
        if not result.get("ok"):
            return None
        session = _get_or_create_session(port)
    if not session:
        return None

    tab_info = session.require_tab(
        "bilibili", url_pattern="bilibili.com",
        open_url=BILI_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        cdp = CDPSession(tab_info["ws"])
        try:
            ov = _overlay()
            has_badge = cdp.evaluate(
                f"!!document.getElementById('{ov.CDMCP_BADGE_ID}')")
            if not has_badge:
                ov.inject_favicon(cdp, svg_color="#00a1d6", letter="B")
                ov.inject_badge(cdp, text="Bilibili MCP", color="#00a1d6")
                ov.inject_focus(cdp, color="#00a1d6")
        except Exception:
            pass
        return cdp
    return None


def _recover(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    if not machine.can_recover():
        machine.reset()
        return boot_session(port)
    if machine.state != BiliState.RECOVERING:
        if not machine.transition(BiliState.RECOVERING):
            machine.reset()
            return boot_session(port)
    target = machine.get_recovery_target()
    result = boot_session(port)
    if not result.get("ok"):
        return result
    url = target.get("url", BILI_HOME)
    if url != BILI_HOME:
        cdp = _ensure_session(port)
        if cdp:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(3)
            machine.set_url(url)
    return {"ok": True, "action": "recovered", "restored_to": url, **machine.to_dict()}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    session = _get_or_create_session(port)
    result = machine.to_dict()
    result["session_alive"] = session is not None
    from logic.chrome.session import is_chrome_cdp_available
    result["cdp_available"] = is_chrome_cdp_available(port)
    return result


# ---------------------------------------------------------------------------
# Player JS helpers
# ---------------------------------------------------------------------------

def _player_js(session: CDPSession, js: str) -> Any:
    return session.evaluate(f"""
        (function(){{
            var v = document.querySelector('video');
            if(!v) return JSON.stringify({{ok: false, error: 'No video element'}});
            {js}
        }})()
    """)


# ---------------------------------------------------------------------------
# Auth & page info
# ---------------------------------------------------------------------------

def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate("""
            (function(){
                var avatar = document.querySelector('.header-avatar-wrap img');
                var loginBtn = document.querySelector('.header-login-entry');
                var name = document.querySelector('.header-entry-mini .nickname');
                if(!name) name = avatar;
                return JSON.stringify({
                    ok: true,
                    authenticated: !!avatar && !loginBtn,
                    username: name ? (name.textContent || name.getAttribute('alt') || '').trim() : '',
                    title: document.title
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate("""
            (function(){
                var url = window.location.href;
                var isVideo = url.includes('/video/');
                var isSearch = url.includes('search.bilibili.com');
                var isHome = url === 'https://www.bilibili.com/' || url === 'https://www.bilibili.com';
                var section = isVideo ? 'video' : (isSearch ? 'search' : (isHome ? 'home' : 'other'));
                return JSON.stringify({ok: true, url: url, title: document.title, section: section});
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

_NAV_TARGETS = {
    "home": "https://www.bilibili.com",
    "bangumi": "https://www.bilibili.com/bangumi/play/",
    "live": "https://live.bilibili.com",
    "anime": "https://www.bilibili.com/anime",
    "history": "https://www.bilibili.com/account/history",
    "favorites": "https://space.bilibili.com/favlist",
    "dynamics": "https://t.bilibili.com",
    "trending": "https://www.bilibili.com/v/popular/all",
    "ranking": "https://www.bilibili.com/v/popular/rank/all",
}


def navigate(target: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a section or URL."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        url = _NAV_TARGETS.get(target.lower(), target)
        if not url.startswith("http"):
            return {"ok": False, "error": f"Unknown target: {target}"}
        machine.transition(BiliState.NAVIGATING, {"target": target})
        interact = _interact()
        interact.mcp_navigate(session, url, tool_name="Bilibili")
        time.sleep(3)
        actual = session.evaluate("window.location.href") or url
        machine.set_url(str(actual))
        if "/video/" in str(actual):
            machine.transition(BiliState.WATCHING)
        elif "search" in str(actual):
            machine.transition(BiliState.SEARCHING)
        else:
            machine.transition(BiliState.IDLE)
        return {"ok": True, "url": str(actual), "target": target}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def open_video(bvid_or_url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open a video by BV ID or URL."""
    if not bvid_or_url.startswith("http"):
        bvid_or_url = f"https://www.bilibili.com/video/{bvid_or_url}"
    return navigate(bvid_or_url, port)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_videos(query: str, limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "search", "query": query})
        interact = _interact()

        from urllib.parse import quote_plus
        url = f"https://search.bilibili.com/all?keyword={quote_plus(query)}"
        interact.mcp_navigate(session, url, tool_name="Bilibili")
        time.sleep(5)

        machine.set_url(f"https://search.bilibili.com/all?keyword={query}")
        machine.transition(BiliState.SEARCHING)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('.video-list-item .bili-video-card, '
                    + '.search-all-list .bili-video-card');
                if(items.length === 0)
                    items = document.querySelectorAll('.bili-video-card');
                var out = [];
                for(var i=0; i<items.length && i<{limit}; i++){{
                    var el = items[i];
                    var titleEl = el.querySelector('.bili-video-card__info--tit a[title], '
                        + '.bili-video-card__info--tit');
                    var authorEl = el.querySelector('.bili-video-card__info--author, '
                        + '.bili-video-card__info--owner span');
                    var durationEl = el.querySelector('.bili-video-card__stats__duration');
                    var viewsEl = el.querySelector('.bili-video-card__stats--item');
                    var linkEl = el.querySelector('a[href*="/video/"]');
                    var href = linkEl ? linkEl.getAttribute('href') || '' : '';
                    if(href.startsWith('//')) href = 'https:' + href;
                    var bv = href.match(/(BV[a-zA-Z0-9]+)/);
                    out.push({{
                        title: titleEl ? (titleEl.getAttribute('title') || titleEl.textContent.trim()).substring(0, 100) : '',
                        author: authorEl ? authorEl.textContent.trim() : '',
                        duration: durationEl ? durationEl.textContent.trim() : '',
                        views: viewsEl ? viewsEl.textContent.trim() : '',
                        url: bv ? 'https://www.bilibili.com/video/' + bv[1] : href,
                        bvid: bv ? bv[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, query: {json.dumps(query)}, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Video info
# ---------------------------------------------------------------------------

def get_video_info(video_url: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        if video_url:
            machine.transition(BiliState.NAVIGATING, {"url": video_url})
            interact = _interact()
            interact.mcp_navigate(session, video_url, tool_name="Bilibili")
            time.sleep(4)
            machine.set_url(video_url)
            machine.transition(BiliState.WATCHING)

        r = session.evaluate("""
            (function(){
                var title = document.querySelector('h1.video-title, .video-title');
                var views = document.querySelector('.view-text, .view.item');
                var dm = document.querySelector('.dm-text, .dm.item');
                var date = document.querySelector('.pubdate-ip-text, .pubdate-text');
                var likes = document.querySelector('.video-like .video-like-info');
                var coins = document.querySelector('.video-coin .video-coin-info');
                var favs = document.querySelector('.video-fav .video-fav-info');
                var shares = document.querySelector('.video-share .video-share-info');
                var up = document.querySelector('.up-name, .up-info-container .up-name');
                var desc = document.querySelector('.basic-desc-info, .desc-info-text');
                var bv = window.location.pathname.match(/(BV[a-zA-Z0-9]+)/);
                return JSON.stringify({
                    ok: true,
                    title: title ? title.textContent.trim() : document.title,
                    views: views ? views.textContent.trim() : '',
                    danmaku: dm ? dm.textContent.trim() : '',
                    date: date ? date.textContent.trim() : '',
                    likes: likes ? likes.textContent.trim() : '',
                    coins: coins ? coins.textContent.trim() : '',
                    favorites: favs ? favs.textContent.trim() : '',
                    shares: shares ? shares.textContent.trim() : '',
                    author: up ? up.textContent.trim() : '',
                    description: desc ? desc.textContent.trim().substring(0, 500) : '',
                    bvid: bv ? bv[1] : '',
                    url: window.location.href
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(output_path: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        img = capture_screenshot(session)
        if not img:
            return {"ok": False, "error": "Screenshot failed"}
        if not output_path:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(_DATA_DIR / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img)
        return {"ok": True, "path": output_path, "size": len(img)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Playback controls
# ---------------------------------------------------------------------------

def play(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        paused = _player_js(session, "return v.paused ? 'yes' : 'no'")
        if paused == "yes":
            interact = _interact()
            interact.mcp_click(session, '.bpx-player-ctrl-play, [aria-label="播放/暂停"]',
                               label="Play", dwell=0.5, color="#00a1d6",
                               tool_name="Bilibili")
        return {"ok": True, "action": "play", "was_paused": paused == "yes"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pause(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        paused = _player_js(session, "return v.paused ? 'yes' : 'no'")
        if paused == "no":
            interact = _interact()
            interact.mcp_click(session, '.bpx-player-ctrl-play, [aria-label="播放/暂停"]',
                               label="Pause", dwell=0.5, color="#00a1d6",
                               tool_name="Bilibili")
        return {"ok": True, "action": "pause", "was_playing": paused == "no"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def seek(target: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Seek to position: seconds, mm:ss, percentage, or relative (+/-N)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        target = target.strip()
        if target.endswith("%"):
            pct = float(target[:-1]) / 100
            r = _player_js(session, f"v.currentTime = v.duration * {pct}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime, duration: v.duration}})")
        elif target.startswith("+") or target.startswith("-"):
            r = _player_js(session, f"v.currentTime += {float(target)}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        elif ":" in target:
            parts = target.split(":")
            secs = sum(int(p) * (60 ** i) for i, p in enumerate(reversed(parts)))
            r = _player_js(session, f"v.currentTime = {secs}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        else:
            r = _player_js(session, f"v.currentTime = {float(target)}; "
                           f"return JSON.stringify({{ok:true, time: v.currentTime}})")
        return json.loads(r) if r else {"ok": False, "error": "No video"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def volume(level: Optional[int] = None, mute: Optional[bool] = None,
           port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        if mute is not None:
            _player_js(session, f"v.muted = {'true' if mute else 'false'}")
        if level is not None:
            _player_js(session, f"v.volume = {max(0, min(100, level)) / 100}")
        r = _player_js(session,
            "return JSON.stringify({ok:true, volume: Math.round(v.volume*100), muted: v.muted})")
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def speed(rate: Optional[float] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        if rate is not None:
            _player_js(session, f"v.playbackRate = {max(0.5, min(2.0, rate))}")
        r = _player_js(session,
            "return JSON.stringify({ok:true, speed: v.playbackRate})")
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def quality(level: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set or list video quality."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(session, '.bpx-player-ctrl-quality, [aria-label="清晰度"]',
                           label="Quality", dwell=0.5, tool_name="Bilibili")
        time.sleep(1)
        items = session.evaluate("""
            (function(){
                var items = document.querySelectorAll('.bpx-player-ctrl-quality-menu-item, '
                    + '.squirtle-quality-item');
                var out = [];
                for(var i=0; i<items.length; i++)
                    out.push(items[i].textContent.trim());
                return JSON.stringify(out);
            })()
        """)
        available = json.loads(items) if items else []
        if level:
            session.evaluate(f"""
                (function(){{
                    var items = document.querySelectorAll('.bpx-player-ctrl-quality-menu-item, '
                        + '.squirtle-quality-item');
                    for(var i=0; i<items.length; i++){{
                        if(items[i].textContent.trim().includes('{level}')){{
                            items[i].click(); return;
                        }}
                    }}
                }})()
            """)
        else:
            session.evaluate("""
                document.querySelector('.bpx-player-ctrl-quality, [aria-label="清晰度"]')?.click()
            """)
        return {"ok": True, "available": available, "selected": level or "current"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def fullscreen(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(session, '.bpx-player-ctrl-full, [aria-label="全屏"]',
                           label="Fullscreen", dwell=0.3, tool_name="Bilibili")
        return {"ok": True, "action": "fullscreen_toggled"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def widescreen(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(session, '.bpx-player-ctrl-wide, [aria-label="宽屏"]',
                           label="Widescreen", dwell=0.3, tool_name="Bilibili")
        return {"ok": True, "action": "widescreen_toggled"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def pip(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
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
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Danmaku
# ---------------------------------------------------------------------------

def danmaku(toggle: Optional[bool] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle danmaku display. If toggle is None, returns current state."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        current = session.evaluate("""
            var sw = document.querySelector('.bui-danmaku-switch input, .bpx-player-dm-switch input');
            sw ? (sw.checked ? 'on' : 'off') : 'unknown'
        """)
        if toggle is not None:
            want_on = toggle
            is_on = current == "on"
            if want_on != is_on:
                interact = _interact()
                interact.mcp_click(
                    session, '.bui-danmaku-switch, .bpx-player-dm-switch',
                    label="Danmaku toggle", dwell=0.5, tool_name="Bilibili")
        after = session.evaluate("""
            var sw = document.querySelector('.bui-danmaku-switch input, .bpx-player-dm-switch input');
            sw ? (sw.checked ? 'on' : 'off') : 'unknown'
        """)
        return {"ok": True, "danmaku": after}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_danmaku(text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Send a danmaku message to the current video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_type(
            session, '.bpx-player-dm-input input, input.bpx-player-dm-input', text,
            label=f"Danmaku: {text[:20]}", char_delay=0.04,
            clear_first=True, tool_name="Bilibili")
        time.sleep(0.3)
        interact.mcp_click(
            session, '.bpx-player-dm-btn-send, .bpx-player-dm-btn',
            label="Send danmaku", dwell=0.5, tool_name="Bilibili")
        return {"ok": True, "action": "danmaku_sent", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Engagement: like, coin, favorite, triple, share, follow, comment
# ---------------------------------------------------------------------------

def like(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(
            session, '.video-like, .video-toolbar-left-item:nth-child(1)',
            label="Like (点赞)", dwell=1.0, color="#fb7299", tool_name="Bilibili")
        time.sleep(0.5)
        count = session.evaluate(
            "document.querySelector('.video-like .video-like-info')?.textContent?.trim() || ''")
        return {"ok": True, "action": "liked", "count": str(count) if count else ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def coin(amount: int = 1, port: int = CDP_PORT) -> Dict[str, Any]:
    """Throw coins (投币). amount: 1 or 2."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(
            session, '.video-coin, .video-toolbar-left-item:nth-child(2)',
            label="Coin (投币)", dwell=1.0, color="#fb7299", tool_name="Bilibili")
        time.sleep(1)
        idx = 1 if amount == 2 else 0
        session.evaluate(f"""
            var btns = document.querySelectorAll('.coin-bottom .bi-btn, .coin-item');
            if(btns.length > {idx}) btns[{idx}].click();
        """)
        time.sleep(0.5)
        session.evaluate("""
            var confirm = document.querySelector('.coin-bottom .bi-btn--primary, '
                + '.coin-confirm, button.bi-btn');
            if(confirm) confirm.click();
        """)
        return {"ok": True, "action": "coined", "amount": amount}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def favorite(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(
            session, '.video-fav, .video-toolbar-left-item:nth-child(3)',
            label="Favorite (收藏)", dwell=1.0, color="#fb7299", tool_name="Bilibili")
        time.sleep(1)
        session.evaluate("""
            var items = document.querySelectorAll('.fav-list-container .fav-item, '
                + '.collection-list-container .collection-item');
            if(items.length > 0) items[0].click();
        """)
        time.sleep(0.3)
        session.evaluate("""
            var btn = document.querySelector('.fav-panel .fav-panel-footer .bi-btn--primary, '
                + '.collection-container .footer .bi-btn--primary, '
                + 'button.fav-confirm');
            if(btn) btn.click();
        """)
        return {"ok": True, "action": "favorited"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def triple(port: int = CDP_PORT) -> Dict[str, Any]:
    """三连: like + coin + favorite in one go."""
    results = {}
    results["like"] = like(port)
    time.sleep(0.5)
    results["coin"] = coin(1, port)
    time.sleep(0.5)
    results["favorite"] = favorite(port)
    all_ok = all(r.get("ok") for r in results.values())
    return {"ok": all_ok, "action": "triple", "details": results}


def share(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(
            session, '.video-share, .video-toolbar-left-item:nth-child(4)',
            label="Share (转发)", dwell=0.8, tool_name="Bilibili")
        time.sleep(1)
        url = session.evaluate("window.location.href") or ""
        return {"ok": True, "share_url": str(url), "action": "share_opened"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def follow(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_click(
            session, '.bi-follow, .follow-btn, .up-info-container .follow-btn',
            label="Follow (关注)", dwell=1.0, color="#00a1d6", tool_name="Bilibili")
        time.sleep(0.5)
        text = session.evaluate(
            "document.querySelector('.bi-follow, .follow-btn')?.textContent?.trim() || ''")
        return {"ok": True, "action": "follow_toggled", "button_text": str(text) if text else ""}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def comment(text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        session.evaluate("window.scrollTo(0, 700)")
        time.sleep(1)
        interact.mcp_click(
            session, '.reply-box-textarea, textarea.reply-box-textarea',
            label="Comment box", dwell=0.8, color="#00a1d6", tool_name="Bilibili")
        time.sleep(0.5)
        interact.mcp_type(
            session, '.reply-box-textarea, textarea.reply-box-textarea', text,
            label=f"Comment: {text[:25]}", char_delay=0.03, tool_name="Bilibili")
        time.sleep(0.5)
        interact.mcp_click(
            session, '.reply-box-send, .reply-box .reply-btn',
            label="Send comment", dwell=0.8, color="#00a1d6", tool_name="Bilibili")
        return {"ok": True, "action": "commented", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Next video / recommendations / comments
# ---------------------------------------------------------------------------

def next_video(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine = get_machine(_session_name)
        machine.transition(BiliState.NAVIGATING, {"action": "next_video"})
        interact = _interact()
        interact.mcp_click(
            session, '.video-page-card-small:first-of-type a, .reco-list-item:first-of-type a',
            label="Next video", dwell=1.0, color="#00a1d6", tool_name="Bilibili")
        time.sleep(3)
        url = session.evaluate("window.location.href") or ""
        machine.set_url(str(url))
        machine.transition(BiliState.WATCHING)
        return {"ok": True, "url": str(url)}
    except Exception as e:
        get_machine(_session_name).transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_recommendations(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('.video-page-card-small, .reco-list-item');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var a = el.querySelector('a');
                    var title = el.querySelector('.title, .info a');
                    var up = el.querySelector('.upname, .name');
                    var views = el.querySelector('.playcount, .count');
                    var dur = el.querySelector('.duration, .dur');
                    var href = a ? a.getAttribute('href') || '' : '';
                    var bv = href.match(/(BV[a-zA-Z0-9]+)/);
                    out.push({{
                        title: title ? title.textContent.trim().substring(0, 80) : '',
                        author: up ? up.textContent.trim() : '',
                        views: views ? views.textContent.trim() : '',
                        duration: dur ? dur.textContent.trim() : '',
                        bvid: bv ? bv[1] : '',
                        url: bv ? 'https://www.bilibili.com/video/' + bv[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_comments(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract top comments (navigates shadow DOM web components)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        session.evaluate("window.scrollTo(0, 700)")
        time.sleep(2)

        r = session.evaluate(f"""
            (function(){{
                var bc = document.querySelector('bili-comments');
                if(!bc || !bc.shadowRoot) return JSON.stringify({{ok:true, count:0, comments:[]}});
                var threads = bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer');
                var out = [];
                for(var i=0; i<Math.min(threads.length, {limit}); i++){{
                    var tsr = threads[i].shadowRoot;
                    if(!tsr) continue;
                    var renderer = tsr.querySelector('bili-comment-renderer');
                    if(!renderer || !renderer.shadowRoot) continue;
                    var rsr = renderer.shadowRoot;
                    var userName = '';
                    var userInfo = rsr.querySelector('bili-comment-user-info');
                    if(userInfo && userInfo.shadowRoot){{
                        var nameEl = userInfo.shadowRoot.querySelector('#user-name a, .user-name');
                        userName = nameEl ? nameEl.textContent.trim() : '';
                    }}
                    var content = '';
                    var richText = rsr.querySelector('#content bili-rich-text');
                    if(richText && richText.shadowRoot){{
                        var p = richText.shadowRoot.querySelector('p');
                        content = p ? p.textContent.trim() : richText.shadowRoot.textContent.trim();
                        content = content.substring(0, 300);
                    }}
                    var likeCount = '', timeStr = '';
                    var actionBtns = rsr.querySelector('bili-comment-action-buttons-renderer');
                    if(actionBtns && actionBtns.shadowRoot){{
                        var likeEl = actionBtns.shadowRoot.querySelector('#like-button span, .like-count');
                        likeCount = likeEl ? likeEl.textContent.trim() : '';
                        var timeEl = actionBtns.shadowRoot.querySelector('#pubdate, .reply-time');
                        timeStr = timeEl ? timeEl.textContent.trim() : '';
                    }}
                    out.push({{author: userName, text: content, likes: likeCount, time: timeStr}});
                }}
                return JSON.stringify({{ok: true, count: out.length, comments: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Comprehensive MCP state
# ---------------------------------------------------------------------------

def get_mcp_state(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine = get_machine(_session_name)
        r = session.evaluate("""
            (function(){
                var out = {};
                out.url = window.location.href;
                out.title = document.title;
                out.section = out.url.includes('/video/') ? 'video'
                    : out.url.includes('search.bilibili.com') ? 'search'
                    : out.url.includes('live.bilibili.com') ? 'live'
                    : 'other';

                var v = document.querySelector('video');
                if(v){
                    out.player = {
                        paused: v.paused,
                        currentTime: Math.round(v.currentTime*10)/10,
                        duration: Math.round(v.duration*10)/10,
                        volume: Math.round(v.volume*100),
                        muted: v.muted,
                        playbackRate: v.playbackRate,
                        ended: v.ended
                    };
                    out.player.progress_pct = out.player.duration > 0
                        ? Math.round(v.currentTime / v.duration * 1000) / 10 : 0;
                }

                var h1 = document.querySelector('h1.video-title, .video-title');
                out.video_title = h1 ? h1.textContent.trim() : '';

                var up = document.querySelector('.up-name');
                out.channel = up ? up.textContent.trim() : '';

                var likes = document.querySelector('.video-like .video-like-info');
                out.likes = likes ? likes.textContent.trim() : '';
                var coins = document.querySelector('.video-coin .video-coin-info');
                out.coins = coins ? coins.textContent.trim() : '';
                var favs = document.querySelector('.video-fav .video-fav-info');
                out.favorites = favs ? favs.textContent.trim() : '';

                var dmSw = document.querySelector('.bui-danmaku-switch input, .bpx-player-dm-switch input');
                out.danmaku = dmSw ? (dmSw.checked ? 'on' : 'off') : 'unknown';

                var qualEl = document.querySelector('.bpx-player-ctrl-quality-result, .squirtle-quality-text');
                out.quality = qualEl ? qualEl.textContent.trim() : '';

                var avatar = document.querySelector('.header-avatar-wrap img');
                out.authenticated = !!avatar;

                var recs = document.querySelectorAll('.video-page-card-small, .reco-list-item');
                out.recommendation_count = recs.length;

                var bv = window.location.pathname.match(/(BV[a-zA-Z0-9]+)/);
                out.bvid = bv ? bv[1] : '';

                return JSON.stringify(out);
            })()
        """)
        state = json.loads(r) if r else {}
        state["machine_state"] = machine.to_dict()
        state["ok"] = True
        return state
    except Exception as e:
        return {"ok": False, "error": str(e)}
