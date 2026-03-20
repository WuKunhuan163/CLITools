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
