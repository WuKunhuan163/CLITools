#!/usr/bin/env python3
"""
TAVILY (SEARCH) Tool Interface

Provides functions for other tools to perform web searches
programmatically via the Tavily API.
"""

def search(query, depth="basic", max_results=5, include_answer=False):
    """
    Run a Tavily web search and return raw results dict.
    
    Returns dict with keys: 'results' (list of {title, url, content, score}),
    optionally 'answer' if include_answer=True. Returns None on failure.
    """
    from tool.TAVILY.main import _load_config, _search
    from types import SimpleNamespace
    from logic.interface.tool import ToolBase

    tool = ToolBase("TAVILY")
    config = _load_config(tool)
    api_key = config.get("api_key")
    if not api_key:
        return None

    args = SimpleNamespace(
        depth=depth,
        max_results=min(max_results, 20),
        include_answer=include_answer,
        raw=True
    )

    import io, sys, json
    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        code = _search(tool, query, api_key, args)
    finally:
        sys.stdout = old_stdout

    if code != 0:
        return None

    try:
        return json.loads(buf.getvalue())
    except (json.JSONDecodeError, ValueError):
        return None
