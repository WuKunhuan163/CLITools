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
from logic.interface.config import get_color


def main():
    tool = MCPToolBase("BILIBILI", session_name="bilibili")

    parser = argparse.ArgumentParser(
        description="Bilibili video platform automation via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

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

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    B = get_color("BOLD")
    G = get_color("GREEN")
    R = get_color("RED")
    Y = get_color("YELLOW")
    BL = get_color("BLUE")
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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
