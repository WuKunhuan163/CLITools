"""Search tools, interfaces, and skills by semantic similarity.

Builds a TF-IDF index over tool README.md / for_agent.md content and
lets agents (or users) discover relevant tools, interfaces, or skills
using natural language queries.

Two search depths:
  - ``search_tools()``: one document per tool (fast, broad)
  - ``search_tools_deep()``: section- and command-level granularity
    (slower first build, but locates specific commands and techniques)
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from logic._.search.semantic import SemanticIndex


def _read_text(path: Path, max_chars: int = 8000) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[:max_chars]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Tool search
# ---------------------------------------------------------------------------

def build_tool_index(project_root: Path) -> SemanticIndex:
    """Index all tools' README.md, for_agent.md, and tool.json description."""
    idx = SemanticIndex()
    tool_dir = project_root / "tool"
    if not tool_dir.exists():
        return idx

    for td in sorted(tool_dir.iterdir()):
        if not td.is_dir():
            continue
        tj = td / "tool.json"
        desc = ""
        purpose = ""
        if tj.exists():
            try:
                meta = json.loads(tj.read_text())
                desc = meta.get("description", "")
                purpose = meta.get("purpose", "")
            except Exception:
                pass

        readme = _read_text(td / "README.md")
        for_agent = _read_text(td / "for_agent.md")

        combined = f"{td.name} {desc} {purpose} {readme} {for_agent}"
        idx.add(td.name, combined, {
            "type": "tool",
            "path": str(td),
            "description": desc,
            "purpose": purpose,
            "has_readme": bool(readme),
            "has_for_agent": bool(for_agent),
        })

    return idx


