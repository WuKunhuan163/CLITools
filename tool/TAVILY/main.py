#!/usr/bin/env python3
import sys
import os
import json
import argparse
from pathlib import Path

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
root_str = str(project_root)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

from logic.tool.blueprint.base import ToolBase
from logic.interface.config import get_color


def main():
    tool = ToolBase("TAVILY")

    first_arg = sys.argv[1] if len(sys.argv) > 1 else None

    if first_arg == "config":
        tool.check_cpu_load_and_warn()
        _handle_config_cli(tool, sys.argv[2:])
        return

    if first_arg == "--setup-tutorial":
        tool.check_cpu_load_and_warn()
        import importlib.util
        cmd_path = Path(__file__).resolve().parent / "logic" / "command" / "tutorial_cmd.py"
        spec = importlib.util.spec_from_file_location("tavily_tutorial_cmd", str(cmd_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        code = mod.execute(tool)
        sys.exit(code or 0)

    parser = argparse.ArgumentParser(
        description="AI-optimized web search via Tavily API", add_help=False
    )
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--depth", choices=["basic", "advanced"], default="basic",
                        help="Search depth (basic=1 credit, advanced=2 credits)")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum results (1-20)")
    parser.add_argument("--include-answer", action="store_true", help="Include AI-generated answer")
    parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    parser.add_argument("--api-key", dest="inline_api_key", help="Tavily API key (or set TAVILY_API_KEY env var)")

    if tool.handle_command_line(parser):
        return

    args, unknown = parser.parse_known_args()

    if not args.query:
        parser.print_help()
        return

    query = " ".join(args.query)
    api_key = args.inline_api_key or os.environ.get("TAVILY_API_KEY")

    if not api_key:
        config = _load_config(tool)
        api_key = config.get("api_key")

    if not api_key:
        BOLD = get_color("BOLD", "\033[1m")
        RED = get_color("RED", "\033[31m")
        RESET = get_color("RESET", "\033[0m")
        print(f"{BOLD}{RED}Missing API key{RESET}. Set via:")
        print(f"  TAVILY config --api-key <key>")
        print(f"  or: export TAVILY_API_KEY=<key>")
        sys.exit(1)

    code = _search(tool, query, api_key, args)
    if code:
        sys.exit(code)


def _search(tool, query, api_key, args):
    """Execute Tavily search and display results."""
    from logic.interface.turing import ProgressTuringMachine
    from logic.interface.turing import TuringStage

    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    BLUE = get_color("BLUE", "\033[34m")
    RESET = get_color("RESET", "\033[0m")

    search_result = {}

    def search_action(stage=None):
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                search_depth=args.depth,
                max_results=min(args.max_results, 20),
                include_answer=args.include_answer
            )
            search_result.update(response)
            return True
        except Exception as e:
            if stage:
                stage.error_brief = str(e)
            return False

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="TAVILY",
                                log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "search", search_action,
        active_status="Searching", active_name=f"'{query}'",
        fail_status="Failed to search",
        success_status="Found", success_name="results",
        bold_part=f"Searching '{query}'"
    ))

    if not pm.run(ephemeral=True):
        return 1

    if args.raw:
        print(json.dumps(search_result, indent=2, ensure_ascii=False))
        return 0

    if args.include_answer and "answer" in search_result:
        print(f"\n{BOLD}Answer:{RESET} {search_result['answer']}\n")

    results = search_result.get("results", [])
    if not results:
        print("No results found.")
        return 0

    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")
        score = r.get("score", 0)

        print(f"{BOLD}{i}. {title}{RESET}")
        print(f"   {BLUE}{url}{RESET}")
        if content:
            lines = content.strip().split("\n")
            preview = lines[0][:200]
            if len(lines[0]) > 200:
                preview += "..."
            print(f"   {preview}")
        if score:
            print(f"   Score: {score:.3f}")
        print()

    return 0


def _handle_config_cli(tool, cli_args):
    """Handle TAVILY config subcommand from raw CLI args."""
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")

    config_parser = argparse.ArgumentParser(prog="TAVILY config", add_help=False)
    config_parser.add_argument("--api-key", help="Set Tavily API key")
    args, _ = config_parser.parse_known_args(cli_args)

    config = _load_config(tool)

    if args.api_key:
        config["api_key"] = args.api_key
        _save_config(tool, config)
        masked = args.api_key[:8] + "..." + args.api_key[-4:] if len(args.api_key) > 12 else "***"
        print(f"{BOLD}{GREEN}Saved API key{RESET} ({masked})")
        return

    if config.get("api_key"):
        key = config["api_key"]
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        print(f"API key: {masked}")
    else:
        print("No API key configured.")
        print(f"  TAVILY config --api-key <key>")


def _save_config(tool, config):
    """Save TAVILY config to data/config.json."""
    config_path = tool.get_data_dir() / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)


def _load_config(tool):
    """Load TAVILY config from data/config.json."""
    config_path = tool.get_data_dir() / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


if __name__ == "__main__":
    main()
