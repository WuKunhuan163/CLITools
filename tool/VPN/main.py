#!/usr/bin/env python3
import sys
import argparse
import os
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tool.VPN.logic.engine import VpnEngine

def main():
    parser = argparse.ArgumentParser(description="VPN Tool: Manages local proxies and VPN connections.")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # start
    start_parser = subparsers.add_parser("start", help="Start the local proxy")
    start_parser.add_argument("--port", type=int, help="Proxy port")

    # stop
    subparsers.add_parser("stop", help="Stop the local proxy")

    # status
    subparsers.add_parser("status", help="Check proxy status")

    args = parser.parse_args()

    engine = VpnEngine()

    if args.command == "start":
        if engine.start_proxy(port=args.port):
            print("Proxy started successfully.")
            urls = engine.get_proxy_urls()
            print(f"HTTP Proxy: {urls.get('http')}")
            print(f"HTTPS Proxy: {urls.get('https')}")
        else:
            print("Failed to start proxy.")
            sys.exit(1)
    elif args.command == "stop":
        if engine.stop_proxy():
            print("Proxy stopped.")
        else:
            print("Failed to stop proxy.")
            sys.exit(1)
    elif args.command == "status":
        if engine.is_running():
            print("Proxy is running.")
            urls = engine.get_proxy_urls()
            print(f"HTTP Proxy: {urls.get('http')}")
            print(f"HTTPS Proxy: {urls.get('https')}")
        else:
            print("Proxy is not running.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