def search_tools(project_root: Path, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search all tools by natural language query.

    Parameters
    ----------
    project_root : Path
        Project root directory.
    query : str
        Natural language query, e.g. "open a Chrome tab".
    top_k : int
        Max results to return.

    Returns
    -------
    list[dict]
        Ranked results with ``id``, ``score``, ``meta``.
    """
    idx = build_tool_index(project_root)
    return idx.search(query, top_k=top_k)


# ---------------------------------------------------------------------------
# Deep tool search (section + command level)
# ---------------------------------------------------------------------------

def _split_sections(text: str) -> List[Dict[str, str]]:
    """Split markdown text into sections by headings."""
    lines = text.split("\n")
    sections = []
    current_heading = ""
    current_body: List[str] = []

    for line in lines:
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            if current_heading or current_body:
                sections.append({
                    "heading": current_heading,
                    "body": "\n".join(current_body).strip(),
                })
            current_heading = m.group(2).strip()
            current_body = []
        else:
            current_body.append(line)

    if current_heading or current_body:
        sections.append({
            "heading": current_heading,
            "body": "\n".join(current_body).strip(),
        })

    return [s for s in sections if s["body"]]


def _extract_commands_from_for_agent(text: str) -> List[Dict[str, str]]:
    """Extract command examples from for_agent.md code blocks."""
    commands = []
    in_code = False
    code_lines: List[str] = []

    for line in text.split("\n"):
        if line.strip().startswith("```"):
            if in_code:
                for cl in code_lines:
                    cl = cl.strip()
                    if cl and not cl.startswith("#") and not cl.startswith("//"):
                        parts = cl.split()
                        if parts:
                            commands.append({
                                "command": cl,
                                "tool": parts[0] if parts else "",
                            })
                code_lines = []
            in_code = not in_code
        elif in_code:
            code_lines.append(line)

    return commands


def build_deep_tool_index(project_root: Path) -> SemanticIndex:
    """Index tools at section and command granularity.

    Indexes three levels:
    1. Tool-level (same as build_tool_index)
    2. Section-level (each heading section of for_agent.md and README.md)
    3. Command-level (each command example from code blocks)
    """
    idx = SemanticIndex()
    tool_dir = project_root / "tool"
    if not tool_dir.exists():
        return idx

    for td in sorted(tool_dir.iterdir()):
        if not td.is_dir():
            continue
        tj = td / "tool.json"
        desc = ""
        purpose = ""
        if tj.exists():
            try:
                meta = json.loads(tj.read_text())
                desc = meta.get("description", "")
                purpose = meta.get("purpose", "")
            except Exception:
                pass

        tool_name = td.name

        idx.add(tool_name, f"{tool_name} {desc} {purpose}", {
            "type": "tool",
            "path": str(td),
            "description": desc,
            "purpose": purpose,
            "level": "tool",
        })

        for doc_name in ("for_agent.md", "README.md"):
            doc_path = td / doc_name
            text = _read_text(doc_path, max_chars=12000)
            if not text:
                continue

            sections = _split_sections(text)
            for sec in sections:
                sec_id = f"{tool_name}::{sec['heading']}"
                combined = f"{tool_name} {sec['heading']} {sec['body']}"
                idx.add(sec_id, combined, {
                    "type": "section",
                    "tool": tool_name,
                    "heading": sec["heading"],
                    "source": doc_name,
                    "path": str(doc_path),
                    "preview": sec["body"][:200],
                    "level": "section",
                })

            cmds = _extract_commands_from_for_agent(text)
            for cmd_info in cmds:
                cmd_id = f"{tool_name}::cmd::{cmd_info['command'][:40]}"
                idx.add(cmd_id, f"{tool_name} {cmd_info['command']}", {
                    "type": "command",
                    "tool": tool_name,
                    "command": cmd_info["command"],
                    "source": doc_name,
                    "path": str(doc_path),
                    "level": "command",
                })

    return idx


def search_tools_deep(project_root: Path, query: str,
                      top_k: int = 10) -> List[Dict[str, Any]]:
    """Search tools at section and command granularity.

    Returns ranked results with ``level`` field indicating
    whether the match is tool/section/command level.
    """
    idx = build_deep_tool_index(project_root)
    return idx.search(query, top_k=top_k)


# ---------------------------------------------------------------------------
# Interface search
# ---------------------------------------------------------------------------

def build_interface_index(project_root: Path) -> SemanticIndex:
    """Index all tool interfaces (interface/main.py docstrings and content)."""
    idx = SemanticIndex()
    tool_dir = project_root / "tool"
    if not tool_dir.exists():
        return idx

    for td in sorted(tool_dir.iterdir()):
        iface = td / "interface" / "main.py"
        if not iface.exists():
            continue
        content = _read_text(iface)
        if not content.strip():
            continue
        idx.add(td.name, f"{td.name} interface {content}", {
            "type": "interface",
            "path": str(iface),
            "tool": td.name,
        })

    return idx


def search_interfaces(project_root: Path, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search tool interfaces by query."""
    idx = build_interface_index(project_root)
    return idx.search(query, top_k=top_k)


# ---------------------------------------------------------------------------
# Skill search
# ---------------------------------------------------------------------------

def build_skill_index(project_root: Path, tool_name: Optional[str] = None) -> SemanticIndex:
    """Index skills.

    If *tool_name* is given, index that tool's skills first, then global
    skills so agents always see all available skills ranked by relevance.
    """
    idx = SemanticIndex()

    skill_dirs = []
    if tool_name:
        skill_dirs.append(project_root / "tool" / tool_name / "skills")

    # Always include global skills
    skill_dirs.extend([
        project_root / "skills" / "core",
        project_root / "skills",
    ])

    # Also include per-tool skills from all tools
    tool_dir = project_root / "tool"
    if tool_dir.exists():
        for td in tool_dir.iterdir():
            sd = td / "skills"
            if sd.exists() and sd.is_dir():
                skill_dirs.append(sd)

    seen = set()
    for sd in skill_dirs:
        if not sd.exists():
            continue
        for entry in sd.iterdir():
            skill_file = None
            if entry.is_dir():
                skill_file = entry / "SKILL.md"
                skill_name = entry.name
            elif entry.suffix == ".md":
                skill_file = entry
                skill_name = entry.stem
            else:
                continue

            if skill_file and skill_file.exists() and skill_name not in seen:
                seen.add(skill_name)
                content = _read_text(skill_file, max_chars=4000)
                parent_tool = ""
                if "tool/" in str(sd):
                    parent_tool = sd.parent.name
                idx.add(skill_name, f"{skill_name} {content}", {
                    "type": "skill",
                    "path": str(skill_file),
                    "tool": parent_tool,
                })

    return idx


def search_skills(project_root: Path, query: str, top_k: int = 5,
                  tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search skills by query, optionally scoped to a specific tool."""
    idx = build_skill_index(project_root, tool_name=tool_name)
    return idx.search(query, top_k=top_k)
