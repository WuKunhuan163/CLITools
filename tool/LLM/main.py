#!/usr/bin/env python3
"""LLM -- Unified LLM provider management tool.

Manages API keys, provider selection, rate limiting, and provides
a CLI for testing LLM connections. Other tools import from
tool.LLM.interface.main to access LLM capabilities.

Usage:
    LLM                   Show help
    LLM setup             Configure API key for a provider
    LLM status            Show all providers and their status
    LLM providers         List available providers with details
    LLM test              Send a test message to verify connectivity
    LLM send "message"    Send a one-shot message to the default provider
"""
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def cmd_setup(args):
    """Configure API key for a provider."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    provider_name = getattr(args, "provider", "nvidia-glm-4-7b")

    if provider_name in ("nvidia-glm-4-7b", "nvidia_glm47"):
        print(f"  {BOLD}LLM Setup{RESET} -- NVIDIA GLM-4.7")
        print()
        print(f"  Get your free API key from: https://build.nvidia.com/z-ai/glm4_7")
        print()

        from tool.LLM.logic.models.glm_4_7.providers.nvidia.interface import get_api_key, save_api_key

        current = get_api_key()
        if current:
            masked = current[:8] + "..." + current[-4:] if len(current) > 12 else "***"
            print(f"  Current key: {masked}")
            print()

        api_key = input("  Enter NVIDIA API key (or Enter to keep current): ").strip()
        if api_key:
            save_api_key(api_key)
            print(f"  {BOLD}{GREEN}Saved{RESET} API key.")
        elif not current:
            print(f"  No key configured. Set NVIDIA_API_KEY env var or run LLM setup again.")
            return
    else:
        print(f"  Unknown provider: {provider_name}")
        return

    from tool.LLM.logic.registry import get_provider
    try:
        p = get_provider(provider_name)
        info = p.get_info()
        avail = f"{GREEN}yes{RESET}" if info["available"] else "no"
        print(f"  {BOLD}Provider{RESET}: {info.get('model', provider_name)}")
        print(f"  {BOLD}Available{RESET}: {avail}")
    except Exception as e:
        print(f"  Check failed: {e}")


def cmd_status(args):
    """Show all providers and their status."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.LLM.logic.registry import list_providers

    providers = list_providers()
    print(f"  {BOLD}LLM Providers{RESET}:")
    for p in providers:
        name = p.get("name", "?")
        avail = p.get("available", False)
        status = f"{GREEN}available{RESET}" if avail else f"{RED}not configured{RESET}"
        model = p.get("model", "")
        rpm = p.get("rpm_limit", "?")
        ctx = p.get("max_context", "?")
        if isinstance(ctx, int):
            ctx = f"{ctx:,}"
        print(f"    {BOLD}{name}{RESET}: {status}")
        if model:
            print(f"      Model: {model}  |  RPM: {rpm}  |  Context: {ctx} tokens")
        cm = p.get("cost_model", {})
        if cm.get("free_tier"):
            print(f"      Pricing: free tier")
        elif cm.get("prompt_price_per_m", 0) > 0:
            print(f"      Pricing: ${cm['prompt_price_per_m']}/M prompt + "
                  f"${cm['completion_price_per_m']}/M completion")


def cmd_providers(args):
    """List available providers with details."""
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    from tool.LLM.logic.registry import list_providers

    providers = list_providers()
    for p in providers:
        print(f"  {BOLD}{p.get('name', '?')}{RESET}")
        for k, v in p.items():
            if k != "name":
                print(f"    {k}: {v}")
        print()


