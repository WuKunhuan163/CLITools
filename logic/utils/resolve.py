"""Universal path resolver for AITerminalTools.

Provides a single, canonical way to find the project root and configure
sys.path so that cross-tool imports (e.g. ``from tool.GOOGLE.logic...``)
work reliably in every context: ToolBase lifecycle, subprocesses, test
runners, and standalone scripts.

Usage — inside any tool file already managed by ToolBase:
    from logic.utils.resolve import setup_paths
    ROOT = setup_paths()

Usage — standalone entry points that may NOT have logic/ in sys.path yet:
    import sys; from pathlib import Path
    _r = Path(__file__).resolve().parent
    while _r != _r.parent:
        if (_r / "bin" / "TOOL").exists(): break
        _r = _r.parent
    sys.path.insert(0, str(_r))
    from logic.utils.resolve import setup_paths
    ROOT = setup_paths()
"""
import sys
from pathlib import Path


_MARKER_BIN = "bin"
_MARKER_FILE = "TOOL"
_MARKER_JSON = "tool.json"


def find_project_root(start: "Path | str | None" = None) -> Path:
    """Walk up from *start* to find the project root.

    The root is identified by the presence of both ``bin/TOOL`` and
    ``tool.json``.  A secondary heuristic (``logic/`` + ``tool/``
    directories) is used as a fallback.

    Parameters
    ----------
    start : Path, str, or None
        Starting directory or file.  When *None*, the caller's file
        location is used.
    """
    if start is None:
        import inspect
        start = Path(inspect.stack()[1].filename).resolve()
    else:
        start = Path(start).resolve()

    if start.is_file():
        start = start.parent

    curr = start
    while curr != curr.parent:
        if (curr / _MARKER_BIN / _MARKER_FILE).exists() and (curr / _MARKER_JSON).exists():
            return curr
        curr = curr.parent

    curr = start
    while curr != curr.parent:
        if (curr / "logic").is_dir() and (curr / "tool").is_dir() and curr.parent.name != "tool":
            return curr
        curr = curr.parent

    return start


def setup_paths(caller_file: "str | Path | None" = None) -> Path:
    """Ensure ``sys.path`` is configured for correct module resolution.

    * Places the project root at ``sys.path[0]``.
    * Removes the caller's own directory from ``sys.path`` when it
      differs from the root (prevents a tool's directory from shadowing
      top-level packages).

    Returns the resolved project root ``Path``.
    """
    if caller_file is not None:
        start = Path(caller_file).resolve()
    else:
        import inspect
        start = Path(inspect.stack()[1].filename).resolve()

    root = find_project_root(start)
    root_str = str(root)

    while root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)

    caller_dir = str(start.parent if start.is_file() else start)
    if caller_dir != root_str and caller_dir in sys.path:
        sys.path.remove(caller_dir)

    return root


def get_tool_module_path(tool_dir: "str | Path", project_root: "str | Path | None" = None) -> str:
    """Return the dotted Python module path for a tool directory.

    Example: ``tool/GOOGLE.GDS`` → ``"tool.GOOGLE.GDS"``
    """
    tool_dir = Path(tool_dir).resolve()
    if project_root is None:
        project_root = find_project_root(tool_dir)
    project_root = Path(project_root).resolve()
    try:
        rel = tool_dir.relative_to(project_root)
        return ".".join(rel.parts)
    except ValueError:
        return ""
