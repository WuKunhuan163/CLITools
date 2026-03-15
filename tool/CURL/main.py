#!/usr/bin/env python3
"""CURL -- HTTP request tool.

A lightweight wrapper for making HTTP requests with structured output.
No external dependencies -- uses stdlib urllib only.

Usage:
    CURL get "https://example.com"
    CURL get "https://api.example.com/data" --headers '{"Authorization": "Bearer ..."}'
    CURL post "https://api.example.com" --data '{"key": "value"}'
    CURL head "https://example.com"
"""
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists():
        break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def _do_request(method, url, headers_str="", data_str="", timeout=30):
    """Perform an HTTP request and return structured result."""
    headers = {}
    if headers_str:
        try:
            headers = json.loads(headers_str)
        except Exception:
            return {"ok": False, "error": f"Invalid headers JSON: {headers_str}"}

    data = None
    if data_str:
        data = data_str.encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": resp.status,
                "headers": dict(resp.headers),
                "body": body,
            }
    except urllib.error.HTTPError as e:
        err_body = ""
        if e.fp:
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
        return {
            "ok": False,
            "status": e.code,
            "error": str(e.reason),
            "body": err_body,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_request(args):
    """Execute an HTTP request."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    get_color("DIM", "\033[2m")
    RESET = get_color("RESET")

    method = args.method
    url = args.url
    headers_str = getattr(args, "headers", "")
    data_str = getattr(args, "data", "")
    timeout = getattr(args, "timeout", 30)

    result = _do_request(method, url, headers_str, data_str, timeout)

    status = result.get("status", "")
    if result["ok"]:
        print(f"  {BOLD}{GREEN}{method.upper()} {status}{RESET} {url}")
    else:
        print(f"  {BOLD}{RED}{method.upper()} {status or 'ERR'}{RESET} {url}")
        if result.get("error"):
            print(f"  {result['error']}")

    body = result.get("body", "")
    if body:
        try:
            parsed = json.loads(body)
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except Exception:
            print(body[:5000])


def main():
    tool = ToolBase("CURL")

    parser = argparse.ArgumentParser(
        description="CURL -- HTTP request tool",
        add_help=False,
    )

    sub = parser.add_subparsers(dest="command")

    for method in ["get", "post", "put", "delete", "head", "patch"]:
        p = sub.add_parser(method, help=f"HTTP {method.upper()} request")
        p.add_argument("url", help="Request URL")
        p.add_argument("--headers", default="", help="JSON headers string")
        p.add_argument("--data", default="", help="Request body (JSON string)")
        p.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    if args.command in ("get", "post", "put", "delete", "head", "patch"):
        args.method = args.command
        cmd_request(args)
    else:
        print(f"  {BOLD}CURL{RESET} -- HTTP request tool.")
        print()
        print(f"  Commands:")
        print(f"    get URL         HTTP GET request")
        print(f"    post URL        HTTP POST (--data JSON)")
        print(f"    put URL         HTTP PUT (--data JSON)")
        print(f"    delete URL      HTTP DELETE")
        print(f"    head URL        HTTP HEAD (headers only)")
        print(f"    patch URL       HTTP PATCH (--data JSON)")
        print()
        print(f"  Options:")
        print(f"    --headers JSON  Custom headers")
        print(f"    --data JSON     Request body")
        print(f"    --timeout N     Timeout in seconds (default: 30)")


if __name__ == "__main__":
    main()