def cmd_test(args):
    """Send a test message to verify connectivity."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    provider_name = getattr(args, "provider", "nvidia-glm-4-7b")
    print(f"  {BOLD}{BLUE}Testing{RESET} provider '{provider_name}'...")

    from tool.LLM.logic.registry import get_provider

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        print(f"  {BOLD}{RED}Failed{RESET} to get provider: {e}")
        return

    if not provider.is_available():
        print(f"  {BOLD}{RED}Not configured{RESET}. Run LLM setup first.")
        return

    messages = [
        {"role": "system", "content": "You are a concise assistant. Reply in one sentence."},
        {"role": "user", "content": "Say hello and confirm you are GLM-4.7."},
    ]

    result = provider.send(messages, temperature=0.5, max_tokens=256)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Success{RESET}.")
        print(f"  Response: {result['text'][:200]}")
        usage = result.get("usage", {})
        if usage:
            print(f"  Tokens: prompt={usage.get('prompt_tokens', '?')}, "
                  f"completion={usage.get('completion_tokens', '?')}, "
                  f"total={usage.get('total_tokens', '?')}")
    else:
        print(f"  {BOLD}{RED}Failed{RESET}: {result.get('error', 'Unknown error')}")


def cmd_send(args):
    """Send a one-shot message to the default provider."""
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    RED = get_color("RED")
    RESET = get_color("RESET")

    message = args.message
    provider_name = getattr(args, "provider", "nvidia-glm-4-7b")

    from tool.LLM.logic.registry import get_provider

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        print(f"  {BOLD}{RED}Failed{RESET}: {e}")
        return

    if not provider.is_available():
        print(f"  {BOLD}{RED}Not configured{RESET}. Run LLM setup first.")
        return

    system = getattr(args, "system", None)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    print(f"  {BOLD}{BLUE}Sending{RESET}...", flush=True)
    result = provider.send(messages, temperature=0.7, max_tokens=4096)

    if result.get("ok"):
        print(result["text"])
    else:
        print(f"  {BOLD}{RED}Failed{RESET}: {result.get('error', 'Unknown error')}")


def cmd_usage(args):
    """Show API usage statistics."""
    BOLD = get_color("BOLD")
    DIM = get_color("DIM", "\033[2m")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    CYAN = get_color("CYAN", "\033[36m")
    RESET = get_color("RESET")

    from tool.LLM.logic.usage import get_summary, get_daily_summary

    period = getattr(args, "period", "all")
    provider = getattr(args, "filter_provider", "")

    if period == "today":
        summary = get_daily_summary(provider=provider)
        label = "Today"
    else:
        summary = get_summary(provider=provider)
        label = "All time"

    total = summary["total_calls"]
    if total == 0:
        print(f"  {DIM}No API usage recorded.{RESET}")
        return

    ok = summary["successful"]
    fail = summary["failed"]
    error_rate = (fail / total * 100) if total else 0

    print(f"  {BOLD}LLM Usage{RESET} ({label})")
    print(f"    Calls: {ok} {GREEN}ok{RESET} / {fail} {RED}failed{RESET} / {total} total")
    print(f"    Tokens: {summary['total_tokens']:,} total "
          f"({summary['prompt_tokens']:,} prompt + {summary['completion_tokens']:,} completion)")
    print(f"    Avg latency: {summary['avg_latency_s']}s")
    if error_rate > 5:
        print(f"    Error rate: {RED}{error_rate:.1f}%{RESET}")
    else:
        print(f"    Error rate: {error_rate:.1f}%")

    by_prov = summary.get("providers", {})
    if by_prov:
        print(f"\n  {BOLD}By Provider{RESET}")
        for pname, stats in by_prov.items():
            print(f"    {CYAN}{pname}{RESET}: {stats['calls']} calls, "
                  f"{stats['tokens']:,} tokens, {stats['errors']} errors")


def cmd_limits(args):
    """View or set per-provider record limits."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    get_color("DIM", "\033[2m")
    RESET = get_color("RESET")

    from tool.LLM.logic.usage import (
        get_provider_limits, set_provider_limits, get_all_provider_limits,
        DEFAULT_RECORD_LIMIT, DEFAULT_CLEANUP_BATCH,
    )

    provider = getattr(args, "provider_name", "")
    limit_val = getattr(args, "limit_val", None)
    batch_val = getattr(args, "batch_val", None)

    if not provider:
        all_limits = get_all_provider_limits()
        from tool.LLM.logic.registry import list_providers
        for p in list_providers():
            name = p["name"]
            lim = all_limits.get(name, {
                "record_limit": DEFAULT_RECORD_LIMIT,
                "cleanup_batch": DEFAULT_CLEANUP_BATCH,
            })
            print(f"  {BOLD}{name}{RESET}: limit={lim['record_limit']}, batch={lim['cleanup_batch']}")
        return

    if limit_val is None:
        lim = get_provider_limits(provider)
        print(f"  {BOLD}{provider}{RESET}: limit={lim['record_limit']}, batch={lim['cleanup_batch']}")
        return

    batch = batch_val if batch_val is not None else (limit_val // 2)
    err = set_provider_limits(provider, limit_val, batch)
    if err:
        print(f"  {BOLD}{RED}Failed{RESET}: {err}")
    else:
        print(f"  {BOLD}{GREEN}Saved{RESET} limits for {provider}: limit={limit_val}, batch={batch}.")


def cmd_agent(args):
    """Start the live LLM Agent GUI with real-time conversation."""
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    explicit = getattr(args, "agent_provider", "")
    if explicit:
        provider_name = explicit
    else:
        from tool.LLM.logic.registry import list_providers
        available = [p["name"] for p in list_providers() if p.get("available")]
        provider_name = available[0] if available else getattr(args, "provider", "zhipu-glm-4.7")

    port = getattr(args, "port", 0) or 0
    no_open = getattr(args, "no_open", False)
    enable_tools = getattr(args, "tools", False)

    from tool.LLM.logic.gui.agent_server import start_agent_server
    from tool.LLM.logic.config import get_config_value

    lang = get_config_value("lang", "en")

    print(f"  {BOLD}{BLUE}Starting{RESET} LLM Agent (provider: {provider_name})...")

    agent = start_agent_server(
        provider_name=provider_name,
        port=port,
        open_browser=not no_open,
        enable_tools=enable_tools,
        lang=lang,
    )

    print(f"  {BOLD}{GREEN}Live{RESET} at {agent.url}")
    print(f"  Press Ctrl+C to stop.")

    try:
        agent._server.wait()
    except KeyboardInterrupt:
        agent.stop()
        print(f"\n  {BOLD}Stopped.{RESET}")


def cmd_keys(args):
    """Manage API keys for a provider."""
    from tool.LLM.logic.config import get_api_keys, add_api_key, remove_api_key

    provider = args.key_provider
    BOLD = get_color("BOLD")
    DIM = get_color("DIM")
    RESET = get_color("RESET")

    if args.keys_add:
        kid = add_api_key(provider, args.keys_add, args.label)
        print(f"  {BOLD}Added.{RESET} {DIM}ID: {kid}{RESET}")
        return

    if args.keys_remove:
        ok = remove_api_key(provider, args.keys_remove)
        if ok:
            print(f"  {BOLD}Removed.{RESET} {DIM}{args.keys_remove}{RESET}")
        else:
            print(f"  Key {args.keys_remove} not found.")
        return

    if args.keys_list:
        keys = get_api_keys(provider)
        if not keys:
            print(f"  No keys for {provider}.")
            return
        for i, k in enumerate(keys):
            masked = k["key"][:8] + "..." + k["key"][-4:] if len(k["key"]) > 12 else k["key"]
            label = k.get("label", "")
            print(f"  {i+1}. [{k['id']}] {masked}  {DIM}({label}){RESET}")
        return

    try:
        from tool.LLM.logic.gui.key_manager import KeyManagerWindow
        import tkinter as tk
        root = tk.Tk()
        KeyManagerWindow(root, provider=provider)
        root.mainloop()
    except ImportError:
        print("  Tkinter not available. Use --list, --add, --remove for CLI access.")


def cmd_dashboard(args):
    """Generate and open the LLM usage dashboard.

    With --serve: starts a persistent local server that auto-regenerates
    the dashboard on each page load. Runs until Ctrl+C or kill.
    Without --serve: generates a static HTML file and opens it.
    """
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    from tool.LLM.logic.dashboard.generate import generate

    output = getattr(args, "output", "")
    path = generate(output_path=output)
    print(f"  {BOLD}{GREEN}Generated{RESET} {path}.")

    if getattr(args, "serve", False):
        from logic.serve.html_server import LocalHTMLServer

        port = getattr(args, "port", 0) or 0
        server = LocalHTMLServer(
            html_path=path,
            port=port,
            title="LLM Dashboard",
            on_generate=lambda p: generate(output_path=p),
        )
        server.start()
        print(f"  {BOLD}{BLUE}Serving{RESET} at {server.url}")

        if not getattr(args, "no_open", False):
            server.open_browser()

        try:
            server.wait()
        except KeyboardInterrupt:
            server.stop()
            print(f"  {BOLD}Stopped.{RESET}")
    elif not getattr(args, "no_open", False):
        import webbrowser
        webbrowser.open(f"file://{path}")
        print(f"  Opened in browser.")


def main():
    tool = ToolBase("LLM")

    parser = argparse.ArgumentParser(
        description="LLM -- Unified LLM provider management",
        add_help=False
    )
    parser.add_argument("--provider", default="nvidia-glm-4-7b",
                        help="Provider name (default: nvidia-glm-4-7b)")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("setup", help="Configure API key for a provider")
    sub.add_parser("status", help="Show all providers and their status")
    sub.add_parser("providers", help="List available providers with details")
    sub.add_parser("test", help="Send a test message to verify connectivity")

    p_send = sub.add_parser("send", help="Send a one-shot message")
    p_send.add_argument("message", help="Message text")
    p_send.add_argument("--system", help="System prompt")

    p_usage = sub.add_parser("usage", help="Show API usage statistics")
    p_usage.add_argument("--period", default="all", choices=["all", "today"],
                         help="Time period (default: all)")
    p_usage.add_argument("--filter-provider", default="",
                         help="Filter by provider name")

    p_limits = sub.add_parser("limits", help="View or set per-provider record limits")
    p_limits.add_argument("provider_name", nargs="?", default="", help="Provider name")
    p_limits.add_argument("limit_val", nargs="?", type=int, help="Max records per provider")
    p_limits.add_argument("batch_val", nargs="?", type=int, help="Records to delete per cleanup")

    p_agent = sub.add_parser("agent", help="Start live LLM Agent GUI")
    p_agent.add_argument("--agent-provider", dest="agent_provider", default="",
                         help="Provider for agent (auto-selects first available)")
    p_agent.add_argument("--port", type=int, default=0, help="Port (0=auto)")
    p_agent.add_argument("--no-open", action="store_true", help="Do not open browser")
    p_agent.add_argument("--tools", action="store_true", help="Enable tool calling")

    p_keys = sub.add_parser("keys", help="Manage API keys (GUI or CLI)")
    p_keys.add_argument("key_provider", nargs="?", default="zhipu",
                        help="Provider name (default: zhipu)")
    p_keys.add_argument("--list", dest="keys_list", action="store_true",
                        help="List keys in CLI")
    p_keys.add_argument("--add", dest="keys_add", default="",
                        help="Add a new key")
    p_keys.add_argument("--label", default="", help="Label for --add")
    p_keys.add_argument("--remove", dest="keys_remove", default="",
                        help="Remove a key by ID")

    p_dash = sub.add_parser("dashboard", help="Generate and open HTML usage dashboard")
    p_dash.add_argument("--output", default="", help="Custom output path for the HTML file")
    p_dash.add_argument("--no-open", action="store_true", help="Do not open in browser")
    p_dash.add_argument("--serve", action="store_true", help="Start persistent local server")
    p_dash.add_argument("--port", type=int, default=0, help="Port for --serve (0=auto)")

    if tool.handle_command_line(parser): return

    args = parser.parse_args()

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "providers":
        cmd_providers(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "send":
        cmd_send(args)
    elif args.command == "usage":
        cmd_usage(args)
    elif args.command == "limits":
        cmd_limits(args)
    elif args.command == "agent":
        cmd_agent(args)
    elif args.command == "keys":
        cmd_keys(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)
    else:
        print(f"  {BOLD}LLM{RESET} -- Unified LLM provider management.")
        print()
        print(f"  Commands:")
        print(f"    setup       Configure API key for a provider")
        print(f"    status      Show all providers and their status")
        print(f"    providers   List available providers with details")
        print(f"    test        Send a test message to verify connectivity")
        print(f"    send \"msg\"  Send a one-shot message")
        print(f"    agent       Start live LLM Agent GUI (--tools for tool calling)")
        print(f"    usage       Show API usage statistics (--period today|all)")
        print(f"    keys        Manage API keys (GUI or --list/--add/--remove)")
        print(f"    limits      View/set per-provider record limits")
        print(f"    dashboard   Open HTML usage dashboard (--serve for persistent server)")
        print()
        print(f"  Options:")
        print(f"    --provider P   Provider name (default: nvidia-glm-4-7b)")
        print()
        print(f"  First-time setup:")
        print(f"    1. LLM setup   (enter NVIDIA API key)")
        print(f"    2. LLM test    (verify connectivity)")


if __name__ == "__main__":
    main()
