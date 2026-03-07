#!/usr/bin/env python3
"""BILIBILI - Bilibili video platform automation via CDMCP."""
import sys
import argparse
import json
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.interface.config import get_color

_TOOL_DIR = Path(__file__).resolve().parent
_REPORT_DIR = _TOOL_DIR / "data" / "report"
_REPORT_DIR.mkdir(parents=True, exist_ok=True)

CDP_PORT = 9222


def _find_bilibili_tab(port=CDP_PORT):
    from logic.chrome.session import list_tabs
    tabs = list_tabs(port)
    for t in tabs:
        url = t.get("url", "")
        if t.get("type") == "page" and "bilibili.com" in url:
            return t
    return None


def _get_cdp(port=CDP_PORT):
    from logic.chrome.session import CDPSession
    tab = _find_bilibili_tab(port)
    if not tab:
        return None
    return CDPSession(tab["webSocketDebuggerUrl"])


def get_auth_state(port=CDP_PORT):
    cdp = _get_cdp(port)
    if not cdp:
        return {"ok": False, "authenticated": False, "error": "No Bilibili tab found"}
    result = cdp.evaluate('''
    (function(){
        var avatar = document.querySelector('.header-avatar-wrap .header-entry-mini');
        var loginBtn = document.querySelector('.header-login-entry');
        var userName = document.querySelector('.header-entry-mini .nickname');
        if(!userName) userName = document.querySelector('.header-avatar-wrap img');
        return JSON.stringify({
            authenticated: !loginBtn && !!avatar,
            username: userName ? (userName.textContent || userName.getAttribute('alt') || '').trim() : '',
            title: document.title
        });
    })()
    ''')
    cdp.close()
    data = json.loads(result) if result else {"authenticated": False}
    data["ok"] = True
    return data


def search_videos(query, limit=10, port=CDP_PORT):
    from logic.chrome.session import CDPSession
    import time
    tab = _find_bilibili_tab(port)
    if not tab:
        return {"ok": False, "error": "No Bilibili tab found"}
    cdp = CDPSession(tab["webSocketDebuggerUrl"])
    search_url = f"https://search.bilibili.com/all?keyword={query}"
    cdp.send_and_recv("Page.navigate", {"url": search_url}, timeout=15)
    time.sleep(3)
    results_js = f'''
    (function(){{
        var items = document.querySelectorAll('.video-list-item, .bili-video-card');
        var out = [];
        for(var i=0; i<items.length && i<{limit}; i++){{
            var el = items[i];
            var h3 = el.querySelector('h3, .bili-video-card__info--tit');
            var titleEl = h3 ? (h3.querySelector('a') || h3) : el.querySelector('.title-text');
            var authorEl = el.querySelector('.bili-video-card__info--author, .up-name');
            var durationEl = el.querySelector('.bili-video-card__stats--duration, .duration');
            var viewsEl = el.querySelector('.bili-video-card__stats--item, .play-text');
            var linkEl = el.querySelector('a[href*="/video/"]');
            out.push({{
                title: titleEl ? titleEl.textContent.trim() : '',
                author: authorEl ? authorEl.textContent.trim() : '',
                duration: durationEl ? durationEl.textContent.trim() : '',
                views: viewsEl ? viewsEl.textContent.trim() : '',
                url: linkEl ? linkEl.href : '',
                bvid: linkEl ? (linkEl.href.match(/BV[a-zA-Z0-9]+/) || [''])[0] : ''
            }});
        }}
        return JSON.stringify(out);
    }})()
    '''
    raw = cdp.evaluate(results_js)
    cdp.close()
    results = json.loads(raw) if raw else []
    return {"ok": True, "query": query, "results": results, "count": len(results)}


