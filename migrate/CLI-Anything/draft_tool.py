"""CLI-Anything: draft-tool migration.

Downloads a CLI harness from the CLI-Anything repo, scaffolds it into
our tool/ directory, parses upstream metadata (setup.py, CLI structure),
and auto-generates ecosystem-compatible wrappers.

CLI-Anything structure (consistent across all harnesses):
  <name>/agent-harness/
    setup.py                          # pip metadata, deps, entry_points
    <NAME>.md                         # Agent docs
    cli_anything/<name>/
      <name>_cli.py                   # Click-based CLI (main entry)
      core/                           # Domain-specific logic modules
      utils/                          # Backend, REPL, helpers
      tests/                          # Tests (TEST.md + test_*.py)
      README.md                       # Package description
      skills/SKILL.md                 # Agent skill definition
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MIGRATE_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _PROJECT_ROOT / "tool"
_CLONE_CACHE = _MIGRATE_DIR / ".cache" / "CLI-Anything"

REPO_URL = "https://github.com/HKUDS/CLI-Anything.git"
REPO_BASE = "https://api.github.com/repos/HKUDS/CLI-Anything/contents"
RAW_BASE = "https://raw.githubusercontent.com/HKUDS/CLI-Anything/main"

SOURCE_PREFIX = "CLIAnything"

SPECIAL_NAMES = {
    "obs-studio": "OBS",
}


def harness_to_tool_name(harness_name: str) -> str:
    """Derive ecosystem tool name from a CLI-Anything harness name.

    Naming convention: <Source>.<N> where Source is the migration source
    and N is the uppercased harness name. This avoids collision with
    tools from other migration sources.

    Examples: CLIAnything.BLENDER, CLIAnything.GIMP, CLIAnything.OBS
    """
    if harness_name in SPECIAL_NAMES:
        short = SPECIAL_NAMES[harness_name]
    else:
        short = harness_name.upper().replace("-", "")
    return f"{SOURCE_PREFIX}.{short}"


def _ensure_clone():
    """Shallow-clone the CLI-Anything repo once, reuse for all harnesses."""
    try:
        from tool.GITHUB.interface.main import clone_repo, pull_repo
        if _CLONE_CACHE.exists() and (_CLONE_CACHE / ".git").exists():
            pull_repo(str(_CLONE_CACHE))
            return True
        _CLONE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        return clone_repo(REPO_URL, str(_CLONE_CACHE), shallow=True)
    except ImportError:
        if _CLONE_CACHE.exists() and (_CLONE_CACHE / ".git").exists():
            subprocess.run(["git", "pull", "--ff-only"], cwd=_CLONE_CACHE,
                            capture_output=True, timeout=60)
            return True
        _CLONE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(_CLONE_CACHE)],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0


def _list_harness_files_local(harness_name):
    """List files from local clone."""
    harness_dir = _CLONE_CACHE / harness_name
    if not harness_dir.exists():
        return []
    files = []
    for p in harness_dir.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            rel = p.relative_to(harness_dir)
            files.append({
                "name": str(rel),
                "local_path": str(p),
                "size": p.stat().st_size,
            })
    return files


def _fetch_json(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "AITerminalTools/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _fetch_raw(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AITerminalTools/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def _list_harness_files_api(harness_name):
    """Recursively list all files via GitHub API (fallback)."""
    try:
        contents = _fetch_json(f"{REPO_BASE}/{harness_name}")
        files = []
        for item in contents:
            if item["type"] == "file":
                files.append({
                    "name": item["name"],
                    "path": item["path"],
                    "download_url": item["download_url"],
                    "size": item["size"],
                })
            elif item["type"] == "dir":
                sub = _list_harness_files_api(f"{harness_name}/{item['name']}")
                for sf in sub:
                    sf["name"] = f"{item['name']}/{sf['name']}"
                files.extend(sub)
        return files
    except Exception:
        return []


def _parse_setup_py(content: str) -> dict:
    """Extract metadata from a CLI-Anything setup.py."""
    meta = {"deps": [], "entry_point": "", "description": "", "name": "", "version": ""}
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'setup':
                for kw in node.keywords:
                    if kw.arg == "name":
                        meta["name"] = ast.literal_eval(kw.value)
                    elif kw.arg == "version":
                        meta["version"] = ast.literal_eval(kw.value)
                    elif kw.arg == "description":
                        meta["description"] = ast.literal_eval(kw.value)
                    elif kw.arg == "install_requires":
                        meta["deps"] = ast.literal_eval(kw.value)
                    elif kw.arg == "entry_points":
                        ep = ast.literal_eval(kw.value)
                        scripts = ep.get("console_scripts", [])
                        if scripts:
                            meta["entry_point"] = scripts[0]
    except Exception:
        pass
    return meta


def _parse_click_commands(cli_content: str) -> list:
    """Extract Click command/group hierarchy from a CLI file.

    Returns a flat list for backward compatibility, but groups are prefixed
    with their parent group name (e.g. "project new", "project open").
    Also returns a structured hierarchy accessible via _parse_click_tree().
    """
    tree = _parse_click_tree(cli_content)
    flat = []
    for group_name, sub_cmds in tree.items():
        if sub_cmds:
            for cmd in sub_cmds:
                flat.append(f"{group_name} {cmd}")
        else:
            flat.append(group_name)
    return flat


def _parse_click_tree(cli_content: str) -> dict:
    """Parse Click CLI file to extract group->commands hierarchy.

    Returns dict of {group_or_cmd: [sub_commands]} where leaf commands
    have an empty list as value.
    """
    tree = {}

    root_group = None
    root_match = re.search(r"@click\.group\(", cli_content)
    if root_match:
        fn_match = re.search(r"def\s+(\w+)\(", cli_content[root_match.end():])
        if fn_match:
            root_group = fn_match.group(1)

    groups = {}
    for match in re.finditer(r"@(\w+)\.group\(\)", cli_content):
        parent = match.group(1)
        fn_match = re.search(r"def\s+(\w+)\(", cli_content[match.end():])
        if fn_match:
            group_name = fn_match.group(1)
            groups[group_name] = parent

    for match in re.finditer(r"@(\w+)\.command\(['\"]?([\w-]+)['\"]?\)", cli_content):
        parent = match.group(1)
        cmd_name = match.group(2)
        if parent not in tree:
            tree[parent] = []
        tree[parent].append(cmd_name)

    result = {}
    for group_name in sorted(groups.keys()):
        cmds = tree.get(group_name, [])
        result[group_name] = cmds

    for parent, cmds in tree.items():
        if parent not in groups and parent != root_group:
            result[parent] = cmds

    if root_group and root_group in tree:
        for cmd in tree[root_group]:
            if cmd not in result:
                result[cmd] = []

    if not result:
        for match in re.finditer(r"def (\w+)\(", cli_content):
            name = match.group(1)
            if not name.startswith("_") and name not in ("main", "get_session", "output", "emit", "cli"):
                result[name] = []

    return result


def _generate_main_py(tool_name, harness_name, meta, commands, click_tree=None):
    """Generate an ecosystem-compatible main.py that wraps the upstream CLI."""
    desc = meta.get("description", f"{tool_name} CLI tool")
    ep = meta.get("entry_point", "")
    module_path = f"cli_anything.{harness_name}.{harness_name}_cli"
    if "=" in ep:
        module_path = ep.split("=")[1].split(":")[0].strip()

    class_name = tool_name.replace(".", "_")

    lines = [
        f'#!/usr/bin/env python3',
        f'"""{tool_name} Tool — {desc}',
        f'',
        f'Wraps the CLI-Anything {harness_name} harness.',
        f'Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/{harness_name}',
        f'"""',
        f'import sys',
        f'import os',
        f'from pathlib import Path',
        f'',
        f'script_path = Path(__file__).resolve()',
        f'project_root = script_path.parent.parent.parent',
        f'if str(project_root) not in sys.path:',
        f'    sys.path.insert(0, str(project_root))',
        f'',
        f'from interface.tool import ToolBase',
        f'from interface.config import get_color',
        f'',
        f'BOLD = get_color("BOLD")',
        f'DIM = get_color("DIM")',
        f'RESET = get_color("RESET")',
        f'GREEN = get_color("GREEN")',
        f'RED = get_color("RED")',
        f'',
        f'',
        f'class {class_name}Tool(ToolBase):',
        f'    def __init__(self):',
        f'        super().__init__("{tool_name}")',
        f'',
        f'',
        f'def _get_upstream_package():',
        f'    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"',
        f'',
        f'',
        f'def main():',
        f'    tool = {class_name}Tool()',
        f'',
        f'    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:',
        f'        print(f"\\n  {{BOLD}}{tool_name}{{RESET}} (via CLI-Anything)")',
        f'        print(f"  {{DIM}}{desc}{{RESET}}")',
        f'        print()',
        f'        print(f"  {{BOLD}}Commands{{RESET}}")',
    ]

    if click_tree:
        shown = 0
        for group, sub_cmds in list(click_tree.items())[:8]:
            if sub_cmds:
                lines.append(f'        print(f"  {{BOLD}}{group}{{RESET}}")')
                for sc in sub_cmds[:5]:
                    lines.append(f'        print(f"    {{DIM}}{sc:12s}{{RESET}}")')
                if len(sub_cmds) > 5:
                    lines.append(f'        print(f"    {{DIM}}... +{len(sub_cmds) - 5} more{{RESET}}")')
            else:
                lines.append(f'        print(f"  {{DIM}}{group:14s}{{RESET}}")')
            shown += 1
        if len(click_tree) > 8:
            lines.append(f'        print(f"  {{DIM}}... +{len(click_tree) - 8} more groups{{RESET}}")')
    else:
        for c in commands[:10]:
            lines.append(f'        print(f"  {{DIM}}{c:14s}{{RESET}}")')

    lines.extend([
        f'        print()',
        f'        print(f"  {{BOLD}}Upstream{{RESET}}")',
        f'        print(f"  {{DIM}}Package: {{_get_upstream_package()}}{{RESET}}")',
        f'        print(f"  {{DIM}}Install: pip install -e {{_get_upstream_package()}}{{RESET}}")',
        f'        print()',
        f'        return 0',
        f'',
        f'    raise NotImplementedError(',
        f'        f"{tool_name} is a draft tool migrated from CLI-Anything/{harness_name}. "',
        f'        f"Post-development required: move logic from data/upstream/ into logic/, "',
        f'        f"rewrite main.py with argparse, create interface/main.py. "',
        f'        f"Run TOOL --migrate --scan CLIANYTHING for migration status."',
        f'    )',
        f'',
        f'',
        f'if __name__ == "__main__":',
        f'    sys.exit(main() or 0)',
    ])
    return "\n".join(lines) + "\n"


