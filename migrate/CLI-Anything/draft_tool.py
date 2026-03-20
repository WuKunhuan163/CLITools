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
import re
import sys
import textwrap
import urllib.request
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MIGRATE_DIR = Path(__file__).resolve().parent
_TOOL_DIR = _PROJECT_ROOT / "tool"

REPO_BASE = "https://api.github.com/repos/HKUDS/CLI-Anything/contents"
RAW_BASE = "https://raw.githubusercontent.com/HKUDS/CLI-Anything/main"

NAME_MAP = {
    "audacity": "AUDACITY",
    "blender": "BLENDER",
    "comfyui": "COMFYUI",
    "drawio": "DRAWIO",
    "gimp": "GIMP.CLI",
    "inkscape": "INKSCAPE",
    "kdenlive": "KDENLIVE",
    "libreoffice": "LIBREOFFICE",
    "mermaid": "MERMAID",
    "obs-studio": "OBS",
    "shotcut": "SHOTCUT",
    "zoom": "ZOOM.CLI",
    "anygen": "ANYGEN",
}


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


def _list_harness_files(harness_name):
    """Recursively list all files in a CLI-Anything harness."""
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
                sub = _list_harness_files(f"{harness_name}/{item['name']}")
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
    """Extract Click command/group names from a CLI file."""
    commands = []
    for match in re.finditer(r"@(\w+)\.(?:command|group)\(['\"](\w+)['\"]", cli_content):
        commands.append(match.group(2))
    for match in re.finditer(r"def (\w+)\(", cli_content):
        name = match.group(1)
        if not name.startswith("_") and name not in ("main", "get_session", "output"):
            commands.append(name)
    return list(dict.fromkeys(commands))


def _generate_main_py(tool_name, harness_name, meta, commands):
    """Generate an ecosystem-compatible main.py that wraps the upstream CLI."""
    desc = meta.get("description", f"{tool_name} CLI tool")
    ep = meta.get("entry_point", "")
    module_path = f"cli_anything.{harness_name}.{harness_name}_cli"
    if "=" in ep:
        module_path = ep.split("=")[1].split(":")[0].strip()

    cmd_lines = []
    for c in commands[:10]:
        cmd_lines.append(f'    print(f"  {{DIM}}{c:14s} ...{{RESET}}")')
    cmd_help = "\n".join(cmd_lines)

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
    for c in commands[:10]:
        lines.append(f'        print(f"  {{DIM}}{c:14s} ...{{RESET}}")')
    lines.extend([
        f'        print()',
        f'        print(f"  {{BOLD}}Upstream{{RESET}}")',
        f'        print(f"  {{DIM}}Package: {{_get_upstream_package()}}{{RESET}}")',
        f'        print(f"  {{DIM}}Install: pip install -e {{_get_upstream_package()}}{{RESET}}")',
        f'        print()',
        f'        return 0',
        f'',
        f'    upstream = _get_upstream_package()',
        f'    if not upstream.exists():',
        f'        print(f"  {{BOLD}}{{RED}}Not installed.{{RESET}} Run: TOOL --migrate --draft-tool CLI-Anything {harness_name}")',
        f'        return 1',
        f'',
        f'    pkg_path = str(upstream)',
        f'    if pkg_path not in sys.path:',
        f'        sys.path.insert(0, pkg_path)',
        f'',
        f'    try:',
        f'        from {module_path} import main as cli_main',
        f'        cli_main()',
        f'    except ImportError as e:',
        f'        print(f"  {{BOLD}}{{RED}}Import error.{{RESET}} {{e}}")',
        f'        print(f"  Try: pip install -e {{upstream}}")',
        f'        return 1',
        f'    except SystemExit as e:',
        f'        return e.code or 0',
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


def migrate_one(harness_name, force=False):
    """Migrate a single CLI-Anything harness as a draft tool."""
    tool_name = NAME_MAP.get(harness_name, harness_name.upper())
    tool_path = _TOOL_DIR / tool_name

    if tool_path.exists() and not force:
        return {"ok": False, "error": f"Tool {tool_name} already exists. Use --force to overwrite upstream dir."}

    print(f"  Fetching {harness_name} from CLI-Anything...")
    files = _list_harness_files(harness_name)
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
    commands = _parse_click_commands(cli_content) if cli_content else []

    main_py = _generate_main_py(tool_name, harness_name, meta, commands)
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


def execute(args=None):
    """Execute draft-tool migration from CLI-Anything.

    Usage: TOOL --migrate --draft-tool CLI-Anything [harness_name] [--all] [--force]
    """
    args = args or []
    force = "--force" in args
    do_all = "--all" in args
    names = [a for a in args if not a.startswith("-")]

    if do_all:
        names = list(NAME_MAP.keys())
    elif not names:
        print("  Usage: TOOL --migrate --draft-tool CLI-Anything <harness> [--all] [--force]")
        print(f"  Available: {', '.join(NAME_MAP.keys())}")
        return 1

    results = []
    for name in names:
        key = name.lower()
        if key not in NAME_MAP:
            print(f"  Unknown harness: {name}")
            continue
        r = migrate_one(key, force=force)
        results.append(r)

    ok_count = sum(1 for r in results if r.get("ok"))
    print(f"\n  Migrated {ok_count}/{len(results)} harnesses as draft tools.")
    return 0 if ok_count > 0 else 1
