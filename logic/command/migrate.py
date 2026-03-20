"""Unified migration framework.

Provides the --migrate symmetric command for importing tools, infrastructure,
hooks, MCP servers, skills, and information from external sources.

Migration levels:
  --tool            Import a complete, ready-to-use tool
  --infrastructure  Import code resources used by a tool (e.g. standalone builds)
  --hooks           Import lifecycle hooks
  --mcp             Import MCP server definitions
  --skills          Import skill definitions
  --info            Import metadata/documentation only
  --draft-tool      Import a tool scaffold that needs post-processing
  --draft-infrastructure  Import infrastructure that needs post-processing
  --draft-hooks     Import hooks that need post-processing
  --draft-mcp       Import MCP definitions that need post-processing

Each domain lives under migrate/<domain>/ with:
  info.json   — domain metadata + supported migration levels
  __init__.py — domain module
  *.py        — level-specific migration logic
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

MIGRATE_DIR = _PROJECT_ROOT / "migrate"

MIGRATION_LEVELS = [
    "tool", "infrastructure", "hooks", "mcp", "skills", "info",
    "draft-tool", "draft-infrastructure", "draft-hooks", "draft-mcp",
]


def list_domains() -> List[Dict[str, Any]]:
    """List all registered migration domains with their info."""
    domains = []
    if not MIGRATE_DIR.exists():
        return domains

    for d in sorted(MIGRATE_DIR.iterdir()):
        info_file = d / "info.json"
        if d.is_dir() and info_file.exists():
            try:
                info = json.loads(info_file.read_text())
                info["path"] = str(d)
                info["domain"] = d.name
                domains.append(info)
            except Exception:
                domains.append({"domain": d.name, "path": str(d), "error": "invalid info.json"})
    return domains


def get_domain_info(domain: str) -> Optional[Dict[str, Any]]:
    """Get info for a specific domain."""
    info_file = MIGRATE_DIR / domain / "info.json"
    if not info_file.exists():
        return None
    try:
        info = json.loads(info_file.read_text())
        info["domain"] = domain
        info["path"] = str(MIGRATE_DIR / domain)
        return info
    except Exception:
        return {"domain": domain, "error": "invalid info.json"}


def get_domain_module(domain: str, level: str):
    """Import and return the migration module for a domain+level.

    The module should expose an execute(args) function.
    """
    import importlib.util
    domain_dir = MIGRATE_DIR / domain

    level_file = domain_dir / f"{level.replace('-', '_')}.py"
    if not level_file.exists():
        level_file = domain_dir / f"migrate_{level.replace('-', '_')}.py"
    if not level_file.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        f"migrate_{domain}_{level}", str(level_file)
    )
    if spec is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_pending(domain: str) -> Dict[str, Any]:
    """Check what's pending migration in a domain.

    The domain module should expose a check_pending() function.
    """
    domain_dir = MIGRATE_DIR / domain
    check_file = domain_dir / "check.py"
    if not check_file.exists():
        return {"pending": [], "up_to_date": True}

    import importlib.util
    spec = importlib.util.spec_from_file_location(f"migrate_{domain}_check", str(check_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if hasattr(mod, "check_pending"):
        return mod.check_pending()
    return {"pending": [], "up_to_date": True}


def scan_domain(domain: str) -> Dict[str, Any]:
    """Scan a domain to discover available items and their migration status.

    The domain module should expose a scan_available() function that returns
    a list of item names, and a harness_to_tool_name(name) function for mapping.
    """
    domain_dir = MIGRATE_DIR / domain
    if not domain_dir.exists():
        return {"error": f"Domain '{domain}' not found"}

    import importlib.util

    draft_file = domain_dir / "draft_tool.py"
    if not draft_file.exists():
        draft_file = domain_dir / "check.py"
    if not draft_file.exists():
        return {"error": f"No scannable module in '{domain}'"}

    spec = importlib.util.spec_from_file_location(f"migrate_{domain}_scan", str(draft_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    scan_fn = getattr(mod, "scan_available", None)
    name_fn = getattr(mod, "harness_to_tool_name", lambda x: x.upper())

    if not scan_fn:
        return {"error": f"Domain '{domain}' has no scan_available()"}

    available = scan_fn()
    tool_dir = _PROJECT_ROOT / "tool"

    migrated = []
    pending = []
    for name in available:
        tool_name = name_fn(name)
        upstream_dir = tool_dir / tool_name / "data" / "upstream" / domain
        if upstream_dir.exists():
            info_file = upstream_dir / "migration_info.json"
            status = "draft"
            if info_file.exists():
                try:
                    info = json.loads(info_file.read_text())
                    status = info.get("status", "draft")
                except Exception:
                    pass
            migrated.append({"name": name, "tool": tool_name, "status": status})
        else:
            pending.append({"name": name, "tool": tool_name})

    return {
        "available": available,
        "migrated": migrated,
        "pending": pending,
        "total": len(available),
    }


def execute_migration(domain: str, level: str, args: list = None) -> int:
    """Execute a migration for the given domain and level."""
    info = get_domain_info(domain)
    if not info:
        print(f"  Unknown domain: {domain}")
        return 1

    supported = info.get("levels", [])
    if level not in supported:
        print(f"  Domain '{domain}' does not support --{level}")
        print(f"  Supported: {', '.join(supported)}")
        return 1

    mod = get_domain_module(domain, level)
    if not mod:
        print(f"  No implementation for {domain} --{level}")
        return 1

    if hasattr(mod, "execute"):
        return mod.execute(args or [])
    else:
        print(f"  Module {domain}/{level} has no execute() function")
        return 1


def create_migrate_progress(domain: str, tool_name: str = "TOOL"):
    """Create a ProgressTuringMachine for migration operations.

    Migration domains can use this to get consistent progress display.
    Falls back to no-op if turing machine is unavailable.

    Usage in domain modules:
        from logic.command.migrate import create_migrate_progress
        tm = create_migrate_progress("CLI-Anything")
        tm.add_stage(TuringStage(...))
        tm.run()
    """
    try:
        from interface.turing import ProgressTuringMachine
        return ProgressTuringMachine(project_root=_PROJECT_ROOT, tool_name=tool_name)
    except ImportError:
        class _NoOpTM:
            def add_stage(self, *a, **kw): pass
            def run(self, *a, **kw): return True
        return _NoOpTM()


def get_turing_stage():
    """Return the TuringStage class for migration progress display."""
    try:
        from interface.turing import TuringStage
        return TuringStage
    except ImportError:
        return None
