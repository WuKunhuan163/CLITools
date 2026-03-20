"""Unified knowledge manager for skills, lessons, and discoveries.

Provides a single interface for searching, creating, and promoting
knowledge items across the three-tier hierarchy:

  Discoveries (ephemeral observations) -> Lessons (validated patterns)
    -> Skills (structured guides) -> Infrastructure (code)

Each tier mirrors the project's directory structure so items naturally
consolidate: a lesson about GIT can become a GIT-scoped skill, which
can become GIT tool infrastructure.

Usage::

    from logic.search.knowledge import KnowledgeManager

    km = KnowledgeManager(project_root)
    results = km.search("rate limiting", scope="all", top_k=5)
    km.add_lesson("API returns 429 after 30 RPM", tool="LLM", severity="warning")
    km.add_discovery("GOOGLE tool supports tab grouping", tool="GOOGLE")
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from logic.search.semantic import SemanticIndex
from logic.search.tools import _read_text, build_skill_index


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _load_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    entries = []
    try:
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def _append_jsonl(path: Path, entry: Dict):
    _ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class KnowledgeManager:
    """Unified manager for skills, lessons, and discoveries.

    Directory layout mirrors the project hierarchy::

        runtime/experience/
        ├── lessons.jsonl              # Global lessons
        ├── discoveries.jsonl          # Global discoveries
        └── tool/
            └── <TOOL_NAME>/
                ├── lessons.jsonl      # Tool-scoped lessons
                └── discoveries.jsonl  # Tool-scoped discoveries

        skills/core/                   # Global skills
        tool/<TOOL_NAME>/skills/       # Tool-scoped skills
    """

    def __init__(self, project_root: str | Path):
        self.root = Path(project_root)
        self.experience_dir = self.root / "runtime" / "experience"

    # ------------------------------------------------------------------
    # Unified search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        scope: str = "all",
        top_k: int = 10,
        tool: Optional[str] = None,
        file_pattern: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search across knowledge tiers.

        Parameters
        ----------
        query : str
            Natural language query.
        scope : str
            One of "all", "skills", "lessons", "discoveries", "tools", "docs".
        top_k : int
            Max results.
        tool : str, optional
            Scope search to a specific tool.
        file_pattern : str, optional
            Glob pattern for file matching (e.g. ``**/README.md``).
        """
        idx = SemanticIndex()

        if scope in ("all", "skills"):
            self._index_skills(idx, tool=tool)
        if scope in ("all", "lessons"):
            self._index_lessons(idx, tool=tool)
        if scope in ("all", "discoveries"):
            self._index_discoveries(idx, tool=tool)
        if scope in ("all", "tools"):
            self._index_tools(idx, tool=tool)
        if scope in ("all", "docs"):
            self._index_docs(idx)

        return idx.search(query, top_k=top_k)

    # ------------------------------------------------------------------
    # Lesson management
    # ------------------------------------------------------------------

    def add_lesson(
        self,
        lesson: str,
        tool: Optional[str] = None,
        severity: str = "info",
        context: str = "",
    ) -> Dict:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "lesson": lesson,
            "severity": severity,
        }
        if tool:
            entry["tool"] = tool
        if context:
            entry["context"] = context

        if tool:
            path = self.experience_dir / "tool" / tool / "lessons.jsonl"
        else:
            path = self.experience_dir / "lessons.jsonl"
        _append_jsonl(path, entry)

        # Also append to global for backward compatibility
        global_path = self.experience_dir / "lessons.jsonl"
        if tool and path != global_path:
            _append_jsonl(global_path, entry)

        return entry

    def get_lessons(
        self, tool: Optional[str] = None, last_n: int = 0
    ) -> List[Dict]:
        entries = _load_jsonl(self.experience_dir / "lessons.jsonl")
        if tool:
            entries = [e for e in entries if e.get("tool", "").upper() == tool.upper()]
        if last_n > 0:
            entries = entries[-last_n:]
        return entries

    # ------------------------------------------------------------------
    # Discovery management
    # ------------------------------------------------------------------

    def add_discovery(
        self,
        content: str,
        tool: Optional[str] = None,
        category: str = "general",
    ) -> Dict:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "category": category,
        }
        if tool:
            entry["tool"] = tool

        if tool:
            path = self.experience_dir / "tool" / tool / "discoveries.jsonl"
        else:
            path = self.experience_dir / "discoveries.jsonl"
        _append_jsonl(path, entry)
        return entry

    def get_discoveries(
        self, tool: Optional[str] = None, last_n: int = 0
    ) -> List[Dict]:
        paths = []
        global_path = self.experience_dir / "discoveries.jsonl"
        if global_path.exists():
            paths.append(global_path)
        tool_dir = self.experience_dir / "tool"
        if tool_dir.exists():
            for td in tool_dir.iterdir():
                if tool and td.name.upper() != tool.upper():
                    continue
                dp = td / "discoveries.jsonl"
                if dp.exists():
                    paths.append(dp)

        entries = []
        seen = set()
        for p in paths:
            for e in _load_jsonl(p):
                key = e.get("timestamp", "") + e.get("content", "")[:50]
                if key not in seen:
                    seen.add(key)
                    entries.append(e)
        entries.sort(key=lambda e: e.get("timestamp", ""))
        if last_n > 0:
            entries = entries[-last_n:]
        return entries

    # ------------------------------------------------------------------
    # Skill management (delegates to SKILLS tool for creation)
    # ------------------------------------------------------------------

    def get_skill_summary(self, top_k: int = 30) -> List[Dict[str, str]]:
        """Return Level-1 metadata for all skills (name + description).

        This is the progressive disclosure Level 1 — always includable
        in system prompt context without loading full SKILL.md files.
        """
        summaries = []
        seen = set()

        for sd in self._skill_dirs():
            if not sd.exists():
                continue
            for entry in sd.iterdir():
                skill_file = None
                if entry.is_dir():
                    skill_file = entry / "SKILL.md"
                    skill_name = entry.name
                elif entry.suffix == ".md" and entry.name != "README.md":
                    skill_file = entry
                    skill_name = entry.stem
                else:
                    continue

                if skill_name in seen or not skill_file or not skill_file.exists():
                    continue
                seen.add(skill_name)

                desc = self._extract_skill_description(skill_file)
                parent_tool = ""
                if "tool/" in str(sd):
                    parent_tool = sd.parent.name

                summaries.append({
                    "name": skill_name,
                    "description": desc,
                    "tool": parent_tool,
                    "path": str(skill_file),
                })

        return summaries[:top_k]

    # ------------------------------------------------------------------
    # Promotion: discovery -> lesson -> skill
    # ------------------------------------------------------------------

    def check_promotable_lessons(self, min_count: int = 3) -> List[Dict]:
        """Find lesson clusters that could be promoted to skills.

        Groups lessons by tool and keyword overlap. Returns clusters
        with >= min_count lessons that share a theme.
        """
        lessons = self.get_lessons()
        by_tool: Dict[str, List[Dict]] = {}
        for le in lessons:
            tool = le.get("tool", "global")
            by_tool.setdefault(tool, []).append(le)

        promotable = []
        for tool, tool_lessons in by_tool.items():
            if len(tool_lessons) >= min_count:
                promotable.append({
                    "tool": tool,
                    "count": len(tool_lessons),
                    "severities": {
                        s: sum(1 for l in tool_lessons if l.get("severity") == s)
                        for s in ("info", "warning", "critical")
                    },
                    "recent": [l["lesson"][:80] for l in tool_lessons[-3:]],
                })
        return promotable

    # ------------------------------------------------------------------
    # Internal indexing helpers
    # ------------------------------------------------------------------

    def _skill_dirs(self) -> List[Path]:
        dirs = [self.root / "skills" / "core", self.root / "skills"]
        tool_dir = self.root / "tool"
        if tool_dir.exists():
            for td in tool_dir.iterdir():
                sd = td / "skills"
                if sd.exists() and sd.is_dir():
                    dirs.append(sd)
        return dirs

    def _index_skills(self, idx: SemanticIndex, tool: Optional[str] = None):
        skill_idx = build_skill_index(self.root, tool_name=tool)
        for doc_id, tokens, meta in skill_idx._docs:
            idx.add(doc_id, " ".join(tokens), meta)

    def _index_lessons(self, idx: SemanticIndex, tool: Optional[str] = None):
        for entry in self.get_lessons(tool=tool):
            doc_id = f"lesson::{entry.get('timestamp', '')[:19]}"
            text = f"{entry.get('tool', '')} {entry.get('lesson', '')} {entry.get('context', '')}"
            idx.add(doc_id, text, {
                "type": "lesson",
                "severity": entry.get("severity", "info"),
                "tool": entry.get("tool", ""),
                "lesson": entry.get("lesson", ""),
                "timestamp": entry.get("timestamp", ""),
            })

    def _index_discoveries(self, idx: SemanticIndex, tool: Optional[str] = None):
        for entry in self.get_discoveries(tool=tool):
            doc_id = f"discovery::{entry.get('timestamp', '')[:19]}"
            text = f"{entry.get('tool', '')} {entry.get('content', '')} {entry.get('category', '')}"
            idx.add(doc_id, text, {
                "type": "discovery",
                "category": entry.get("category", "general"),
                "tool": entry.get("tool", ""),
                "content": entry.get("content", ""),
                "timestamp": entry.get("timestamp", ""),
            })

    def _index_tools(self, idx: SemanticIndex, tool: Optional[str] = None):
        from logic.search.tools import build_tool_index
        tool_idx = build_tool_index(self.root)
        for doc_id, tokens, meta in tool_idx._docs:
            if tool and doc_id.upper() != tool.upper():
                continue
            idx.add(doc_id, " ".join(tokens), meta)

    def _index_docs(self, idx: SemanticIndex):
        """Index root-level and shared logic documentation.

        Covers: for_agent.md, README.md, for_agent_reflection.md at project root,
        plus logic/*/README.md, logic/*/for_agent.md, interface/for_agent.md.
        """
        from logic.search.tools import _read_text, _split_sections

        root_docs = [
            ("for_agent.md", self.root / "for_agent.md"),
            ("README.md", self.root / "README.md"),
            ("for_agent_reflection.md", self.root / "for_agent_reflection.md"),
        ]

        for name, path in root_docs:
            text = _read_text(path, max_chars=12000)
            if not text:
                continue
            idx.add(f"root::{name}", f"project root {name} {text}", {
                "type": "doc",
                "path": str(path),
                "source": name,
                "level": "root",
            })
            for sec in _split_sections(text):
                sec_id = f"root::{name}::{sec['heading']}"
                idx.add(sec_id, f"{name} {sec['heading']} {sec['body']}", {
                    "type": "doc_section",
                    "path": str(path),
                    "source": name,
                    "heading": sec["heading"],
                    "preview": sec["body"][:200],
                    "level": "section",
                })

        for subdir in ("logic", "interface", "hooks"):
            base = self.root / subdir
            if not base.exists():
                continue
            for doc_name in ("README.md", "for_agent.md"):
                doc_path = base / doc_name
                text = _read_text(doc_path, max_chars=6000)
                if text:
                    idx.add(f"{subdir}::{doc_name}", f"{subdir} {doc_name} {text}", {
                        "type": "doc",
                        "path": str(doc_path),
                        "source": doc_name,
                        "level": "framework",
                    })

            if base.is_dir():
                for child in sorted(base.iterdir()):
                    if not child.is_dir():
                        continue
                    for doc_name in ("README.md", "for_agent.md"):
                        doc_path = child / doc_name
                        text = _read_text(doc_path, max_chars=4000)
                        if text:
                            idx.add(
                                f"{subdir}/{child.name}::{doc_name}",
                                f"{subdir} {child.name} {doc_name} {text}",
                                {
                                    "type": "doc",
                                    "path": str(doc_path),
                                    "source": doc_name,
                                    "module": f"{subdir}/{child.name}",
                                    "level": "module",
                                },
                            )

    @staticmethod
    def _extract_skill_description(skill_file: Path) -> str:
        """Extract description from SKILL.md front-matter or first paragraph."""
        try:
            text = skill_file.read_text(encoding="utf-8", errors="replace")[:2000]
        except Exception:
            return ""

        # Try YAML front-matter
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = text[3:end]
                for line in fm.split("\n"):
                    if line.strip().startswith("description:"):
                        return line.split(":", 1)[1].strip().strip('"').strip("'")

        # Fall back to first non-heading, non-empty paragraph
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("---"):
                return line[:200]

        return ""
