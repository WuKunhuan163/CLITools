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

    p_search = sub.add_parser("search", help="Search for videos")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    p_info = sub.add_parser("info", help="Get video details")
    p_info.add_argument("url", nargs="?", help="Video URL (or use current page)")

    p_screen = sub.add_parser("screenshot", help="Screenshot current YouTube page")
    p_screen.add_argument("--output", help="Output file path")

    p_trans = sub.add_parser("transcript", help="Get video transcript from browser")
    p_trans.add_argument("url", nargs="?", help="Video URL (or use current page)")

    p_subs = sub.add_parser("subtitles", help="Fetch subtitles via API (no browser)")
    p_subs.add_argument("video_id", help="YouTube video ID (e.g., dQw4w9WgXcQ)")
    p_subs.add_argument("--save", help="Save transcript to file")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.YOUTUBE.logic.chrome.api import (
        get_auth_state, get_page_info, search_videos, get_video_info,
        take_screenshot, get_transcript, fetch_subtitles_api, login,
        boot_session, get_session_status,
    )
    from tool.YOUTUBE.logic.chrome.api import _recover

    if args.command == "boot":
        r = boot_session()
        if r.get("ok"):
            action = r.get("action", "booted")
            print(f"  {BOLD}{GREEN}Session {action}{RESET}")
            print(f"  State: {r.get('state', '?')}")
            if r.get("tabId"):
                print(f"  Tab ID: {r['tabId']}")
        else:
            print(f"  {BOLD}{RED}Boot failed{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "session":
        r = get_session_status()
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
        r = _recover()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Recovered{RESET}: {r.get('action', '?')}")
            print(f"  Restored to: {r.get('restored_to', '?')}")
        else:
            print(f"  {BOLD}{RED}Recovery failed{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        if r.get("channelName"):
            print(f"  Channel: {r['channelName']}")
        print(f"  Page:    {r.get('title', '?')}")
        if r.get("hasSignInButton"):
            print(f"  {YELLOW}Sign-in button detected. Run 'YOUTUBE login' to authenticate.{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "login":
        r = login()
        if r.get("ok"):
            print(f"  {BOLD}{BLUE}Navigated{RESET} to sign-in page.")
            print(f"  {r.get('action', '')}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "search":
        r = search_videos(args.query, limit=args.limit)
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
        r = get_video_info(video_url=args.url)
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
                desc = r['description'][:200]
                print(f"  Desc:     {desc}")
            if r.get("videoId"):
                print(f"  ID:       {r['videoId']}")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "screenshot":
        r = take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Saved{RESET} screenshot to {r['path']} ({r['size']} bytes).")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "transcript":
        r = get_transcript(video_url=args.url)
        if r.get("ok"):
            print(f"  Transcript: {r.get('segments', 0)} segments")
            lines = r.get("lines", [])[:20]
            for line in lines:
                ts = line.get("timestamp", "")
                text = line.get("text", "")
                print(f"  {ts:>8} {text[:80]}")
            if r.get("segments", 0) > 20:
                print(f"  ... and {r['segments'] - 20} more segments")
        else:
            print(f"  {BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "subtitles":
        r = fetch_subtitles_api(args.video_id)
        if r.get("ok"):
            print(f"  Language: {r.get('languageName', r.get('language', '?'))}")
            print(f"  Segments: {r.get('segments', 0)}")
            langs = r.get("availableLanguages", [])
            if langs:
                lang_str = ", ".join(f"{l['code']}" for l in langs[:5])
                print(f"  Available: {lang_str}")
            lines = r.get("lines", [])[:15]
            print()
            for line in lines:
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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
