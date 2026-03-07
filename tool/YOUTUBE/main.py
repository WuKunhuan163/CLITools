#!/usr/bin/env python3
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


def main():
    tool = ToolBase("YOUTUBE")

    parser = argparse.ArgumentParser(
        description="YouTube automation via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("boot", help="Boot YouTube session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Recover from error state")
    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current YouTube page info")
    sub.add_parser("login", help="Navigate to YouTube sign-in")
    sub.add_parser("state", help="Get comprehensive MCP state (player + page)")

    # Navigation
    p_nav = sub.add_parser("navigate", help="Navigate to a section or URL")
    p_nav.add_argument("target", help="Section name or URL")

    p_open = sub.add_parser("open", help="Open a video by URL or ID")
    p_open.add_argument("video", help="Video URL or ID")

    # Search
    p_search = sub.add_parser("search", help="Search for videos")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    # Video info
    p_info = sub.add_parser("info", help="Get video details")
    p_info.add_argument("url", nargs="?", help="Video URL (or use current page)")

    # Screenshot
    p_screen = sub.add_parser("screenshot", help="Screenshot current YouTube page")
    p_screen.add_argument("--output", help="Output file path")

    # Transcript / subtitles
    p_trans = sub.add_parser("transcript", help="Get video transcript from browser")
    p_trans.add_argument("url", nargs="?", help="Video URL (or use current page)")

    p_subs = sub.add_parser("subtitles", help="Fetch subtitles via API (no browser)")
    p_subs.add_argument("video_id", help="YouTube video ID (e.g., dQw4w9WgXcQ)")
    p_subs.add_argument("--save", help="Save transcript to file")

    # Playback controls
    sub.add_parser("play", help="Play current video")
    sub.add_parser("pause", help="Pause current video")

    p_seek = sub.add_parser("seek", help="Seek to position (seconds, mm:ss, pct, relative)")
    p_seek.add_argument("target", help="Position: seconds, mm:ss, 50%%, or +10/-10")

    p_vol = sub.add_parser("volume", help="Set volume (0-100) or mute/unmute")
    p_vol.add_argument("level", nargs="?", type=int, help="Volume 0-100")
    p_vol.add_argument("--mute", action="store_true", help="Mute audio")
    p_vol.add_argument("--unmute", action="store_true", help="Unmute audio")

    p_speed = sub.add_parser("speed", help="Set playback speed (0.25-2.0)")
    p_speed.add_argument("rate", nargs="?", type=float, help="Speed rate")

    p_quality = sub.add_parser("quality", help="Set video quality (1080p, 720p, ...)")
    p_quality.add_argument("level", nargs="?", help="Quality level (or omit to list)")

    p_captions = sub.add_parser("captions", help="Toggle subtitles on/off")
    p_captions.add_argument("--on", action="store_true", help="Turn on")
    p_captions.add_argument("--off", action="store_true", help="Turn off")

    sub.add_parser("fullscreen", help="Toggle fullscreen mode")
    sub.add_parser("theater", help="Toggle theater mode")

    p_autoplay = sub.add_parser("autoplay", help="Toggle autoplay")
    p_autoplay.add_argument("--on", action="store_true")
    p_autoplay.add_argument("--off", action="store_true")

    sub.add_parser("pip", help="Toggle picture-in-picture")

    # Engagement
    sub.add_parser("like", help="Like the current video")
    sub.add_parser("dislike", help="Dislike the current video")
    sub.add_parser("subscribe", help="Subscribe/unsubscribe to channel")

    p_share = sub.add_parser("share", help="Open share dialog and get URL")

    p_save = sub.add_parser("save", help="Save video to playlist")
    p_save.add_argument("--playlist", default="Watch later", help="Playlist name")

    p_comment = sub.add_parser("comment", help="Add a comment")
    p_comment.add_argument("text", help="Comment text")

    # Recommendation / comments
    sub.add_parser("next", help="Navigate to next recommended video")

    p_recs = sub.add_parser("recommendations", help="List recommended videos")
    p_recs.add_argument("--limit", type=int, default=10)

    p_comments = sub.add_parser("comments", help="Extract top comments")
    p_comments.add_argument("--limit", type=int, default=10)

    sub.add_parser("expand-description", help="Expand video description")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.YOUTUBE.logic.chrome import api

    if args.command == "boot":
        r = api.boot_session()
        if r.get("ok"):
            action = r.get("action", "booted")
            print(f"  {BOLD}{GREEN}Session {action}{RESET}")
            print(f"  State: {r.get('state', '?')}")
        else:
            print(f"  {BOLD}{RED}Boot failed{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "session":
        r = api.get_session_status()
        state = r.get("state", "?")
        color = GREEN if state == "idle" else (YELLOW if state in ("navigating", "searching", "watching") else RED)
        print(f"  State:     {BOLD}{color}{state}{RESET}")
        print(f"  Transcript: {r.get('transcript_state', '?')}")
        print(f"  Session:   {'alive' if r.get('session_alive') else 'none'}")
        print(f"  CDP:       {'available' if r.get('cdp_available') else 'unavailable'}")
        if r.get("last_url"):
            print(f"  Last URL:  {r['last_url'][:80]}")
        if r.get("last_video_id"):
            print(f"  Video ID:  {r['last_video_id']}")
        if r.get("error"):
            print(f"  Error:     {RED}{r['error']}{RESET}")
        print(f"  Recoveries: {r.get('recovery_count', 0)}")

    elif args.command == "recover":
        r = api._recover()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Recovered{RESET}: {r.get('action', '?')}")
            print(f"  Restored to: {r.get('restored_to', '?')}")
        else:
            print(f"  {BOLD}{RED}Recovery failed{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "status":
        r = api.get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        if r.get("channelName"):
            print(f"  Channel: {r['channelName']}")
        print(f"  Page:    {r.get('title', '?')}")
        if r.get("hasSignInButton"):
            print(f"  {YELLOW}Sign-in button detected. Run 'YOUTUBE login' to authenticate.{RESET}")

    elif args.command == "page":
        r = api.get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "login":
        r = api.login()
        if r.get("ok"):
            print(f"  {BOLD}{BLUE}Navigated{RESET} to sign-in page.")
            print(f"  {r.get('action', '')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "state":
        r = api.get_mcp_state()
        if r.get("ok"):
            print(f"  {BOLD}URL:{RESET}     {r.get('url', '?')[:80]}")
            print(f"  {BOLD}Section:{RESET} {r.get('section', '?')}")
            if r.get("video_title"):
                print(f"  {BOLD}Video:{RESET}   {r['video_title'][:70]}")
            if r.get("channel"):
                print(f"  {BOLD}Channel:{RESET} {r['channel']}")
            p = r.get("player", {})
            if p:
                status = "paused" if p.get("paused") else "playing"
                print(f"  {BOLD}Player:{RESET}  {status} | {p.get('currentTime', 0)}s / {p.get('duration', 0)}s ({p.get('progress_pct', 0)}%)")
                print(f"  {BOLD}Volume:{RESET}  {p.get('volume', '?')}% {'(muted)' if p.get('muted') else ''}")
                print(f"  {BOLD}Speed:{RESET}   {p.get('playbackRate', 1)}x")
            print(f"  {BOLD}Captions:{RESET} {r.get('captions', 'n/a')}")
            print(f"  {BOLD}Auth:{RESET}     {'Yes' if r.get('authenticated') else 'No'}")
            print(f"  {BOLD}Recs:{RESET}     {r.get('recommendation_count', 0)} videos")
            ms = r.get("machine_state", {})
            print(f"  {BOLD}Machine:{RESET} {ms.get('state', '?')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "navigate":
        r = api.navigate(args.target)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Navigated{RESET} to {r.get('target', '?')}")
            print(f"  URL: {r.get('url', '?')[:80]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "open":
        r = api.open_video(args.video)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Opened{RESET} video")
            print(f"  URL: {r.get('url', '?')[:80]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "search":
        r = api.search_videos(args.query, limit=args.limit)
        if r.get("ok"):
            results = r.get("results", [])
            print(f"  Search '{r.get('query','')}': {r.get('count', 0)} results")
            for i, v in enumerate(results):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:70]}")
                print(f"       {v.get('channel', '?')} | {v.get('views', '')}")
                if v.get("videoId"):
                    print(f"       {v['url']}")
            if not results:
                print(f"  {YELLOW}No results found.{RESET}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "info":
        r = api.get_video_info(video_url=args.url)
        if r.get("ok"):
            print(f"  Title:    {r.get('title', '?')}")
            print(f"  Channel:  {r.get('channel', '?')}")
            print(f"  Views:    {r.get('views', '?')}")
            if r.get("likes"):
                print(f"  Likes:    {r['likes']}")
            if r.get("date"):
                print(f"  Date:     {r['date']}")
            if r.get("subscribers"):
                print(f"  Subs:     {r['subscribers']}")
            if r.get("description"):
                print(f"  Desc:     {r['description'][:200]}")
            if r.get("videoId"):
                print(f"  ID:       {r['videoId']}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "screenshot":
        r = api.take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Saved{RESET} screenshot to {r['path']} ({r['size']} bytes).")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "transcript":
        r = api.get_transcript(video_url=args.url)
        if r.get("ok"):
            print(f"  Transcript: {r.get('segments', 0)} segments")
            for line in r.get("lines", [])[:20]:
                print(f"  {line.get('timestamp', ''):>8} {line.get('text', '')[:80]}")
            if r.get("segments", 0) > 20:
                print(f"  ... and {r['segments'] - 20} more segments")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "subtitles":
        r = api.fetch_subtitles_api(args.video_id)
        if r.get("ok"):
            print(f"  Language: {r.get('languageName', r.get('language', '?'))}")
            print(f"  Segments: {r.get('segments', 0)}")
            langs = r.get("availableLanguages", [])
            if langs:
                print(f"  Available: {', '.join(l['code'] for l in langs[:5])}")
            for line in r.get("lines", [])[:15]:
                print(f"  {line.get('timestamp', ''):>8} {line.get('text', '')[:80]}")
            if r.get("segments", 0) > 15:
                print(f"  ... and {r['segments'] - 15} more segments")
            if args.save:
                Path(args.save).parent.mkdir(parents=True, exist_ok=True)
                with open(args.save, "w") as f:
                    f.write(r.get("fullText", ""))
                print(f"\n  {BOLD}{GREEN}Saved{RESET} transcript to {args.save}.")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "play":
        r = api.play()
        print(f"  {BOLD}{GREEN}Playing{RESET}" if r.get("ok") else f"  {RED}Error: {r.get('error')}{RESET}")

    elif args.command == "pause":
        r = api.pause()
        print(f"  {BOLD}{YELLOW}Paused{RESET}" if r.get("ok") else f"  {RED}Error: {r.get('error')}{RESET}")

    elif args.command == "seek":
        r = api.seek(args.target)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Seeked{RESET} to {r.get('time', '?')}s")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "volume":
        mute_val = True if args.mute else (False if args.unmute else None)
        r = api.volume(level=args.level, mute=mute_val)
        if r.get("ok"):
            print(f"  Volume: {r.get('volume', '?')}% {'(muted)' if r.get('muted') else ''}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "speed":
        r = api.speed(rate=args.rate)
        if r.get("ok"):
            print(f"  Speed: {r.get('speed', '?')}x")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "quality":
        r = api.quality(level=args.level)
        if r.get("ok"):
            print(f"  Available: {', '.join(r.get('available', []))}")
            if args.level:
                print(f"  {BOLD}{GREEN}Set to{RESET}: {args.level}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "captions":
        toggle = True if args.on else (False if args.off else None)
        r = api.captions(toggle=toggle)
        if r.get("ok"):
            print(f"  Captions: {r.get('captions', '?')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "fullscreen":
        r = api.fullscreen()
        print(f"  {GREEN}Toggled fullscreen{RESET}" if r.get("ok") else f"  {RED}Error: {r.get('error')}{RESET}")

    elif args.command == "theater":
        r = api.theater()
        print(f"  {GREEN}Toggled theater{RESET}" if r.get("ok") else f"  {RED}Error: {r.get('error')}{RESET}")

    elif args.command == "autoplay":
        toggle = True if args.on else (False if args.off else None)
        r = api.autoplay(toggle=toggle)
        if r.get("ok"):
            print(f"  Autoplay: {'on' if r.get('autoplay') else 'off'}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "pip":
        r = api.pip()
        if r.get("ok"):
            print(f"  PiP: {'on' if r.get('pip') else 'off'}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "like":
        r = api.like()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Liked{RESET} — {r.get('state', '')[:50]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "dislike":
        r = api.dislike()
        print(f"  {GREEN}Disliked{RESET}" if r.get("ok") else f"  {RED}Error: {r.get('error')}{RESET}")

    elif args.command == "subscribe":
        r = api.subscribe()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Toggled{RESET}: {r.get('button_text', '?')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "share":
        r = api.share()
        if r.get("ok"):
            print(f"  Share URL: {r.get('share_url', '(none)')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "save":
        r = api.save(playlist=args.playlist)
        if r.get("ok"):
            status = GREEN + "Saved" if r.get("saved") else YELLOW + "Not found"
            print(f"  {BOLD}{status}{RESET} to '{r.get('playlist', '?')}'")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "comment":
        r = api.comment(args.text)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Commented{RESET}: {r.get('text', '')[:60]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "next":
        r = api.next_video()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Next video{RESET}: {r.get('url', '?')[:80]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "recommendations":
        r = api.get_recommendations(limit=args.limit)
        if r.get("ok"):
            for i, v in enumerate(r.get("results", [])):
                dur = f" [{v['duration']}]" if v.get("duration") else ""
                print(f"  [{i+1:2d}]{dur} {v.get('title', '?')[:65]}")
                if v.get("channel"):
                    print(f"       {v['channel']} | {v.get('views', '')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "comments":
        r = api.get_comments(limit=args.limit)
        if r.get("ok"):
            for c in r.get("comments", []):
                print(f"  {BOLD}{c.get('author', '?')}{RESET} ({c.get('time', '?')})")
                print(f"    {c.get('text', '')[:120]}")
                likes = c.get("likes", "0")
                replies = c.get("reply_count", "")
                if likes or replies:
                    print(f"    👍 {likes}  {'💬 ' + replies if replies else ''}")
                print()
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "expand-description":
        r = api.expand_description()
        if r.get("ok"):
            print(f"  {r.get('description', '')[:500]}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
