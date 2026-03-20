"""Core ecosystem navigation logic.

Provides structured exploration of the AITerminalTools ecosystem:
tools, skills, brain state, docs, and blueprint commands.
"""
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


def get_dashboard(root: Path) -> Dict[str, Any]:
    """Collect ecosystem overview data for the dashboard display."""
    root = Path(root)
    result = {
        "tools": _count_tools(root),
        "skills": _count_skills(root),
        "brain": _brain_summary(root),
        "workspace": _workspace_info(root),
        "blueprint_cmds": list(get_blueprint_commands(root).keys()),
    }
    return result


def get_tool_info(root: Path, name: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive info about a specific tool."""
    root = Path(root)
    tool_dir = root / "tool" / name
    if not tool_dir.exists():
        return None

    info: Dict[str, Any] = {"name": name, "path": str(tool_dir)}

    tool_json = tool_dir / "tool.json"
    if tool_json.exists():
        try:
            meta = json.loads(tool_json.read_text())
            info["description"] = meta.get("description", "")
            info["version"] = meta.get("version", "")
            info["dependencies"] = meta.get("dependencies", [])
            info["commands"] = meta.get("commands", {})
        except Exception:
            pass

    info["has_readme"] = (tool_dir / "README.md").exists()
    info["has_for_agent"] = (tool_dir / "AGENT.md").exists()
    info["has_interface"] = (tool_dir / "interface" / "main.py").exists()
    info["has_hooks"] = (tool_dir / "hooks").is_dir()
    info["has_tests"] = (tool_dir / "test").is_dir()

    test_count = 0
    if info["has_tests"]:
        test_count = sum(1 for _ in (tool_dir / "test").glob("test_*.py"))
    info["test_count"] = test_count

    if info["has_interface"]:
        iface_path = tool_dir / "interface" / "main.py"
        info["interface_functions"] = _extract_public_functions(iface_path)

    return info


def get_skill_content(root: Path, name: str) -> Optional[str]:
    """Find and return skill content by name.

    Searches project skills (with symlink resolution), library skills,
    and tool-specific skills directories.
    """
    root = Path(root)
    search_dirs = [root / "skills", root / "tool" / "SKILLS" / "logic" / "library"]

    for td in (root / "tool").iterdir() if (root / "tool").is_dir() else []:
        skill_dir = td / "skills"
        if skill_dir.is_dir():
            search_dirs.append(skill_dir)

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        direct = search_dir / name / "SKILL.md"
        if direct.exists():
            return direct.read_text(encoding="utf-8")
        for subdir in search_dir.iterdir():
            if subdir.is_dir():
                candidate = subdir / name / "SKILL.md"
                if candidate.exists():
                    return candidate.read_text(encoding="utf-8")
        for skill_file in search_dir.rglob("SKILL.md"):
            if skill_file.parent.name == name:
                return skill_file.read_text(encoding="utf-8")
    return None


def get_ecosystem_map(root: Path) -> Dict[str, Any]:
    """Build a structural map of the ecosystem."""
    root = Path(root)
    emap: Dict[str, Any] = {"root": str(root), "directories": {}}

    dir_purposes = {
        "bin/": "CLI entry points — one per tool, accessible via PATH",
        "logic/": "Internal implementation — shared modules (import via interface/)",
        "interface/": "Public API facade — all cross-tool imports go through here",
        "tool/": "Individual tools — each has main.py, logic/, interface/, hooks/, test/",
        "skills/": "Agent skill guides — SKILL.md files for development patterns",
        "hooks/": "Lifecycle hooks — session start, pre-commit, tool-call intercept",
        "runtime/": "Brain state — tasks, context, activity, lessons",
        "test/": "Root-level unit tests",
        "data/": "Runtime data — API keys, caches (gitignored)",
        "tmp/": "Temporary scripts and prototypes (gitignored, clean up after use)",
    }

    for dirname, purpose in dir_purposes.items():
        dirpath = root / dirname.rstrip("/")
        exists = dirpath.exists()
        children = []
        if exists and dirpath.is_dir():
            children = sorted(
                d.name for d in dirpath.iterdir()
                if d.is_dir() and not d.name.startswith(("__", "."))
            )[:20]
        emap["directories"][dirname] = {
            "purpose": purpose,
            "exists": exists,
            "children": children,
        }

    return emap


def get_context_here(root: Path, cwd: str) -> Dict[str, Any]:
    """Context-aware navigation based on current working directory."""
    root = Path(root)
    cwd_path = Path(cwd).resolve()
    root_resolved = root.resolve()

    ctx: Dict[str, Any] = {"cwd": str(cwd_path), "in_project": False}

    try:
        rel = cwd_path.relative_to(root_resolved)
        ctx["in_project"] = True
        ctx["relative"] = str(rel) or "."
    except ValueError:
        ctx["relative"] = None
        ctx["suggestion"] = (
            f"CWD is outside project. Ecosystem tools are available via PATH.\n"
            f"Use TOOL_PROJECT_ROOT={root} to reference project files."
        )
        return ctx

    parts = rel.parts
    ctx["level"] = "root"
    ctx["docs"] = []
    ctx["actions"] = []

    if not parts or parts[0] == ".":
        ctx["level"] = "root"
        ctx["docs"] = _find_docs(root)
        ctx["actions"] = [
            "TOOL --eco — ecosystem dashboard",
            "TOOL --eco search \"query\" — find anything",
            "TOOL --eco guide — onboarding for new agents",
        ]
    elif parts[0] == "tool" and len(parts) >= 2:
        tool_name = parts[1]
        ctx["level"] = "tool"
        ctx["tool"] = tool_name
        ctx["docs"] = _find_docs(root / "tool" / tool_name)
        ctx["actions"] = [
            f"TOOL --eco tool {tool_name} — full tool overview",
            f"TOOL --eco search \"{tool_name}\" — search related knowledge",
            f"TOOL --dev sanity-check {tool_name} — check tool structure",
        ]
    elif parts[0] == "logic" and len(parts) >= 2:
        module = parts[1]
        ctx["level"] = "module"
        ctx["module"] = module
        ctx["docs"] = _find_docs(root / "logic" / module)
        ctx["actions"] = [
            f"TOOL --eco search \"{module}\" — search related knowledge",
        ]
    elif parts[0] == "skills":
        ctx["level"] = "skills"
        ctx["actions"] = [
            "TOOL --eco skill <name> — read a specific skill",
            "SKILLS list --core — list project skills",
        ]
    elif parts[0] == "runtime":
        ctx["level"] = "brain"
        ctx["actions"] = [
            "BRAIN status — agent progress dashboard",
            "BRAIN reflect — self-check + gaps",
            "BRAIN recall \"query\" — search memory",
        ]

    return ctx


def get_onboarding_guide(root: Path) -> str:
    """Generate an onboarding guide for a context-free assistant."""
    root = Path(root)
    lines = [
        "# Quick Bootstrap",
        "",
        "## Step 1: Orient",
        "  TOOL --eco                    — ecosystem dashboard (tools, skills, brain)",
        "  TOOL --eco map                — directory structure and purposes",
        "  TOOL --eco here               — context-aware help for your CWD",
        "",
        "## Step 2: Understand",
        "  TOOL --eco search \"topic\"     — semantic search across all knowledge",
        "  TOOL --eco tool <NAME>        — deep-dive into a specific tool",
        "  TOOL --eco skill <name>       — read a development skill/pattern",
        "",
        "## Step 3: Remember",
        "  BRAIN status                — current tasks and brain state",
        "  BRAIN recall \"keyword\"      — search lessons and activity",
        "  BRAIN reflect               — self-check protocol + system gaps",
        "",
        "## Step 4: Act",
        "  TOOL --eco cmds               — blueprint-defined shortcut commands",
        "  TOOL --eco cmd <name>         — run a shortcut command",
        "  TOOL --audit code           — code quality check",
        "  SKILLS learn \"lesson\"       — record a discovery",
        "",
        "## Key Principles",
        "  - Search before creating: TOOL --eco search \"...\" avoids duplicates",
        "  - Fix bugs at source, don't work around them",
        "  - Record lessons: SKILLS learn \"lesson\" --severity warning",
        "  - After tasks: BRAIN log \"what I did\" then BRAIN reflect",
    ]
    return "\n".join(lines)


def get_blueprint_commands(root: Path) -> Dict[str, Dict[str, str]]:
    """Load custom CLI commands defined in the active brain blueprint."""
    root = Path(root)

    active_blueprint = _get_active_blueprint(root)
    if not active_blueprint:
        return {}

    return active_blueprint.get("commands", {})


def run_blueprint_command(root: Path, cmd_name: str) -> Optional[str]:
    """Get the shell command string for a blueprint-defined command.

    Returns the command string to execute, or None if not found.
    """
    cmds = get_blueprint_commands(root)
    cmd_def = cmds.get(cmd_name)
    if not cmd_def:
        return None
    if isinstance(cmd_def, str):
        return cmd_def
    return cmd_def.get("run", "")


# --- Internal helpers ---

def _count_tools(root: Path) -> Dict[str, int]:
    tool_dir = root / "tool"
    if not tool_dir.exists():
        return {"total": 0, "installed": 0}
    all_tools = [d for d in tool_dir.iterdir() if d.is_dir() and (d / "main.py").exists()]
    bin_dir = root / "bin"
    installed = 0
    for t in all_tools:
        if (bin_dir / t.name / t.name).exists() or (bin_dir / t.name).is_file():
            installed += 1
    return {"total": len(all_tools), "installed": installed}


def _count_skills(root: Path) -> Dict[str, int]:
    core = root / "skills"
    library = root / "tool" / "SKILLS" / "logic" / "library"
    core_count = sum(1 for _ in core.rglob("SKILL.md")) if core.exists() else 0
    lib_count = sum(1 for _ in library.rglob("SKILL.md")) if library.exists() else 0
    return {"core": core_count, "library": lib_count}


def _brain_summary(root: Path) -> Dict[str, Any]:
    brain_dir = root / "runtime" / "brain"
    lessons_file = root / "runtime" / "experience" / "lessons.jsonl"

    summary: Dict[str, Any] = {"tasks_active": 0, "tasks_done": 0, "lessons": 0}

    tasks_file = brain_dir / "tasks.json"
    if tasks_file.exists():
        try:
            tasks = json.loads(tasks_file.read_text())
            for t in tasks:
                if t.get("status") == "done":
                    summary["tasks_done"] += 1
                else:
                    summary["tasks_active"] += 1
        except Exception:
            pass

    if lessons_file.exists():
        summary["lessons"] = sum(
            1 for line in lessons_file.read_text().strip().split("\n")
            if line.strip()
        )

    context_file = brain_dir / "context.md"
    if context_file.exists():
        age = time.time() - context_file.stat().st_mtime
        summary["context_age_min"] = int(age / 60)
    else:
        summary["context_age_min"] = -1

    return summary


def _workspace_info(root: Path) -> Optional[Dict[str, str]]:
    try:
        from interface.workspace import get_workspace_manager
        wm = get_workspace_manager(root)
        info = wm.active_workspace_info()
        if info:
            return {"name": info["name"], "path": info["path"]}
    except Exception:
        pass
    return None


def _find_docs(directory: Path) -> List[str]:
    docs = []
    for name in ["README.md", "AGENT.md", "AGENT_REFLECTION.md"]:
        if (directory / name).exists():
            docs.append(str(directory / name))
    return docs


def _extract_public_functions(filepath: Path) -> List[str]:
    """Extract public function names from a Python file (quick parse)."""
    funcs = []
    try:
        for line in filepath.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("def ") and not stripped.startswith("def _"):
                name = stripped.split("(")[0][4:]
                funcs.append(name)
    except Exception:
        pass
    return funcs


def _get_active_blueprint(root: Path) -> Optional[Dict]:
    """Load the active brain blueprint JSON.

    Resolution order:
    1. runtime/brain/blueprint.json (active runtime blueprint)
    2. If it has inherits/type/active, also load the referenced type from
       logic/brain/blueprint/ and merge commands from both
    3. Fallback to logic/brain/blueprint/base.json
    """
    root = Path(root)
    result = {}

    blueprint_file = root / "runtime" / "brain" / "blueprint.json"
    if blueprint_file.exists():
        try:
            result = json.loads(blueprint_file.read_text())
        except Exception:
            pass

    bp_name = result.get("active") or result.get("type") or result.get("inherits")
    if bp_name and bp_name != "base":
        bp_dir = root / "logic" / "brain" / "blueprint" / bp_name
        bp_json = bp_dir / "blueprint.json"
        if bp_json.exists():
            try:
                parent = json.loads(bp_json.read_text())
                parent_cmds = parent.get("commands", {})
                runtime_cmds = result.get("commands", {})
                parent_cmds.update(runtime_cmds)
                if parent_cmds:
                    result["commands"] = parent_cmds
            except Exception:
                pass

    if result:
        return result

    base_json = root / "logic" / "brain" / "blueprint" / "base.json"
    if base_json.exists():
        try:
            return json.loads(base_json.read_text())
        except Exception:
            pass

    return None