def get_video_info(video_url=None, port=CDP_PORT):
    import time
    from logic.chrome.session import CDPSession
    tab = _find_bilibili_tab(port)
    if not tab:
        return {"ok": False, "error": "No Bilibili tab found"}
    cdp = CDPSession(tab["webSocketDebuggerUrl"])
    if video_url:
        cdp.send_and_recv("Page.navigate", {"url": video_url}, timeout=15)
        time.sleep(3)
    info_js = '''
    (function(){
        var title = document.querySelector('.video-title, h1.title');
        var author = document.querySelector('.up-name, .username');
        var views = document.querySelector('.view-text, .view.item');
        var danmaku = document.querySelector('.dm-text, .dm.item');
        var date = document.querySelector('.pubdate-text, .pudate-text');
        var likes = document.querySelector('.video-like-info .video-like-number');
        var coins = document.querySelector('.video-coin-info .video-coin-number');
        var favs = document.querySelector('.video-fav-info .video-fav-number');
        var shares = document.querySelector('#share-btn-outer, .video-share-info .video-share-number');
        var desc = document.querySelector('.basic-desc-info, .desc-info-text');
        var bvid = window.location.pathname.match(/BV[a-zA-Z0-9]+/);
        return JSON.stringify({
            title: title ? title.textContent.trim() : document.title,
            author: author ? author.textContent.trim() : '',
            views: views ? views.textContent.trim() : '',
            danmaku: danmaku ? danmaku.textContent.trim() : '',
            date: date ? date.textContent.trim() : '',
            likes: likes ? likes.textContent.trim() : '',
            coins: coins ? coins.textContent.trim() : '',
            favorites: favs ? favs.textContent.trim() : '',
            shares: shares ? shares.textContent.trim() : '',
            description: desc ? desc.textContent.trim().substring(0, 500) : '',
            bvid: bvid ? bvid[0] : '',
            url: window.location.href
        });
    })()
    '''
    raw = cdp.evaluate(info_js)
    cdp.close()
    data = json.loads(raw) if raw else {}
    data["ok"] = True
    return data


def take_screenshot(output_path=None, port=CDP_PORT):
    from logic.chrome.session import CDPSession, capture_screenshot
    tab = _find_bilibili_tab(port)
    if not tab:
        return {"ok": False, "error": "No Bilibili tab found"}
    cdp = CDPSession(tab["webSocketDebuggerUrl"])
    img = capture_screenshot(cdp)
    cdp.close()
    if not img:
        return {"ok": False, "error": "Screenshot failed"}
    if not output_path:
        output_path = str(_REPORT_DIR / "screenshot.png")
    with open(output_path, "wb") as f:
        f.write(img)
    return {"ok": True, "path": output_path, "size": len(img)}


def main():
    tool = ToolBase("BILIBILI")

    parser = argparse.ArgumentParser(
        description="Bilibili video platform automation via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check Bilibili auth state")

    p_search = sub.add_parser("search", help="Search Bilibili for videos")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    p_info = sub.add_parser("info", help="Get video details")
    p_info.add_argument("url", nargs="?", default=None, help="Video URL (default: current)")

    p_shot = sub.add_parser("screenshot", help="Capture page screenshot")
    p_shot.add_argument("--output", default=None, help="Output file path")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    if args.command == "status":
        r = get_auth_state()
        if r.get("authenticated"):
            print(f"  {BOLD}{GREEN}Authenticated{RESET}: {r.get('username', 'unknown')}")
        else:
            print(f"  {BOLD}{RED}Not authenticated{RESET}")
        print(f"  {BOLD}Title:{RESET} {r.get('title', 'N/A')}")

    elif args.command == "search":
        print(f"  {BOLD}{BLUE}Searching{RESET} Bilibili for '{args.query}'...")
        r = search_videos(args.query, limit=args.limit)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Found{RESET} {r['count']} results:")
            for i, v in enumerate(r.get("results", [])):
                print(f"    {i+1}. {v.get('title', 'N/A')}")
                print(f"       {v.get('author', '')} | {v.get('views', '')} | {v.get('duration', '')}")
                if v.get("url"):
                    print(f"       {v['url'][:80]}")
        else:
            print(f"  {BOLD}{RED}Search failed:{RESET} {r.get('error', 'unknown')}")

    elif args.command == "info":
        print(f"  {BOLD}{BLUE}Getting{RESET} video info...")
        r = get_video_info(video_url=args.url)
        if r.get("ok"):
            print(f"  {BOLD}Title:{RESET} {r.get('title', 'N/A')}")
            print(f"  {BOLD}Author:{RESET} {r.get('author', 'N/A')}")
            print(f"  {BOLD}Views:{RESET} {r.get('views', 'N/A')}")
            print(f"  {BOLD}Danmaku:{RESET} {r.get('danmaku', 'N/A')}")
            print(f"  {BOLD}Date:{RESET} {r.get('date', 'N/A')}")
            print(f"  {BOLD}Likes:{RESET} {r.get('likes', 'N/A')}")
            print(f"  {BOLD}Coins:{RESET} {r.get('coins', 'N/A')}")
            print(f"  {BOLD}Favorites:{RESET} {r.get('favorites', 'N/A')}")
            print(f"  {BOLD}BVID:{RESET} {r.get('bvid', 'N/A')}")
            desc = r.get("description", "")
            if desc:
                print(f"  {BOLD}Description:{RESET} {desc[:200]}")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', 'unknown')}")

    elif args.command == "screenshot":
        r = take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Screenshot saved:{RESET} {r['path']} ({r['size']} bytes)")
        else:
            print(f"  {BOLD}{RED}Failed:{RESET} {r.get('error', 'unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
