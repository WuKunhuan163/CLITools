"""Procedural skill matching — ProcMEM-inspired reflex arcs.

Two layers of reflex arcs:

1. **Blueprint skills** (static): Predefined in blueprint.json's procedural_skills.
   Activation conditions are regex patterns matched against agent actions.
   These are deterministic — guaranteed to fire when the pattern matches.

2. **Lesson triggers** (dynamic): Lessons in lessons.jsonl can have optional
   trigger_patterns. When an agent action matches, the lesson is surfaced.
   This allows the system to learn new reflex arcs from experience.

Both layers are checked by check_action() and merged into a single injection.

Reference: ProcMEM (Mi et al., ICML 2026) — Skill = <activation, execution, termination>
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Layer 1: Blueprint procedural skills (static, deterministic)
# ---------------------------------------------------------------------------

def load_procedural_skills(blueprint_path: Path) -> list:
    """Load procedural_skills from a blueprint.json file."""
    try:
        with open(blueprint_path, "r", encoding="utf-8") as f:
            bp = json.load(f)
        section = bp.get("procedural_skills", {})
        return section.get("skills", [])
    except Exception:
        return []


def match_skills(action_text: str, skills: list) -> List[dict]:
    """Match an agent action against procedural skill activation patterns.

    Returns list of matched skill dicts, sorted by hit count (desc).
    """
    if not action_text or not skills:
        return []

    matched = []
    action_lower = action_text.lower()

    for skill in skills:
        activation = skill.get("activation", {})
        patterns = activation.get("patterns", [])
        hit_count = 0
        for pattern in patterns:
            try:
                if re.search(pattern, action_text, re.IGNORECASE):
                    hit_count += 1
            except re.error:
                if pattern.lower() in action_lower:
                    hit_count += 1
        if hit_count > 0:
            matched.append((hit_count, skill))

    matched.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in matched]


# ---------------------------------------------------------------------------
# Layer 2: Lesson-based triggers (dynamic, learned from experience)
# ---------------------------------------------------------------------------

def load_lessons_with_triggers(lessons_path: Path) -> List[Dict]:
    """Load lessons that have trigger_patterns defined."""
    if not lessons_path.exists():
        return []
    triggered = []
    try:
        for line in lessons_path.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("trigger_patterns"):
                triggered.append(entry)
    except Exception:
        pass
    return triggered


def match_lessons(action_text: str, lessons: List[Dict]) -> List[Dict]:
    """Match agent action against lesson trigger patterns.

    Returns matched lessons sorted by severity (critical > warning > info).
    """
    if not action_text or not lessons:
        return []

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    matched = []

    for lesson in lessons:
        patterns = lesson.get("trigger_patterns", [])
        for pattern in patterns:
            try:
                if re.search(pattern, action_text, re.IGNORECASE):
                    matched.append(lesson)
                    break
            except re.error:
                if pattern.lower() in action_text.lower():
                    matched.append(lesson)
                    break

    matched.sort(key=lambda l: severity_order.get(l.get("severity", "info"), 2))
    return matched


def add_trigger_patterns(lessons_path: Path, lesson_index: int,
                         patterns: List[str]) -> bool:
    """Add trigger_patterns to an existing lesson by line index (0-based).

    This upgrades a passive lesson into an active reflex arc.
    """
    if not lessons_path.exists():
        return False
    try:
        lines = lessons_path.read_text(encoding="utf-8").strip().split("\n")
        if lesson_index < 0 or lesson_index >= len(lines):
            return False
        entry = json.loads(lines[lesson_index])
        existing = entry.get("trigger_patterns", [])
        merged = list(set(existing + patterns))
        entry["trigger_patterns"] = merged
        lines[lesson_index] = json.dumps(entry, ensure_ascii=False)
        lessons_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_skill_injection(skills: List[dict], max_skills: int = 3) -> Optional[str]:
    """Format matched blueprint skills as injection text."""
    if not skills:
        return None

    lines = ["[Procedural Reflex Arc — review before proceeding]"]
    for skill in skills[:max_skills]:
        desc = skill.get("activation", {}).get("description", "")
        steps = skill.get("execution", [])
        term = skill.get("termination", "")

        lines.append(f"\n  Trigger: {desc}")
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step}")
        if term:
            lines.append(f"  Done when: {term}")

    return "\n".join(lines)


def format_lesson_injection(lessons: List[Dict], max_lessons: int = 3) -> Optional[str]:
    """Format matched lessons as injection text."""
    if not lessons:
        return None

    lines = ["[Learned Reflex — from past experience]"]
    for lesson in lessons[:max_lessons]:
        sev = lesson.get("severity", "info")
        text = lesson.get("lesson", "")
        tool = lesson.get("tool", "")
        ctx = lesson.get("context", "")

        prefix = f"[{sev}]" if sev != "info" else ""
        tool_tag = f" ({tool})" if tool else ""
        lines.append(f"\n  {prefix} {text}{tool_tag}")
        if ctx:
            lines.append(f"  Context: {ctx}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Unified check
# ---------------------------------------------------------------------------

def _resolve_root(blueprint_path: Path) -> Path:
    """Resolve project root from blueprint path."""
    # blueprint_path: <root>/logic/_/brain/blueprint/<name>/blueprint.json
    return blueprint_path.parent.parent.parent.parent.parent


def check_action(action_text: str, blueprint_path: Path,
                 max_skills: int = 3, lessons_path: Optional[Path] = None,
                 use_graph: bool = True) -> Optional[str]:
    """Check all three layers for matching triggers.

    Layer 1: Blueprint procedural skills (static, deterministic)
    Layer 2: Lesson-based triggers (dynamic, learned from experience)
    Layer 3: Graph-RAG associations (multi-hop reasoning)

    Returns combined injection text or None.
    """
    parts = []
    root = _resolve_root(blueprint_path)

    # Layer 1: Blueprint skills
    skills = load_procedural_skills(blueprint_path)
    matched_skills = match_skills(action_text, skills)
    skill_text = format_skill_injection(matched_skills, max_skills)
    if skill_text:
        parts.append(skill_text)

    # Layer 2: Lesson triggers
    if lessons_path is None:
        candidates = [
            root / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl",
            root / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "sessions" / "default" / "knowledge" / "lessons.jsonl",
        ]
        for c in candidates:
            if c.exists():
                lessons_path = c
                break

    if lessons_path and lessons_path.exists():
        triggered_lessons = load_lessons_with_triggers(lessons_path)
        matched_lessons = match_lessons(action_text, triggered_lessons)
        lesson_text = format_lesson_injection(matched_lessons)
        if lesson_text:
            parts.append(lesson_text)

    # Layer 3: Graph-RAG associations
    if use_graph:
        graph_path = root / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "action_graph.json"
        if graph_path.exists():
            from logic._.brain.utils.graph import ActionGraph
            graph = ActionGraph(graph_path)
            paths = graph.query(action_text, max_hops=3)
            graph_text = graph.format_paths(paths, max_paths=3)
            if graph_text:
                parts.append(graph_text)

    return "\n\n".join(parts) if parts else None
