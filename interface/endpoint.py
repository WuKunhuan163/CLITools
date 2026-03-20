"""Tool endpoint interface — structured JSON monitoring for stateful tools.

Provides the ``--endpoint`` symmetric command framework. Any tool that
maintains runtime state (sessions, tabs, queues, caches) can expose
monitoring endpoints by implementing ``get_endpoints()`` in its
``interface/main.py`` and overriding ``_handle_endpoint()`` in its
ToolBase subclass.

Usage (consumer)::

    from interface.endpoint import EndpointRegistry

    registry = EndpointRegistry()
    registry.register("chrome/status", handler_fn)
    registry.dispatch(["chrome", "status"])

Usage (tool implementor)::

    class MyTool(ToolBase):
        def _handle_endpoint(self, args):
            from my_tool.logic.endpoint import handle_endpoint
            handle_endpoint(args)
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.

import json
from typing import Any, Callable, Dict, List, Optional


class EndpointNotImplemented(NotImplementedError):
    """Raised when a tool does not implement --endpoint commands."""
    pass


class EndpointRegistry:
    """Dispatches ``--endpoint`` path segments to registered handlers.

    Handlers are plain callables that return a JSON-serializable dict
    (the registry prints it to stdout) or print output directly.
    """

    def __init__(self):
        self._static: Dict[tuple, Callable] = {}
        self._dynamic: List[tuple] = []

    def register(self, path: str, handler: Callable, *, doc: str = ""):
        """Register a static endpoint path.

        Args:
            path: Slash-separated path (e.g. ``"chrome/status"``).
            handler: Zero-arg callable returning a dict, or accepting
                     dynamic path segments as positional args.
            doc: One-line description for help output.
        """
        key = tuple(path.split("/"))
        self._static[key] = (handler, doc)

    def register_dynamic(self, prefix: str, handler: Callable, *, doc: str = ""):
        """Register a dynamic endpoint (prefix match, remaining segments passed as args).

        Args:
            prefix: Slash-separated prefix (e.g. ``"session"``).
            handler: Callable accepting remaining path segments as positional args.
            doc: One-line description for help output.
        """
        key = tuple(prefix.split("/"))
        self._dynamic.append((key, handler, doc))

    def dispatch(self, segments: List[str]) -> bool:
        """Dispatch a parsed path to its handler.

        Returns True if handled, False if no matching route.
        """
        key = tuple(segments)

        if key in self._static:
            handler, _ = self._static[key]
            result = handler()
            if isinstance(result, dict):
                _print_json(result)
            return True

        for prefix, handler, _ in self._dynamic:
            if key[:len(prefix)] == prefix and len(key) > len(prefix):
                remaining = list(key[len(prefix):])
                result = handler(*remaining)
                if isinstance(result, dict):
                    _print_json(result)
                return True

        return False

    def help_text(self, tool_name: str = "TOOL") -> str:
        """Generate help text listing all registered endpoints."""
        lines = [
            f"\n{tool_name} Endpoint Monitor (JSON output)\n",
            f"Usage: {tool_name} --endpoint <path>\n",
            "Endpoints:",
        ]
        for key, (_, doc) in sorted(self._static.items()):
            path = "/".join(key)
            lines.append(f"  {path:<35} {doc}")
        for prefix, _, doc in self._dynamic:
            path = "/".join(prefix) + "/<...>"
            lines.append(f"  {path:<35} {doc}")
        return "\n".join(lines)


def parse_endpoint_segments(args: list) -> List[str]:
    """Normalize endpoint args into flat path segments.

    Accepts slash-separated, space-separated, or ``--flag``-separated forms::

        ["chrome/status"]        → ["chrome", "status"]
        ["chrome", "status"]     → ["chrome", "status"]
        ["--chrome", "--status"] → ["chrome", "status"]
    """
    segments = []
    for arg in args:
        cleaned = arg.lstrip("-") if arg.startswith("--") else arg
        segments.extend(cleaned.split("/"))
    return [s for s in segments if s]


def endpoint_not_implemented(tool_name: str) -> None:
    """Default handler for tools that don't implement --endpoint."""
    raise EndpointNotImplemented(
        f"{tool_name} does not implement --endpoint commands. "
        f"Override _handle_endpoint() in the tool's ToolBase subclass."
    )


def _print_json(data: dict) -> None:
    """Print a dict as formatted JSON with safe serialization."""
    def _default(obj):
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"
    print(json.dumps(data, indent=2, ensure_ascii=False, default=_default))