def _generate_tool_json(tool_name, harness_name, meta):
    return json.dumps({
        "name": tool_name,
        "version": meta.get("version", "0.1.0") + "-draft",
        "description": meta.get("description", f"CLI harness for {harness_name}"),
        "source": "CLI-Anything",
        "upstream": f"https://github.com/HKUDS/CLI-Anything/tree/main/{harness_name}",
        "status": "draft",
        "dependencies": meta.get("deps", []),
    }, indent=2)


def _generate_for_agent(tool_name, harness_name, meta, commands):
    cmd_list = "\n".join(f"| {c} | (upstream) |" for c in commands[:15])
    return textwrap.dedent(f"""\
        # {tool_name} — Agent Guide

        ## Source

        Migrated from [CLI-Anything/{harness_name}](https://github.com/HKUDS/CLI-Anything/tree/main/{harness_name}).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        {tool_name}/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        {cmd_list}

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
    """)


def migrate_one(harness_name, force=False, use_local=True):
    """Migrate a single CLI-Anything harness as a draft tool."""
    tool_name = harness_to_tool_name(harness_name)
    tool_path = _TOOL_DIR / tool_name

    if tool_path.exists() and not force:
        return {"ok": False, "error": f"Tool {tool_name} already exists. Use --force to overwrite upstream dir."}

    print(f"  Fetching {harness_name} from CLI-Anything...")

    if use_local:
        files = _list_harness_files_local(harness_name)
    else:
        files = _list_harness_files_api(harness_name)
    if not files:
        return {"ok": False, "error": f"No files found for {harness_name}"}

    tool_path.mkdir(parents=True, exist_ok=True)
    for subdir in ["logic", "interface", "data", "test"]:
        (tool_path / subdir).mkdir(exist_ok=True)

    upstream_dir = tool_path / "data" / "upstream" / "CLI-Anything"
    upstream_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    setup_content = ""
    cli_content = ""
    readme_content = ""

    for f in files:
        try:
            if "local_path" in f:
                content = Path(f["local_path"]).read_text(errors="replace")
            else:
                content = _fetch_raw(f["download_url"])
            target = upstream_dir / f["name"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            downloaded += 1

            if f["name"].endswith("setup.py"):
                setup_content = content
            elif f["name"].endswith(f"{harness_name}_cli.py") or f["name"].endswith("_cli.py"):
                cli_content = content
            elif f["name"] == f"agent-harness/{harness_name.upper()}.md" or f["name"].endswith(f"/{harness_name.upper()}.md"):
                readme_content = content
            elif f["name"].endswith("README.md") and not readme_content:
                readme_content = content
        except Exception as e:
            print(f"    Warning: failed to fetch {f['name']}: {e}")

    meta = _parse_setup_py(setup_content) if setup_content else {}
    click_tree = _parse_click_tree(cli_content) if cli_content else {}
    commands = _parse_click_commands(cli_content) if cli_content else []

    main_py = _generate_main_py(tool_name, harness_name, meta, commands, click_tree=click_tree)
    (tool_path / "main.py").write_text(main_py)

    tool_json = _generate_tool_json(tool_name, harness_name, meta)
    (tool_path / "tool.json").write_text(tool_json)

    for_agent = _generate_for_agent(tool_name, harness_name, meta, commands)
    (tool_path / "for_agent.md").write_text(for_agent)

    readme = f"# {tool_name}\n\n"
    if meta.get("description"):
        readme += f"{meta['description']}\n\n"
    readme += f"Migrated from [CLI-Anything/{harness_name}](https://github.com/HKUDS/CLI-Anything/tree/main/{harness_name}).\n\n"
    readme += "**Status**: Draft — needs post-processing for ecosystem integration.\n"
    (tool_path / "README.md").write_text(readme)

    migration_info = {
        "source": "CLI-Anything",
        "harness": harness_name,
        "tool_name": tool_name,
        "files_downloaded": downloaded,
        "total_files": len(files),
        "status": "draft",
        "metadata": meta,
        "click_tree": click_tree,
        "commands_detected": commands,
        "auto_generated": ["main.py", "tool.json", "for_agent.md", "README.md"],
        "post_processing": [
            "Move core logic from data/upstream/ into logic/",
            "Rewrite main.py with argparse (replace Click)",
            "Create interface/main.py for cross-tool API",
            "Add localization support",
            "Write tests",
        ],
    }
    (upstream_dir / "migration_info.json").write_text(json.dumps(migration_info, indent=2))

    print(f"  Migrated {harness_name} -> {tool_name}: {downloaded}/{len(files)} files, {len(commands)} commands detected")
    return {"ok": True, "tool_name": tool_name, "files": downloaded, "commands": commands}


def scan_available():
    """Discover all available harnesses from the upstream repo.

    Returns a list of harness names found in the clone, each with an
    agent-harness/ subdirectory.
    """
    if not _ensure_clone():
        return []
    harnesses = []
    for d in sorted(_CLONE_CACHE.iterdir()):
        if d.is_dir() and (d / "agent-harness").is_dir():
            harnesses.append(d.name)
    return harnesses


def execute(args=None):
    """Execute draft-tool migration from CLI-Anything.

    Usage: TOOL --migrate --draft-tool CLI-Anything [harness_name] [--all] [--force]
    """
    args = args or []
    force = "--force" in args
    do_all = "--all" in args
    names = [a for a in args if not a.startswith("-")]

    print("  Ensuring local clone...")
    use_local = _ensure_clone()
    if not use_local:
        print("  Warning: git clone failed, falling back to API (may hit rate limits)")

    available = scan_available() if use_local else []

    if do_all:
        names = available if available else names
    elif not names:
        print("  Usage: TOOL --migrate --draft-tool CLI-Anything <harness> [--all] [--force]")
        if available:
            print(f"  Available ({len(available)}): {', '.join(available)}")
        return 1

    results = []
    for name in names:
        key = name.lower()
        if available and key not in available:
            print(f"  Unknown harness: {name} (not found in upstream)")
            continue
        r = migrate_one(key, force=force, use_local=use_local)
        results.append(r)

    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"\n  Migrated {ok_count}/{len(results)} harnesses as draft tools.")
    return 0 if ok_count > 0 else 1
