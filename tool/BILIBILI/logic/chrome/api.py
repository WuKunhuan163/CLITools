"""Bilibili operations via CDMCP (Chrome DevTools MCP).

ToS COMPLIANCE: Bilibili's Terms of Service prohibit automated access,
bots, and scraping. All DOM automation functions are disabled.
Only session/auth state checking remains active.

Use the Bilibili Open Platform API instead: https://open.bilibili.com/

Active functions: boot_session, get_session_status, get_auth_state,
                  get_page_info, get_mcp_state, take_screenshot
All other functions return ToS errors.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from interface.chrome import CDPSession, CDP_PORT, capture_screenshot
from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_interact,
)

from tool.BILIBILI.logic.utils.chrome.state_machine import (
    BiliState, get_machine,
)

BILI_URL_PATTERN = "bilibili.com"
BILI_HOME = "https://www.bilibili.com"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _TOOL_DIR / "data"

_TOS_ERR = ("Disabled: Bilibili ToS prohibits automated access. "
            "Use Bilibili Open Platform API (open.bilibili.com) instead.")

_AUTH_FUNCS = frozenset({
    "boot_session", "get_session_status", "get_auth_state",
    "get_page_info", "get_mcp_state", "take_screenshot",
})


def _tos_guard(func):
    """Decorator that blocks non-auth functions with ToS error."""
    import functools
    if func.__name__ in _AUTH_FUNCS or func.__name__.startswith("_"):
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return {"ok": False, "error": _TOS_ERR}
    return wrapper


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
        session.touch()
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
    from interface.chrome import is_chrome_cdp_available
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
    "tech": "https://www.bilibili.com/v/tech",
    "science": "https://www.bilibili.com/v/knowledge",
    "game": "https://www.bilibili.com/v/game",
    "music": "https://www.bilibili.com/v/music",
    "dance": "https://www.bilibili.com/v/dance",
    "food": "https://www.bilibili.com/v/food",
    "car": "https://www.bilibili.com/v/car",
    "fashion": "https://www.bilibili.com/v/fashion",
    "sports": "https://www.bilibili.com/v/sports",
    "settings": "https://space.bilibili.com/setting",
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

        for _wait in range(15):
            time.sleep(1)
            count = session.evaluate(
                "document.querySelectorAll('.bili-video-card').length")
            if count and int(count) > 0:
                break

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
                    desc: desc ? desc.textContent.trim().substring(0, 500) : '',
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

def _hover_video(session: CDPSession):
    """Move mouse over video area to reveal player controls."""
    rect = session.evaluate("""
        (function() {
            var v = document.querySelector('video');
            if (!v) return null;
            var r = v.getBoundingClientRect();
            return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2});
        })()
    """)
    if rect:
        import json as _j
        pos = _j.loads(rect)
        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": int(pos["x"]), "y": int(pos["y"]),
        })
        time.sleep(0.5)


def play(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        paused = _player_js(session, "return v.paused ? 'yes' : 'no'")
        if paused == "yes":
            _hover_video(session)
            interact = _interact()
            r = interact.mcp_click(session, '.bpx-player-ctrl-play, [aria-label="播放/暂停"]',
                                   label="Play", dwell=0.5, color="#00a1d6",
                                   tool_name="Bilibili")
            if not r.get("ok"):
                _player_js(session, "v.play()")
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
            _hover_video(session)
            interact = _interact()
            r = interact.mcp_click(session, '.bpx-player-ctrl-play, [aria-label="播放/暂停"]',
                                   label="Pause", dwell=0.5, color="#00a1d6",
                                   tool_name="Bilibili")
            if not r.get("ok"):
                _player_js(session, "v.pause()")
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

        href = session.evaluate("""
            (function(){
                var np = document.querySelector('.next-play .video-page-card-small a[href]');
                if(np) return np.getAttribute('href');
                var rec = document.querySelector('.rec-list .video-page-card-small a[href]');
                return rec ? rec.getAttribute('href') : '';
            })()
        """)
        if href and not str(href).startswith("http"):
            href = "https://www.bilibili.com" + str(href).split("?")[0]

        if href:
            interact = _interact()
            interact.mcp_navigate(session, str(href), tool_name="Bilibili")
        else:
            interact = _interact()
            interact.mcp_click(
                session, '.next-play .video-page-card-small a, .rec-list .video-page-card-small a',
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
        session.evaluate("window.scrollTo(0, 400)")
        time.sleep(1)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('.rec-list .video-page-card-small');
                if(!items.length)
                    items = document.querySelectorAll('.video-page-card-small');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var a = el.querySelector('a[href]');
                    var title = el.querySelector('.title') || el.querySelector('.info a');
                    var up = el.querySelector('.upname') || el.querySelector('.name');
                    var dur = el.querySelector('.duration') || el.querySelector('.dur');
                    var views = el.querySelector('.playcount') || el.querySelector('.count');
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
# Trending / Popular
# ---------------------------------------------------------------------------

def get_trending(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch trending/popular videos from bilibili.com/v/popular/all."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "trending"})
        interact = _interact()
        interact.mcp_navigate(
            session, "https://www.bilibili.com/v/popular/all",
            tool_name="Bilibili")

        for _wait in range(10):
            time.sleep(1)
            count = session.evaluate(
                "document.querySelectorAll('.video-card, .card-list .video-card').length")
            if count and int(count) > 0:
                break

        machine.transition(BiliState.IDLE)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('.video-card, .card-list .video-card');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var a = el.querySelector('a[href*="/video/"]');
                    var title = el.querySelector('.video-name, .title');
                    var up = el.querySelector('.up-name__text, .up-name');
                    var views = el.querySelector('.play-text, .detail-state .data-box:first-child');
                    var dur = el.querySelector('.duration, .time-wrap');
                    var desc = el.querySelector('.video-desc, .desc');
                    var href = a ? a.getAttribute('href') || '' : '';
                    if(href.startsWith('//')) href = 'https:' + href;
                    var bv = href.match(/(BV[a-zA-Z0-9]+)/);
                    out.push({{
                        title: title ? title.textContent.trim().substring(0, 80) : '',
                        author: up ? up.textContent.trim() : '',
                        views: views ? views.textContent.trim() : '',
                        duration: dur ? dur.textContent.trim() : '',
                        desc: desc ? desc.textContent.trim().substring(0, 120) : '',
                        bvid: bv ? bv[1] : '',
                        url: bv ? 'https://www.bilibili.com/video/' + bv[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_history(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch user watch history."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "history"})
        interact = _interact()
        interact.mcp_navigate(
            session, "https://www.bilibili.com/account/history",
            tool_name="Bilibili")

        for _wait in range(10):
            time.sleep(1)
            count = session.evaluate(
                "document.querySelectorAll('.history-record').length")
            if count and int(count) > 0:
                break

        machine.transition(BiliState.IDLE)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll('.history-record');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var a = el.querySelector('a[href*="/video/"]');
                    var titleEl = el.querySelector('.r-info .title, .r-info a.title');
                    if(!titleEl) titleEl = el.querySelectorAll('a')[1];
                    var upEl = el.querySelector('.r-info a[href*="space.bilibili.com"]');
                    var timeEl = el.querySelector('.lastplay-t');
                    var progEl = el.querySelector('.progress');
                    var href = a ? a.getAttribute('href') || '' : '';
                    if(href.startsWith('//')) href = 'https:' + href;
                    var bv = href.match(/(BV[a-zA-Z0-9]+)/);
                    out.push({{
                        title: titleEl ? titleEl.textContent.trim().substring(0, 80) : '',
                        author: upEl ? upEl.textContent.trim() : '',
                        time: timeEl ? timeEl.textContent.trim() : '',
                        progress: progEl ? progEl.textContent.trim() : '',
                        bvid: bv ? bv[1] : '',
                        url: bv ? 'https://www.bilibili.com/video/' + bv[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
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


# ---------------------------------------------------------------------------
# Additional functions for basic/advanced tasks
# ---------------------------------------------------------------------------

def go_back(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate back to the previous page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        session.evaluate("window.history.back()")
        time.sleep(2)
        url = session.evaluate("window.location.href") or ""
        machine = get_machine(_session_name)
        machine.set_url(str(url))
        if "/video/" in str(url):
            machine.transition(BiliState.WATCHING)
        elif "search" in str(url):
            machine.transition(BiliState.SEARCHING)
        else:
            machine.transition(BiliState.IDLE)
        return {"ok": True, "url": str(url)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_home_layout(port: int = CDP_PORT) -> Dict[str, Any]:
    """Identify the core layout areas of the Bilibili home page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        layout = session.evaluate("""
        (function() {
            var out = {};
            out.url = window.location.href;
            out.title = document.title;

            var nav = document.querySelector('.bili-header__bar, .bili-header');
            out.topbar = !!nav;

            var searchBox = document.querySelector('input.nav-search-input, .center-search__bar input');
            out.search_box = !!searchBox;

            var avatar = document.querySelector('.header-avatar-wrap img, .bili-avatar');
            out.user_avatar = !!avatar;

            var tabs = document.querySelectorAll('.channel-link, .bili-header__channel a, .channel-entry-more__link');
            out.nav_tabs = [];
            for (var i = 0; i < Math.min(tabs.length, 15); i++) {
                var text = tabs[i].textContent.trim();
                if (text) out.nav_tabs.push(text);
            }

            var cards = document.querySelectorAll('.feed-card, .bili-video-card, .video-card');
            out.video_count = cards.length;

            var sections = [];
            if (out.topbar) sections.push('Top navigation bar (search, logo, user avatar)');
            if (out.nav_tabs.length > 0) sections.push('Section tabs (' + out.nav_tabs.slice(0,5).join(', ') + ')');
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


def navigate_to_uploader(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click on the UP name of the current video to navigate to their page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        up_info = session.evaluate("""
        (function() {
            var link = document.querySelector('.up-name, .up-info--detail a, a.up-name');
            if (link) {
                var name = link.textContent.trim();
                link.click();
                return JSON.stringify({name: name, ok: true});
            }
            var upLink = document.querySelector('.upname a, .up-info a');
            if (upLink) {
                var name = upLink.textContent.trim();
                upLink.click();
                return JSON.stringify({name: name, ok: true});
            }
            return JSON.stringify({ok: false});
        })()
        """)
        result = json.loads(up_info) if up_info else {"ok": False}
        if result.get("ok"):
            time.sleep(3)
            url = session.evaluate("window.location.href") or ""
            machine = get_machine(_session_name)
            machine.set_url(str(url))
            machine.transition(BiliState.IDLE)
            return {"ok": True, "up_name": result.get("name", ""), "url": str(url)}
        return {"ok": False, "error": "UP name link not found on current page"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_personal(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to personal space (my profile page)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        uid = session.evaluate("""
        (function() {
            var link = document.querySelector('.header-avatar-wrap a, a[href*="space.bilibili.com"]');
            if (link) return link.getAttribute('href') || '';
            var uid = document.cookie.match(/DedeUserID=(\\d+)/);
            return uid ? 'https://space.bilibili.com/' + uid[1] : '';
        })()
        """)
        if uid and str(uid).strip():
            url = str(uid).strip()
            if not url.startswith("http"):
                url = "https:" + url if url.startswith("//") else "https://space.bilibili.com/" + url
            return navigate(url, port)
        return {"ok": False, "error": "Could not determine user space URL"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 1: Danmaku display settings
# ---------------------------------------------------------------------------

def get_danmaku_settings(port: int = CDP_PORT) -> Dict[str, Any]:
    """Open danmaku settings panel and read current configuration."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        interact = _interact()
        interact.mcp_click(
            session,
            '.bpx-player-dm-setting, .bpx-player-dm-btn-setting, '
            '.bpx-player-ctrl-setting-dm',
            label="Danmaku settings", dwell=0.5, tool_name="Bilibili")
        time.sleep(1)

        r = session.evaluate("""
            (function(){
                var out = {};
                var panel = document.querySelector(
                    '.bpx-player-dm-setting-wrap, .bpx-player-dm-setting-panel, '
                    + '.bpx-player-ctrl-setting-box');
                out.panel_open = !!panel;
                var switches = document.querySelectorAll(
                    '.bpx-player-dm-setting-wrap .bui-switch input, '
                    + '.bpx-player-dm-setting-panel input[type="checkbox"]');
                out.switches = [];
                for(var i=0; i<switches.length; i++){
                    var label = '';
                    var p = switches[i].closest('.bui-switch, label, .setting-item');
                    if(p) label = p.textContent.trim().substring(0, 40);
                    out.switches.push({label: label, checked: switches[i].checked});
                }
                var opacitySlider = document.querySelector(
                    '.bpx-player-dm-setting-wrap input[type="range"], '
                    + '.bpx-player-dm-setting-opacity input[type="range"]');
                out.opacity = opacitySlider ? opacitySlider.value : null;
                var areaItems = document.querySelectorAll(
                    '.bpx-player-dm-setting-area .bui-radio input:checked, '
                    + '.bpx-player-dm-setting-area input:checked');
                out.area = [];
                for(var i=0; i<areaItems.length; i++){
                    var p = areaItems[i].closest('.bui-radio, label');
                    if(p) out.area.push(p.textContent.trim());
                }
                return JSON.stringify(out);
            })()
        """)
        result = json.loads(r) if r else {}
        result["ok"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_danmaku_filter(keyword: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a keyword to the danmaku block list."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        interact = _interact()
        interact.mcp_click(
            session,
            '.bpx-player-dm-setting, .bpx-player-dm-btn-setting, '
            '.bpx-player-ctrl-setting-dm',
            label="Danmaku settings", dwell=0.5, tool_name="Bilibili")
        time.sleep(1)

        interact.mcp_click(
            session,
            '.bpx-player-block-filter-tab, '
            '.bpx-player-dm-setting-tab:last-child, '
            '[data-tab="block"]',
            label="Block filter tab", dwell=0.3, tool_name="Bilibili")
        time.sleep(0.5)

        interact.mcp_type(
            session,
            '.bpx-player-block-filter-input input, '
            '.bpx-player-dm-setting-filter input',
            keyword,
            label=f"Block: {keyword}", char_delay=0.03,
            clear_first=True, tool_name="Bilibili")
        time.sleep(0.3)

        interact.mcp_click(
            session,
            '.bpx-player-block-filter-btn, .bpx-player-dm-setting-filter button, '
            '.bpx-player-block-filter-add',
            label="Add filter", dwell=0.3, tool_name="Bilibili")
        return {"ok": True, "action": "filter_added", "keyword": keyword}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_danmaku_opacity(opacity: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set danmaku opacity (0-100)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        session.evaluate(f"""
            (function(){{
                var slider = document.querySelector(
                    '.bpx-player-dm-setting-opacity input[type="range"], '
                    + '.bpx-player-dm-setting-wrap input[type="range"]');
                if(slider){{
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(slider, {max(0, min(100, opacity))});
                    slider.dispatchEvent(new Event('input', {{bubbles: true}}));
                    slider.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
            }})()
        """)
        return {"ok": True, "action": "opacity_set", "opacity": opacity}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 2: Video chapters
# ---------------------------------------------------------------------------

def get_chapters(port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract video chapter markers from the player."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        r = session.evaluate("""
            (function(){
                var chapters = document.querySelectorAll(
                    '.bpx-player-ctrl-viewpoint-item, '
                    + '.bpx-player-chapters-item, '
                    + '.video-sections-item, '
                    + '.video-section-list .section-link');
                if(chapters.length === 0){
                    var pbItems = document.querySelectorAll(
                        '.bpx-player-progress-chapter, '
                        + '.bpx-player-ctrl-progress-marker');
                    if(pbItems.length > 0) {
                        var out = [];
                        for(var i=0; i<pbItems.length; i++){
                            out.push({
                                index: i,
                                title: pbItems[i].getAttribute('title') || pbItems[i].textContent.trim(),
                                time: pbItems[i].getAttribute('data-time') || ''
                            });
                        }
                        return JSON.stringify({ok: true, count: out.length, chapters: out, source: 'progress_markers'});
                    }
                }
                var out = [];
                for(var i=0; i<chapters.length; i++){
                    var el = chapters[i];
                    var timeEl = el.querySelector('.time, .duration, .viewpoint-time');
                    var titleEl = el.querySelector('.title, .text, .viewpoint-title');
                    out.push({
                        index: i,
                        title: (titleEl || el).textContent.trim().substring(0, 80),
                        time: timeEl ? timeEl.textContent.trim() : ''
                    });
                }
                return JSON.stringify({ok: true, count: out.length, chapters: out, source: 'viewpoints'});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "count": 0, "chapters": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def seek_to_chapter(index: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Click on a chapter marker to seek to that point."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        r = session.evaluate(f"""
            (function(){{
                var chapters = document.querySelectorAll(
                    '.bpx-player-ctrl-viewpoint-item, '
                    + '.bpx-player-chapters-item, '
                    + '.video-sections-item, '
                    + '.video-section-list .section-link');
                if({index} < chapters.length){{
                    chapters[{index}].click();
                    return JSON.stringify({{ok: true, clicked: {index}}});
                }}
                return JSON.stringify({{ok: false, error: 'Chapter index out of range', count: chapters.length}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 3: Dynamic speed adjustment
# ---------------------------------------------------------------------------

def auto_speed(port: int = CDP_PORT) -> Dict[str, Any]:
    """Automatically adjust speed based on video content type (tutorial vs drama)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        title = session.evaluate(
            "document.querySelector('h1.video-title, .video-title')?.textContent?.trim() || document.title"
        ) or ""
        title_str = str(title)
        tutorial_keywords = ["教程", "教学", "入门", "学习", "课程", "指南", "攻略", "讲解", "科普"]
        is_tutorial = any(kw in title_str for kw in tutorial_keywords)
        target_speed = 1.25 if is_tutorial else 1.0
        result = speed(target_speed, port)
        return {
            "ok": True,
            "title": title_str[:80],
            "detected_type": "tutorial" if is_tutorial else "entertainment",
            "applied_speed": target_speed,
            "speed_result": result,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 4: AI subtitles
# ---------------------------------------------------------------------------

def get_subtitles(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check subtitle availability and toggle AI subtitles."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        r = session.evaluate("""
            (function(){
                var btn = document.querySelector(
                    '.bpx-player-ctrl-subtitle, '
                    + '[aria-label="字幕"], '
                    + '.bilibili-player-video-btn-subtitle');
                if(!btn) return JSON.stringify({ok: true, available: false, message: 'No subtitle button found'});
                btn.click();
                var items = document.querySelectorAll(
                    '.bpx-player-ctrl-subtitle-menu-item, '
                    + '.bpx-player-ctrl-subtitle-list li');
                var out = [];
                for(var i=0; i<items.length; i++)
                    out.push(items[i].textContent.trim());
                return JSON.stringify({ok: true, available: true, options: out});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "available": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def toggle_subtitles(on: bool = True, port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle subtitle display on or off."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _hover_video(session)
        interact = _interact()
        interact.mcp_click(
            session,
            '.bpx-player-ctrl-subtitle, [aria-label="字幕"]',
            label="Subtitles", dwell=0.5, tool_name="Bilibili")
        time.sleep(0.5)
        if on:
            session.evaluate("""
                var items = document.querySelectorAll(
                    '.bpx-player-ctrl-subtitle-menu-item, '
                    + '.bpx-player-ctrl-subtitle-list li');
                for(var i=0; i<items.length; i++){
                    if(items[i].textContent.includes('AI') || items[i].textContent.includes('自动'))
                        items[i].click();
                }
            """)
        else:
            session.evaluate("""
                var items = document.querySelectorAll(
                    '.bpx-player-ctrl-subtitle-menu-item, '
                    + '.bpx-player-ctrl-subtitle-list li');
                for(var i=0; i<items.length; i++){
                    if(items[i].textContent.includes('关闭') || items[i].textContent.includes('off'))
                        items[i].click();
                }
            """)
        return {"ok": True, "action": "subtitles_" + ("on" if on else "off")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 5: Watch Later
# ---------------------------------------------------------------------------

def add_to_watchlater(port: int = CDP_PORT) -> Dict[str, Any]:
    """Add current video to Watch Later list."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        _interact()
        r = session.evaluate("""
            (function(){
                var btn = document.querySelector(
                    '.video-toolbar-right .watchlater, '
                    + '.video-toolbar-right [title*="稍后再看"], '
                    + '.video-toolbar-item-more .more-ops-list [title*="稍后再看"]');
                if(btn) { btn.click(); return JSON.stringify({ok: true, method: 'direct'}); }
                var more = document.querySelector(
                    '.video-toolbar-right-item:last-child, .video-more-btn');
                if(more) more.click();
                return JSON.stringify({ok: false, method: 'need_more_menu'});
            })()
        """)
        result = json.loads(r) if r else {}
        if not result.get("ok"):
            time.sleep(0.5)
            session.evaluate("""
                var items = document.querySelectorAll(
                    '.more-ops-list .more-ops-item, '
                    + '.video-more-popup-item');
                for(var i=0; i<items.length; i++){
                    if(items[i].textContent.includes('稍后再看')){
                        items[i].click(); break;
                    }
                }
            """)
        return {"ok": True, "action": "added_to_watchlater"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_watchlater(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch the Watch Later list."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "watchlater"})
        interact = _interact()
        interact.mcp_navigate(
            session, "https://www.bilibili.com/watchlater/#/list",
            tool_name="Bilibili")
        for _ in range(10):
            time.sleep(1)
            count = session.evaluate(
                "document.querySelectorAll('.list-box .av-item, .watch-later-list .wl-item').length")
            if count and int(count) > 0:
                break

        machine.transition(BiliState.IDLE)
        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll(
                    '.list-box .av-item, .watch-later-list .wl-item');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var titleEl = el.querySelector('.av-about .t, .title a, .wl-item-title');
                    var upEl = el.querySelector('.av-about .creator, .up-name, .wl-item-author');
                    var durEl = el.querySelector('.av-img .dur, .duration');
                    var linkEl = el.querySelector('a[href*="/video/"]');
                    var href = linkEl ? linkEl.getAttribute('href') || '' : '';
                    var bv = href.match(/(BV[a-zA-Z0-9]+)/);
                    out.push({{
                        title: titleEl ? titleEl.textContent.trim().substring(0, 80) : '',
                        author: upEl ? upEl.textContent.trim() : '',
                        duration: durEl ? durEl.textContent.trim() : '',
                        bvid: bv ? bv[1] : '',
                        url: bv ? 'https://www.bilibili.com/video/' + bv[1] : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, results: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def play_watchlater(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to Watch Later and start continuous playback."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://www.bilibili.com/watchlater/#/list",
            tool_name="Bilibili")
        time.sleep(3)
        interact.mcp_click(
            session,
            '.play-all-btn, .header-btn .play, '
            '.list-box .av-item:first-child .av-img a',
            label="Play all", dwell=1.0, color="#00a1d6", tool_name="Bilibili")
        time.sleep(3)
        url = session.evaluate("window.location.href") or ""
        return {"ok": True, "action": "watchlater_playing", "url": str(url)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Tasks 6-8: Live streaming
# ---------------------------------------------------------------------------

def navigate_live(category: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to Bilibili Live, optionally to a specific category."""
    get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        live_cats = {
            "tech": "https://live.bilibili.com/p/eden/area-tags/#/area?parentAreaId=9&areaId=0",
            "game": "https://live.bilibili.com/p/eden/area-tags/#/area?parentAreaId=2&areaId=0",
            "music": "https://live.bilibili.com/p/eden/area-tags/#/area?parentAreaId=5&areaId=0",
            "anime": "https://live.bilibili.com/p/eden/area-tags/#/area?parentAreaId=1&areaId=0",
            "entertainment": "https://live.bilibili.com/p/eden/area-tags/#/area?parentAreaId=6&areaId=0",
        }
        url = live_cats.get(category, "https://live.bilibili.com") if category else "https://live.bilibili.com"
        return navigate(url, port)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def enter_live_room(room_id: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Enter a live room by ID, or click the first available one."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        if room_id:
            url = f"https://live.bilibili.com/{room_id}"
            return navigate(url, port)

        _interact()
        href = session.evaluate("""
            (function(){
                var card = document.querySelector(
                    'a[href*="live.bilibili.com/"][href*="live_from"], '
                    + '.room-card-wrapper a[href], '
                    + '.live-card a[href*="live.bilibili.com"], '
                    + 'a[href*="live.bilibili.com/"]');
                return card ? card.getAttribute('href') : '';
            })()
        """)
        if href:
            url = str(href)
            if not url.startswith("http"):
                url = "https:" + url if url.startswith("//") else "https://live.bilibili.com" + url
            return navigate(url, port)
        return {"ok": False, "error": "No live room found on current page"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_live_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get information about the current live room."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate("""
            (function(){
                var title = document.querySelector('.live-title .text, #link-header-title, .room-info-ctnr .title');
                var streamer = document.querySelector('.upper-row .room-owner-username, .live-anchor-name');
                var viewers = document.querySelector('.online-num, .live-count-text, .online');
                var area = document.querySelector('.live-area, .area-name, .room-info-ctnr .area-tag');
                var announcement = document.querySelector('.room-announcement, .room-detail .detail-content');
                var fans = document.querySelector('.fans-medal-item-text, .medal-info');
                var startTime = document.querySelector('.live-start-time, .room-info-time');
                return JSON.stringify({
                    ok: true,
                    title: title ? title.textContent.trim() : document.title,
                    streamer: streamer ? streamer.textContent.trim() : '',
                    viewers: viewers ? viewers.textContent.trim() : '',
                    area: area ? area.textContent.trim() : '',
                    announcement: announcement ? announcement.textContent.trim().substring(0, 200) : '',
                    fans_badge: fans ? fans.textContent.trim() : '',
                    start_time: startTime ? startTime.textContent.trim() : '',
                    url: window.location.href
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_live_danmaku(text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Send a danmaku in the live room."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_type(
            session,
            '#chat-control-panel-vm textarea, '
            '.chat-input-ctnr textarea, '
            '.danmaku-input textarea',
            text,
            label=f"Live danmaku: {text[:20]}", char_delay=0.04,
            clear_first=True, tool_name="Bilibili")
        time.sleep(0.3)
        interact.mcp_click(
            session,
            '#chat-control-panel-vm .bl-button--primary, '
            '.chat-input-ctnr .danmaku-btn-send, '
            '.chat-input-ctnr button',
            label="Send live danmaku", dwell=0.5, tool_name="Bilibili")
        return {"ok": True, "action": "live_danmaku_sent", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_live_stats(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get live stream statistics (viewers, danmaku density, etc.)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate("""
            (function(){
                var viewers = document.querySelector('.online-num, .live-count-text, .online');
                var likes = document.querySelector('.like-btn .text, .icon-action-item-text');
                var chatItems = document.querySelectorAll(
                    '#chat-items .chat-item, .chat-history-panel .chat-item, '
                    + '.chat-history-list .danmaku-item');
                return JSON.stringify({
                    ok: true,
                    viewers: viewers ? viewers.textContent.trim() : '',
                    likes: likes ? likes.textContent.trim() : '',
                    chat_count: chatItems.length,
                    url: window.location.href
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_live_replays(limit: int = 5, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get past live stream replays from a live room or UP space."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        r = session.evaluate(f"""
            (function(){{
                var replays = document.querySelectorAll(
                    '.live-playback-item, .playback-card, '
                    + '.section-content .video-card, .live-record-list .record-item');
                if(replays.length === 0){{
                    var sections = document.querySelectorAll('.sections-item, .video-sections-item');
                    var out = [];
                    for(var i=0; i<Math.min(sections.length, {limit}); i++){{
                        out.push({{
                            title: sections[i].textContent.trim().substring(0, 80),
                            url: ''
                        }});
                    }}
                    return JSON.stringify({{ok: true, count: out.length, replays: out, source: 'sections'}});
                }}
                var out = [];
                for(var i=0; i<Math.min(replays.length, {limit}); i++){{
                    var el = replays[i];
                    var titleEl = el.querySelector('.title, .text, a');
                    var a = el.querySelector('a[href]');
                    out.push({{
                        title: titleEl ? titleEl.textContent.trim().substring(0, 80) : '',
                        url: a ? a.getAttribute('href') || '' : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, replays: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": True, "count": 0, "replays": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Tasks 9-12: Content creation & management
# ---------------------------------------------------------------------------

def navigate_creative_center(section: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to Bilibili Creative Center."""
    sections = {
        "home": "https://member.bilibili.com/platform/home",
        "upload": "https://member.bilibili.com/platform/upload/video/frame",
        "content": "https://member.bilibili.com/platform/upload-manager/article",
        "article": "https://member.bilibili.com/platform/upload/text/edit",
        "data": "https://member.bilibili.com/platform/data/overview",
        "income": "https://member.bilibili.com/platform/finance/income",
        "comments": "https://member.bilibili.com/platform/comment",
        "fans": "https://member.bilibili.com/platform/fans/overview",
    }
    url = sections.get(section, "https://member.bilibili.com/platform/home") if section else sections["home"]
    return navigate(url, port)


def create_article_draft(title: str, content: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to article editor and create a draft."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://member.bilibili.com/platform/upload/text/edit",
            tool_name="Bilibili")
        time.sleep(5)

        interact.mcp_type(
            session,
            'input.article-title, .title-container input, '
            'input[placeholder*="标题"], input[placeholder*="title"]',
            title,
            label=f"Article title: {title[:30]}", char_delay=0.03,
            clear_first=True, tool_name="Bilibili")
        time.sleep(0.5)

        if content:
            interact.mcp_click(
                session,
                '.ql-editor, .article-editor .editor-content, '
                '.ProseMirror, .ql-blank',
                label="Editor body", dwell=0.3, tool_name="Bilibili")
            time.sleep(0.3)
            interact.mcp_type(
                session,
                '.ql-editor, .article-editor .editor-content, .ProseMirror',
                content,
                label="Article content", char_delay=0.02, tool_name="Bilibili")

        return {"ok": True, "action": "article_draft_created", "title": title}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_creative_inspiration(category: str = "tech", port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch trending topics from Creative Center for content ideas."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "creative_inspiration"})
        interact = _interact()
        interact.mcp_navigate(
            session, "https://member.bilibili.com/platform/home",
            tool_name="Bilibili")
        time.sleep(4)
        machine.transition(BiliState.IDLE)

        r = session.evaluate("""
            (function(){
                var hot = document.querySelectorAll(
                    '.hot-topic-item, .trend-item, .popular-content-item, '
                    + '.hot-word-item, .creative-topic-item');
                var out = [];
                for(var i=0; i<Math.min(hot.length, 20); i++){
                    var el = hot[i];
                    var title = el.querySelector('.title, .text, a') || el;
                    var heat = el.querySelector('.hot, .heat, .count');
                    out.push({
                        topic: title.textContent.trim().substring(0, 60),
                        heat: heat ? heat.textContent.trim() : ''
                    });
                }
                return JSON.stringify({ok: true, count: out.length, topics: out});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "count": 0, "topics": []}
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_data_center(time_range: str = "30d", port: int = CDP_PORT) -> Dict[str, Any]:
    """Fetch data center overview (views, fans trend)."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine.transition(BiliState.NAVIGATING, {"action": "data_center"})
        interact = _interact()
        interact.mcp_navigate(
            session, "https://member.bilibili.com/platform/data/overview",
            tool_name="Bilibili")
        time.sleep(5)
        machine.transition(BiliState.IDLE)

        r = session.evaluate("""
            (function(){
                var cards = document.querySelectorAll(
                    '.data-card, .overview-card, .data-overview-item, .summary-item');
                var out = {};
                out.metrics = [];
                for(var i=0; i<cards.length; i++){
                    var label = cards[i].querySelector('.label, .title, .name');
                    var value = cards[i].querySelector('.value, .number, .count, .num');
                    if(label && value)
                        out.metrics.push({
                            name: label.textContent.trim(),
                            value: value.textContent.trim()
                        });
                }
                return JSON.stringify(out);
            })()
        """)
        result = json.loads(r) if r else {}
        result["ok"] = True
        result["url"] = "https://member.bilibili.com/platform/data/overview"
        return result
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def manage_favorites(action: str = "list", name: Optional[str] = None,
                     fav_id: Optional[int] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Manage favorite folders: list, create, rename."""
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        if action == "list":
            uid = session.evaluate("""
                (function(){
                    var uid = document.cookie.match(/DedeUserID=(\\d+)/);
                    return uid ? uid[1] : '';
                })()
            """)
            if uid:
                machine.transition(BiliState.NAVIGATING, {"action": "favorites_list"})
                interact = _interact()
                interact.mcp_navigate(
                    session, f"https://space.bilibili.com/{uid}/favlist",
                    tool_name="Bilibili")
                time.sleep(4)
                machine.transition(BiliState.IDLE)

            r = session.evaluate("""
                (function(){
                    var items = document.querySelectorAll(
                        '.fav-list-item, .favlist-item, .fav-item, '
                        + '.channel-list .list-item');
                    var out = [];
                    for(var i=0; i<items.length; i++){
                        var nameEl = items[i].querySelector('.fav-name, .title, a.t');
                        var countEl = items[i].querySelector('.fav-count, .num, .count');
                        out.push({
                            index: i,
                            name: nameEl ? nameEl.textContent.trim() : '',
                            count: countEl ? countEl.textContent.trim() : ''
                        });
                    }
                    return JSON.stringify({ok: true, count: out.length, folders: out});
                })()
            """)
            return json.loads(r) if r else {"ok": True, "folders": []}

        elif action == "create" and name:
            interact = _interact()
            interact.mcp_click(
                session,
                '.fav-create-btn, .create-fav-btn, button[title*="新建"]',
                label="Create folder", dwell=0.5, tool_name="Bilibili")
            time.sleep(1)
            interact.mcp_type(
                session,
                '.fav-create-input input, input[placeholder*="收藏夹"], '
                '.dialog-body input',
                name,
                label=f"Folder name: {name}", char_delay=0.03,
                clear_first=True, tool_name="Bilibili")
            time.sleep(0.3)
            interact.mcp_click(
                session,
                '.fav-create-confirm, .dialog-footer .confirm, '
                '.bi-btn--primary',
                label="Confirm create", dwell=0.5, tool_name="Bilibili")
            return {"ok": True, "action": "folder_created", "name": name}

        return {"ok": False, "error": f"Unsupported action: {action}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Tasks 13-16: Community interaction
# ---------------------------------------------------------------------------

def post_dynamic(text: str, poll_options: Optional[list] = None,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Post a dynamic (feed post), optionally with poll options."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://t.bilibili.com",
            tool_name="Bilibili")
        time.sleep(3)

        interact.mcp_click(
            session,
            '.dynamic-editor .editor-input, '
            '.bili-dyn-publishing__input, '
            '.editor-container .editor, '
            'textarea.publish-textarea',
            label="Dynamic editor", dwell=0.5, tool_name="Bilibili")
        time.sleep(0.5)

        interact.mcp_type(
            session,
            '.dynamic-editor .editor-input, '
            '.bili-dyn-publishing__input .ql-editor, '
            '.editor-container .editor, '
            'textarea.publish-textarea',
            text,
            label=f"Dynamic: {text[:30]}", char_delay=0.03, tool_name="Bilibili")
        time.sleep(0.5)

        if poll_options and len(poll_options) >= 2:
            interact.mcp_click(
                session,
                '.bili-dyn-publishing__vote, .publish-tool-vote, '
                '.editor-toolbar [title*="投票"]',
                label="Add poll", dwell=0.5, tool_name="Bilibili")
            time.sleep(1)
            session.evaluate("""
                var inputs = document.querySelectorAll(
                    '.vote-option input, .poll-option input, '
                    + '.vote-input input');
                inputs.length
            """)
            for i, option in enumerate(poll_options[:4]):
                session.evaluate(f"""
                    var inputs = document.querySelectorAll(
                        '.vote-option input, .poll-option input, '
                        + '.vote-input input');
                    if(inputs[{i}]){{
                        inputs[{i}].focus();
                        inputs[{i}].value = {json.dumps(option)};
                        inputs[{i}].dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}
                """)
                time.sleep(0.2)

        return {"ok": True, "action": "dynamic_composed", "text": text,
                "has_poll": bool(poll_options)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def batch_reply_comments(reply_text: str, count: int = 3,
                         port: int = CDP_PORT) -> Dict[str, Any]:
    """Reply to multiple recent comments on a video."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        session.evaluate("window.scrollTo(0, 700)")
        time.sleep(2)
        _interact()
        replied = 0

        for i in range(count):
            success = session.evaluate(f"""
                (function(){{
                    var bc = document.querySelector('bili-comments');
                    if(!bc || !bc.shadowRoot) return false;
                    var threads = bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer');
                    if({i} >= threads.length) return false;
                    var tsr = threads[{i}].shadowRoot;
                    if(!tsr) return false;
                    var renderer = tsr.querySelector('bili-comment-renderer');
                    if(!renderer || !renderer.shadowRoot) return false;
                    var rsr = renderer.shadowRoot;
                    var replyBtn = rsr.querySelector('bili-comment-action-buttons-renderer');
                    if(!replyBtn || !replyBtn.shadowRoot) return false;
                    var btn = replyBtn.shadowRoot.querySelector('#reply-button, .reply-btn');
                    if(btn){{ btn.click(); return true; }}
                    return false;
                }})()
            """)
            if not success:
                continue
            time.sleep(1)

            session.evaluate(f"""
                (function(){{
                    var textareas = document.querySelectorAll(
                        '.reply-box-textarea, textarea.reply-box-textarea');
                    if(textareas.length > 0){{
                        var ta = textareas[textareas.length - 1];
                        ta.focus();
                        ta.value = {json.dumps(reply_text)};
                        ta.dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}
                }})()
            """)
            time.sleep(0.5)

            session.evaluate("""
                var btns = document.querySelectorAll(
                    '.reply-box-send, .reply-box .reply-btn');
                if(btns.length > 0) btns[btns.length - 1].click();
            """)
            replied += 1
            time.sleep(1)

        return {"ok": True, "action": "batch_replied", "replied": replied, "text": reply_text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_fan_medal(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to fan medal management page."""
    return navigate("https://link.bilibili.com/p/center/index#/user-center/medal/manage", port)


def navigate_topic_challenge(query: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to topic challenges / activities page."""
    if query:
        from urllib.parse import quote_plus
        url = f"https://search.bilibili.com/all?keyword={quote_plus(query)}"
    else:
        url = "https://www.bilibili.com/v/popular/all"
    return navigate(url, port)


# ---------------------------------------------------------------------------
# Advanced Tasks 17-19: Settings & Privacy
# ---------------------------------------------------------------------------

def navigate_privacy_settings(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to privacy settings page."""
    return navigate("https://space.bilibili.com/setting/privacy", port)


def set_privacy(space_visible: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Read or set privacy settings."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://space.bilibili.com/setting/privacy",
            tool_name="Bilibili")
        time.sleep(4)

        r = session.evaluate("""
            (function(){
                var items = document.querySelectorAll(
                    '.setting-item, .privacy-item, .list-item, '
                    + '.content-right .item');
                var out = [];
                for(var i=0; i<items.length; i++){
                    var label = items[i].querySelector('.label, .title, .name, .text');
                    var toggle = items[i].querySelector('input[type="checkbox"], .bui-switch input');
                    out.push({
                        label: label ? label.textContent.trim() : items[i].textContent.trim().substring(0, 50),
                        enabled: toggle ? toggle.checked : null
                    });
                }
                return JSON.stringify({ok: true, settings: out});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "settings": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_notification_settings(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to notification settings page."""
    return navigate("https://space.bilibili.com/setting/notify", port)


def set_notifications(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read current notification settings."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://space.bilibili.com/setting/notify",
            tool_name="Bilibili")
        time.sleep(4)

        r = session.evaluate("""
            (function(){
                var items = document.querySelectorAll(
                    '.setting-item, .notify-item, .list-item, '
                    + '.content-right .item');
                var out = [];
                for(var i=0; i<items.length; i++){
                    var label = items[i].querySelector('.label, .title, .name, .text');
                    var toggle = items[i].querySelector('input[type="checkbox"], .bui-switch input');
                    out.push({
                        label: label ? label.textContent.trim() : items[i].textContent.trim().substring(0, 50),
                        enabled: toggle ? toggle.checked : null
                    });
                }
                return JSON.stringify({ok: true, settings: out});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "settings": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_vip_page(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to Bilibili VIP/大会员 page (no purchase)."""
    return navigate("https://account.bilibili.com/big", port)


def get_vip_benefits(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read VIP benefits from the membership page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        interact = _interact()
        interact.mcp_navigate(
            session, "https://account.bilibili.com/big",
            tool_name="Bilibili")
        time.sleep(4)

        r = session.evaluate("""
            (function(){
                var items = document.querySelectorAll(
                    '.benefit-item-wrapper, .benefit-item, '
                    + '.privilege-item-wrapper, .vip-privilege-item, '
                    + '.item-box, .vip-card-item');
                var out = [];
                for(var i=0; i<items.length; i++){
                    var text = items[i].textContent.trim();
                    if(text.length < 5) continue;
                    var nameEl = items[i].querySelector('.name, .title, h3, h4');
                    var descEl = items[i].querySelector('.desc, .tip, p, .sub-title');
                    out.push({
                        name: nameEl ? nameEl.textContent.trim() : text.substring(0, 40),
                        desc: descEl ? descEl.textContent.trim().substring(0, 100) : text.substring(0, 100)
                    });
                }
                return JSON.stringify({ok: true, count: out.length, benefits: out});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "benefits": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced Task 20: Filtered search
# ---------------------------------------------------------------------------

def search_with_filters(query: str, duration: Optional[str] = None,
                        sort_by: Optional[str] = None, tids: Optional[str] = None,
                        limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search with filters: duration (0-10, 10-30, 30-60, 60+), sort (click, pubdate, dm, stow)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Bilibili session"}
    try:
        machine = get_machine(_session_name)
        machine.transition(BiliState.NAVIGATING, {"action": "filter_search"})
        interact = _interact()

        from urllib.parse import quote_plus
        url = f"https://search.bilibili.com/all?keyword={quote_plus(query)}"
        params = []
        if duration:
            dur_map = {"0-10": "1", "10-30": "2", "30-60": "3", "60+": "4"}
            d = dur_map.get(duration, duration)
            params.append(f"duration={d}")
        if sort_by:
            sort_map = {"views": "click", "date": "pubdate", "danmaku": "dm", "favorites": "stow"}
            s = sort_map.get(sort_by, sort_by)
            params.append(f"order={s}")
        if tids:
            params.append(f"tids={tids}")
        if params:
            url += "&" + "&".join(params)

        interact.mcp_navigate(session, url, tool_name="Bilibili")

        for _ in range(15):
            time.sleep(1)
            count = session.evaluate(
                "document.querySelectorAll('.bili-video-card').length")
            if count and int(count) > 0:
                break

        machine.transition(BiliState.SEARCHING)
        return search_videos(query, limit, port)
    except Exception as e:
        machine.transition(BiliState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


# Apply ToS guard to all public functions defined in this module
import types as _types
for _name in list(globals()):
    _obj = globals()[_name]
    if (isinstance(_obj, _types.FunctionType)
            and not _name.startswith("_")
            and getattr(_obj, "__module__", "") == __name__):
        globals()[_name] = _tos_guard(_obj)
del _types, _name, _obj

