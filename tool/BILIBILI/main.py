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

from logic.tool.blueprint.mcp import MCPToolBase
from interface.config import get_color


def main():
    tool = MCPToolBase("BILIBILI", session_name="bilibili")

    parser = argparse.ArgumentParser(
        description="Bilibili video platform automation via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., BILIBILI --mcp-boot, BILIBILI --mcp-play",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    # Session & status
    sub.add_parser("boot", help="Boot Bilibili session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Recover from error state")
    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("state", help="Get comprehensive MCP state")

    # Navigation
    p_nav = sub.add_parser("navigate", help="Navigate to a section or URL")
    p_nav.add_argument("target", help="Section name or URL")
    p_open = sub.add_parser("open", help="Open video by BV ID or URL")
    p_open.add_argument("video", help="BV ID or URL")

    # Search
    p_search = sub.add_parser("search", help="Search for videos")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10)

    # Info & screenshot
    p_info = sub.add_parser("info", help="Get video details")
    p_info.add_argument("url", nargs="?", help="Video URL (default: current)")
    p_shot = sub.add_parser("screenshot", help="Capture page screenshot")
    p_shot.add_argument("--output", help="Output file path")

    # Playback
    sub.add_parser("play", help="Play current video")
    sub.add_parser("pause", help="Pause current video")
    p_seek = sub.add_parser("seek", help="Seek to position")
    p_seek.add_argument("target", help="Seconds, mm:ss, pct, or +/-N")
    p_vol = sub.add_parser("volume", help="Set volume or mute")
    p_vol.add_argument("level", nargs="?", type=int)
    p_vol.add_argument("--mute", action="store_true")
    p_vol.add_argument("--unmute", action="store_true")
    p_speed = sub.add_parser("speed", help="Set playback speed")
    p_speed.add_argument("rate", nargs="?", type=float)
    p_qual = sub.add_parser("quality", help="Set video quality")
    p_qual.add_argument("level", nargs="?")
    sub.add_parser("fullscreen", help="Toggle fullscreen")
    sub.add_parser("widescreen", help="Toggle widescreen")
    sub.add_parser("pip", help="Toggle picture-in-picture")

    # Danmaku
    p_dm = sub.add_parser("danmaku", help="Toggle danmaku on/off")
    p_dm.add_argument("--on", action="store_true")
    p_dm.add_argument("--off", action="store_true")
    p_send_dm = sub.add_parser("send-danmaku", help="Send a danmaku message")
    p_send_dm.add_argument("text", help="Danmaku text")

    # Engagement
    sub.add_parser("like", help="Like current video")
    p_coin = sub.add_parser("coin", help="Throw coins")
    p_coin.add_argument("--amount", type=int, default=1, choices=[1, 2])
    sub.add_parser("favorite", help="Favorite current video")
    sub.add_parser("triple", help="Triple combo (like + coin + favorite)")
    sub.add_parser("share", help="Share current video")
    sub.add_parser("follow", help="Follow/unfollow UP")
    p_comment = sub.add_parser("comment", help="Post a comment")
    p_comment.add_argument("text", help="Comment text")

    # Discovery
    sub.add_parser("next", help="Play next recommended video")
    p_recs = sub.add_parser("recommendations", help="List recommended videos")
    p_recs.add_argument("--limit", type=int, default=10)
    p_comments = sub.add_parser("comments", help="Extract top comments")
    p_comments.add_argument("--limit", type=int, default=10)
    p_trend = sub.add_parser("trending", help="List trending/popular videos")
    p_trend.add_argument("--limit", type=int, default=20)
    p_hist = sub.add_parser("history", help="View watch history")
    p_hist.add_argument("--limit", type=int, default=20)

    sub.add_parser("back", help="Navigate back to previous page")
    sub.add_parser("layout", help="Identify home page layout areas")
    sub.add_parser("uploader", help="Navigate to current video's UP page")
    sub.add_parser("personal", help="Navigate to personal space")

    # Advanced: Danmaku settings
    sub.add_parser("danmaku-settings", help="View danmaku display settings")
    p_dm_filter = sub.add_parser("danmaku-filter", help="Add danmaku block keyword")
    p_dm_filter.add_argument("keyword", help="Keyword to block")
    p_dm_opacity = sub.add_parser("danmaku-opacity", help="Set danmaku opacity")
    p_dm_opacity.add_argument("opacity", type=int, help="Opacity 0-100")

    # Advanced: Chapters
    sub.add_parser("chapters", help="List video chapters")
    p_seek_ch = sub.add_parser("seek-chapter", help="Seek to chapter by index")
    p_seek_ch.add_argument("index", type=int, help="Chapter index (0-based)")

    # Advanced: Auto speed
    sub.add_parser("auto-speed", help="Auto-adjust speed based on content type")

    # Advanced: Subtitles
    sub.add_parser("subtitles", help="Check subtitle availability")
    p_sub_toggle = sub.add_parser("toggle-subtitles", help="Toggle subtitles")
    p_sub_toggle.add_argument("--on", action="store_true", default=True)
    p_sub_toggle.add_argument("--off", action="store_true")

    # Advanced: Watch Later
    sub.add_parser("watchlater-add", help="Add current video to Watch Later")
    p_wl = sub.add_parser("watchlater", help="List Watch Later videos")
    p_wl.add_argument("--limit", type=int, default=20)
    sub.add_parser("watchlater-play", help="Play Watch Later list")

    # Advanced: Live
    p_live = sub.add_parser("live", help="Navigate to Bilibili Live")
    p_live.add_argument("--category", help="Category: tech, game, music, anime, entertainment")
    p_live_enter = sub.add_parser("live-enter", help="Enter a live room")
    p_live_enter.add_argument("room_id", nargs="?", help="Room ID (optional)")
    sub.add_parser("live-info", help="Get current live room info")
    p_live_dm = sub.add_parser("live-danmaku", help="Send danmaku in live room")
    p_live_dm.add_argument("text", help="Danmaku text")
    sub.add_parser("live-stats", help="Get live stream statistics")
    p_live_replays = sub.add_parser("live-replays", help="Get past live replays")
    p_live_replays.add_argument("--limit", type=int, default=5)

    # Advanced: Creative Center
    p_creative = sub.add_parser("creative", help="Navigate to Creative Center")
    p_creative.add_argument("section", nargs="?", help="Section: home, upload, content, article, data, fans")
    p_article = sub.add_parser("article-draft", help="Create an article draft")
    p_article.add_argument("title", help="Article title")
    p_article.add_argument("--content", default="", help="Article body text")
    p_inspire = sub.add_parser("inspiration", help="Fetch creative inspiration topics")
    p_inspire.add_argument("--category", default="tech")
    sub.add_parser("data-center", help="View data center overview")

    # Advanced: Favorites management
    p_fav_mgmt = sub.add_parser("favorites-manage", help="Manage favorite folders")
    p_fav_mgmt.add_argument("action", choices=["list", "create"], help="Action")
    p_fav_mgmt.add_argument("--name", help="Folder name (for create)")

    # Advanced: Community
    p_dyn = sub.add_parser("post-dynamic", help="Post a dynamic/feed post")
    p_dyn.add_argument("text", help="Dynamic text")
    p_dyn.add_argument("--poll", nargs="+", help="Poll options (2-4)")
    p_batch_reply = sub.add_parser("batch-reply", help="Batch reply to comments")
    p_batch_reply.add_argument("text", help="Reply text")
    p_batch_reply.add_argument("--count", type=int, default=3)
    sub.add_parser("fan-medal", help="Navigate to fan medal page")
    p_topic = sub.add_parser("topic-challenge", help="Navigate to topic challenges")
    p_topic.add_argument("query", nargs="?", help="Topic search query")

    # Advanced: Settings & Privacy
    sub.add_parser("privacy-settings", help="Navigate to privacy settings")
    sub.add_parser("privacy", help="Read privacy settings")
    sub.add_parser("notification-settings", help="Navigate to notification settings")
    sub.add_parser("notifications", help="Read notification settings")
    sub.add_parser("vip-page", help="Navigate to VIP/大会员 page")
    sub.add_parser("vip-benefits", help="Read VIP benefits")

    # Advanced: Filtered search
    p_fsearch = sub.add_parser("filter-search", help="Search with filters")
    p_fsearch.add_argument("query", help="Search query")
    p_fsearch.add_argument("--duration", help="Duration filter: 0-10, 10-30, 30-60, 60+")
    p_fsearch.add_argument("--sort", help="Sort: views, date, danmaku, favorites")
    p_fsearch.add_argument("--limit", type=int, default=10)

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    B = get_color("BOLD")
    G = get_color("GREEN")
    R = get_color("RED")
    Y = get_color("YELLOW")
    get_color("BLUE")
    E = get_color("RESET")

    from tool.BILIBILI.logic.chrome import api

    if args.command == "boot":
        r = api.boot_session()
        if r.get("ok"):
            print(f"  {B}{G}Session {r.get('action', 'booted')}{E}")
            print(f"  State: {r.get('state', '?')}")
        else:
            print(f"  {B}{R}Boot failed{E}: {r.get('error')}")

    elif args.command == "session":
        r = api.get_session_status()
        st = r.get("state", "?")
        c = G if st == "idle" else (Y if st in ("navigating", "watching") else R)
        print(f"  State:   {B}{c}{st}{E}")
        print(f"  Session: {'alive' if r.get('session_alive') else 'none'}")
        print(f"  CDP:     {'ok' if r.get('cdp_available') else 'unavail'}")
        if r.get("last_url"): print(f"  URL:     {r['last_url'][:80]}")
        if r.get("last_bvid"): print(f"  BVID:    {r['last_bvid']}")

    elif args.command == "recover":
        r = api._recover()
        print(f"  {B}{G}Recovered{E}" if r.get("ok") else f"  {R}Failed: {r.get('error')}{E}")

    elif args.command == "status":
        r = api.get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Auth: {B}{G if auth else Y}{'Yes' if auth else 'No'}{E}")
        if r.get("username"): print(f"  User: {r['username']}")

    elif args.command == "page":
        r = api.get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')[:80]}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "state":
        r = api.get_mcp_state()
        if r.get("ok"):
            print(f"  {B}URL:{E}      {r.get('url', '?')[:80]}")
            print(f"  {B}Section:{E}  {r.get('section', '?')}")
            if r.get("video_title"): print(f"  {B}Video:{E}    {r['video_title'][:70]}")
            if r.get("channel"): print(f"  {B}UP:{E}       {r['channel']}")
            if r.get("bvid"): print(f"  {B}BVID:{E}     {r['bvid']}")
            p = r.get("player", {})
            if p:
                st = "paused" if p.get("paused") else "playing"
                print(f"  {B}Player:{E}   {st} | {p.get('currentTime',0)}s / {p.get('duration',0)}s ({p.get('progress_pct',0)}%)")
                print(f"  {B}Volume:{E}   {p.get('volume','?')}% {'(muted)' if p.get('muted') else ''}")
                print(f"  {B}Speed:{E}    {p.get('playbackRate',1)}x")
            print(f"  {B}Quality:{E}  {r.get('quality', '?')}")
            print(f"  {B}Danmaku:{E}  {r.get('danmaku', '?')}")
            if r.get("likes"): print(f"  {B}Likes:{E}    {r['likes']}  Coins: {r.get('coins','')}  Favs: {r.get('favorites','')}")
            print(f"  {B}Auth:{E}     {'Yes' if r.get('authenticated') else 'No'}")
            ms = r.get("machine_state", {})
            print(f"  {B}Machine:{E}  {ms.get('state', '?')}")
        else:
            print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "navigate":
        r = api.navigate(args.target)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to {r.get('target')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "open":
        r = api.open_video(args.video)
        if r.get("ok"): print(f"  {B}{G}Opened{E} {r.get('url', '?')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "search":
        r = api.search_videos(args.query, limit=args.limit)
        if r.get("ok"):
            print(f"  Search '{r.get('query','')}': {r.get('count', 0)} results")
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:65]}")
                if v.get("author"): print(f"       {v['author']} | {v.get('views', '')}")
                if v.get("bvid"): print(f"       {v['url'][:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "info":
        r = api.get_video_info(video_url=args.url)
        if r.get("ok"):
            print(f"  {B}Title:{E}    {r.get('title', '?')}")
            print(f"  {B}Author:{E}   {r.get('author', '?')}")
            print(f"  {B}Views:{E}    {r.get('views', '?')}")
            print(f"  {B}Danmaku:{E}  {r.get('danmaku', '?')}")
            print(f"  {B}Date:{E}     {r.get('date', '?')}")
            print(f"  {B}Likes:{E}    {r.get('likes', '')}  Coins: {r.get('coins', '')}  Favs: {r.get('favorites', '')}")
            print(f"  {B}BVID:{E}     {r.get('bvid', '?')}")
            if r.get("description"): print(f"  {B}Desc:{E}     {r['description'][:200]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "screenshot":
        r = api.take_screenshot(output_path=args.output)
        if r.get("ok"): print(f"  {B}{G}Saved{E} {r['path']} ({r['size']} bytes)")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "play":
        r = api.play()
        print(f"  {B}{G}Playing{E}" if r.get("ok") else f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "pause":
        r = api.pause()
        print(f"  {B}{Y}Paused{E}" if r.get("ok") else f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "seek":
        r = api.seek(args.target)
        if r.get("ok"): print(f"  {B}{G}Seeked{E} to {r.get('time', '?')}s")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "volume":
        m = True if args.mute else (False if args.unmute else None)
        r = api.volume(level=args.level, mute=m)
        if r.get("ok"): print(f"  Volume: {r.get('volume', '?')}% {'(muted)' if r.get('muted') else ''}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "speed":
        r = api.speed(rate=args.rate)
        if r.get("ok"): print(f"  Speed: {r.get('speed', '?')}x")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "quality":
        r = api.quality(level=args.level)
        if r.get("ok"): print(f"  Available: {', '.join(r.get('available', []))}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "fullscreen":
        r = api.fullscreen()
        print(f"  {G}Toggled fullscreen{E}" if r.get("ok") else f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "widescreen":
        r = api.widescreen()
        print(f"  {G}Toggled widescreen{E}" if r.get("ok") else f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "pip":
        r = api.pip()
        if r.get("ok"): print(f"  PiP: {'on' if r.get('pip') else 'off'}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "danmaku":
        toggle = True if args.on else (False if args.off else None)
        r = api.danmaku(toggle=toggle)
        if r.get("ok"): print(f"  Danmaku: {r.get('danmaku', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "send-danmaku":
        r = api.send_danmaku(args.text)
        if r.get("ok"): print(f"  {B}{G}Sent{E} danmaku: {args.text}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "like":
        r = api.like()
        if r.get("ok"): print(f"  {B}{G}Liked{E} — {r.get('count', '')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "coin":
        r = api.coin(amount=args.amount)
        if r.get("ok"): print(f"  {B}{G}Coined{E} x{r.get('amount', 1)}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "favorite":
        r = api.favorite()
        print(f"  {B}{G}Favorited{E}" if r.get("ok") else f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "triple":
        r = api.triple()
        if r.get("ok"): print(f"  {B}{G}Triple combo (三连) done!{E}")
        else: print(f"  {R}Some actions failed{E}: {json.dumps(r.get('details', {}), indent=2)}")
    elif args.command == "share":
        r = api.share()
        if r.get("ok"): print(f"  URL: {r.get('share_url', '?')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "follow":
        r = api.follow()
        if r.get("ok"): print(f"  {B}{G}Toggled{E}: {r.get('button_text', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "comment":
        r = api.comment(args.text)
        if r.get("ok"): print(f"  {B}{G}Commented{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "next":
        r = api.next_video()
        if r.get("ok"): print(f"  {B}{G}Next video{E}: {r.get('url', '?')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "recommendations":
        r = api.get_recommendations(limit=args.limit)
        if r.get("ok"):
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:60]}")
                if v.get("author"): print(f"       {v['author']} | {v.get('views', '')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")
    elif args.command == "comments":
        r = api.get_comments(limit=args.limit)
        if r.get("ok"):
            for c in r.get("comments", []):
                print(f"  {B}{c.get('author', '?')}{E} ({c.get('time', '')})")
                print(f"    {c.get('text', '')[:120]}")
                if c.get("likes", "0") != "0": print(f"    likes: {c['likes']}")
                print()
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "trending":
        r = api.get_trending(limit=args.limit)
        if r.get("ok"):
            print(f"  Trending: {r.get('count', 0)} videos")
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:60]}")
                if v.get("author"): print(f"       {v['author']} | {v.get('views', '')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "history":
        r = api.get_history(limit=args.limit)
        if r.get("ok"):
            print(f"  History: {r.get('count', 0)} items")
            for i, v in enumerate(r.get("results", [])):
                prog = f" ({v['progress']})" if v.get("progress") else ""
                print(f"  [{i+1:2d}] {v.get('title', '?')[:60]}{prog}")
                if v.get("author"): print(f"       {v['author']}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "back":
        r = api.go_back()
        if r.get("ok"): print(f"  {B}{G}Navigated back{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "layout":
        r = api.get_home_layout()
        if r.get("ok"):
            for area in r.get("areas", []):
                print(f"    - {area}")
            tabs = r.get("nav_tabs", [])
            if tabs: print(f"  Tabs: {', '.join(tabs[:10])}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "uploader":
        r = api.navigate_to_uploader()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to UP: {r.get('up_name', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "personal":
        r = api.navigate_personal()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to personal space")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    # --- Advanced commands ---
    elif args.command == "danmaku-settings":
        r = api.get_danmaku_settings()
        if r.get("ok"):
            print(f"  Panel open: {r.get('panel_open', False)}")
            for sw in r.get("switches", []):
                st = "on" if sw.get("checked") else "off"
                print(f"    [{st}] {sw.get('label', '?')}")
            if r.get("opacity"): print(f"  Opacity: {r['opacity']}")
            if r.get("area"): print(f"  Area: {', '.join(r['area'])}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "danmaku-filter":
        r = api.set_danmaku_filter(args.keyword)
        if r.get("ok"): print(f"  {B}{G}Added filter{E}: {args.keyword}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "danmaku-opacity":
        r = api.set_danmaku_opacity(args.opacity)
        if r.get("ok"): print(f"  {B}{G}Opacity set{E} to {args.opacity}%")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "chapters":
        r = api.get_chapters()
        if r.get("ok"):
            chs = r.get("chapters", [])
            if chs:
                print(f"  Chapters: {len(chs)}")
                for ch in chs:
                    t = f" {ch['time']}" if ch.get("time") else ""
                    print(f"  [{ch['index']}]{t} {ch.get('title', '?')[:60]}")
            else:
                print(f"  No chapters found.")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "seek-chapter":
        r = api.seek_to_chapter(args.index)
        if r.get("ok"): print(f"  {B}{G}Seeked{E} to chapter {args.index}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "auto-speed":
        r = api.auto_speed()
        if r.get("ok"):
            print(f"  {B}Type:{E}  {r.get('detected_type', '?')}")
            print(f"  {B}Speed:{E} {r.get('applied_speed', '?')}x")
            print(f"  Title: {r.get('title', '')[:60]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "subtitles":
        r = api.get_subtitles()
        if r.get("ok"):
            if r.get("available"):
                print(f"  Subtitle options: {', '.join(r.get('options', []))}")
            else:
                print(f"  {Y}No subtitles available{E}: {r.get('message', '')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "toggle-subtitles":
        on = not args.off
        r = api.toggle_subtitles(on=on)
        if r.get("ok"): print(f"  {B}{G}Subtitles {'on' if on else 'off'}{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "watchlater-add":
        r = api.add_to_watchlater()
        if r.get("ok"): print(f"  {B}{G}Added to Watch Later{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "watchlater":
        r = api.get_watchlater(limit=args.limit)
        if r.get("ok"):
            print(f"  Watch Later: {r.get('count', 0)} items")
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:60]}")
                if v.get("author"): print(f"       {v['author']}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "watchlater-play":
        r = api.play_watchlater()
        if r.get("ok"): print(f"  {B}{G}Playing Watch Later{E}: {r.get('url', '')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live":
        r = api.navigate_live(category=args.category)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to Bilibili Live")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live-enter":
        r = api.enter_live_room(room_id=args.room_id)
        if r.get("ok"): print(f"  {B}{G}Entered{E} live room")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live-info":
        r = api.get_live_info()
        if r.get("ok"):
            print(f"  {B}Title:{E}    {r.get('title', '?')}")
            print(f"  {B}Streamer:{E} {r.get('streamer', '?')}")
            print(f"  {B}Viewers:{E}  {r.get('viewers', '?')}")
            print(f"  {B}Area:{E}     {r.get('area', '?')}")
            if r.get("announcement"): print(f"  {B}Notice:{E}   {r['announcement'][:100]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live-danmaku":
        r = api.send_live_danmaku(args.text)
        if r.get("ok"): print(f"  {B}{G}Sent{E} live danmaku: {args.text}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live-stats":
        r = api.get_live_stats()
        if r.get("ok"):
            print(f"  Viewers:  {r.get('viewers', '?')}")
            print(f"  Likes:    {r.get('likes', '?')}")
            print(f"  Chat:     {r.get('chat_count', 0)} messages")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "live-replays":
        r = api.get_live_replays(limit=args.limit)
        if r.get("ok"):
            print(f"  Replays: {r.get('count', 0)}")
            for i, rp in enumerate(r.get("replays", [])):
                print(f"  [{i+1}] {rp.get('title', '?')[:60]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "creative":
        r = api.navigate_creative_center(section=args.section)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to Creative Center")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "article-draft":
        r = api.create_article_draft(args.title, content=args.content)
        if r.get("ok"): print(f"  {B}{G}Draft created{E}: {args.title}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "inspiration":
        r = api.get_creative_inspiration(category=args.category)
        if r.get("ok"):
            print(f"  Topics: {r.get('count', 0)}")
            for t in r.get("topics", []):
                heat = f" ({t['heat']})" if t.get("heat") else ""
                print(f"    - {t.get('topic', '?')}{heat}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "data-center":
        r = api.get_data_center()
        if r.get("ok"):
            print(f"  Data Center:")
            for m in r.get("metrics", []):
                print(f"    {B}{m.get('name', '?')}:{E} {m.get('value', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "favorites-manage":
        r = api.manage_favorites(action=args.action, name=args.name)
        if r.get("ok"):
            if args.action == "list":
                print(f"  Folders: {r.get('count', 0)}")
                for f in r.get("folders", []):
                    cnt = f" ({f['count']})" if f.get("count") else ""
                    print(f"  [{f['index']}] {f.get('name', '?')}{cnt}")
            else:
                print(f"  {B}{G}{args.action.capitalize()}d{E} folder: {args.name or '?'}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "post-dynamic":
        r = api.post_dynamic(args.text, poll_options=args.poll)
        if r.get("ok"):
            poll_info = " (with poll)" if r.get("has_poll") else ""
            print(f"  {B}{G}Dynamic composed{E}{poll_info}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "batch-reply":
        r = api.batch_reply_comments(args.text, count=args.count)
        if r.get("ok"): print(f"  {B}{G}Replied{E} to {r.get('replied', 0)} comments")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "fan-medal":
        r = api.navigate_fan_medal()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to fan medal page")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "topic-challenge":
        r = api.navigate_topic_challenge(query=args.query)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to topic challenges")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "privacy-settings":
        r = api.navigate_privacy_settings()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to privacy settings")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "privacy":
        r = api.set_privacy()
        if r.get("ok"):
            print(f"  Privacy settings:")
            for s in r.get("settings", []):
                st = "on" if s.get("enabled") else ("off" if s.get("enabled") is False else "?")
                print(f"    [{st}] {s.get('label', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "notification-settings":
        r = api.navigate_notification_settings()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to notification settings")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "notifications":
        r = api.set_notifications()
        if r.get("ok"):
            print(f"  Notification settings:")
            for s in r.get("settings", []):
                st = "on" if s.get("enabled") else ("off" if s.get("enabled") is False else "?")
                print(f"    [{st}] {s.get('label', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "vip-page":
        r = api.navigate_vip_page()
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to VIP page")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "vip-benefits":
        r = api.get_vip_benefits()
        if r.get("ok"):
            print(f"  VIP Benefits: {r.get('count', 0)}")
            for b in r.get("benefits", []):
                desc = f" - {b['description']}" if b.get("description") else ""
                print(f"    - {b.get('name', '?')}{desc}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "filter-search":
        r = api.search_with_filters(
            args.query, duration=args.duration, sort_by=args.sort, limit=args.limit)
        if r.get("ok"):
            print(f"  Filtered search '{r.get('query', '')}': {r.get('count', 0)} results")
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:65]}")
                if v.get("author"): print(f"       {v['author']} | {v.get('views', '')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
