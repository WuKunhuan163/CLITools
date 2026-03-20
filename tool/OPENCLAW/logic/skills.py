"""Active skill chaining for OPENCLAW.

Maps runtime situations (errors, command types, context patterns) to
relevant skills, reads them, and returns content for injection into the
agent's feedback loop.  This turns passive skill listing into active
skill triggering.
"""
import re
from pathlib import Path
from typing import List, Optional

_OPENCLAW_SKILLS = Path(__file__).resolve().parent.parent / "skills"
_PROJECT_SKILLS = Path(__file__).resolve().parent.parent.parent.parent / "skills" / "core"

_TRIGGER_MAP = [
    # (pattern applied to error/context, skill name, skill root)
    (r"(?i)(retry|timeout|rate.?limit|transient|backoff)", "error-recovery-patterns", _OPENCLAW_SKILLS),
    (r"(?i)(not recognized|unknown command|not permitted|not allowed)", "naming-conventions", _PROJECT_SKILLS),
    (r"(?i)(hyphen|underscore|kebab.?case|snake.?case|naming)", "naming-conventions", _PROJECT_SKILLS),
    (r"(?i)(tool-help|for_agent|how to use)", "task-orchestration", _OPENCLAW_SKILLS),
    (r"(?i)(memory|lesson|experience|learn)", "memory-recall", _OPENCLAW_SKILLS),
    (r"(?i)(prerequisite|before.+start|preflight|validate)", "preflight-checks", _OPENCLAW_SKILLS),
    (r"(?i)(recipe|workflow|end.?to.?end|compose)", "recipes", _OPENCLAW_SKILLS),
    (r"(?i)(formul|when.+skill|when.+tool|create.+skill)", "formulation-guide", _OPENCLAW_SKILLS),
    (r"(?i)(chrome|browser|cdp|tab|navigate|google)", "cdmcp-web-exploration", _PROJECT_SKILLS),
    (r"(?i)(cache|rotation|log.?limit|retention|prune|evict)", "retention-rotation", _PROJECT_SKILLS),
]

_SKILL_CACHE: dict = {}


def _read_skill(name: str, root: Path) -> Optional[str]:
    """Read and cache a skill file."""
    key = f"{root}/{name}"
    if key in _SKILL_CACHE:
        return _SKILL_CACHE[key]
    path = root / name / "SKILL.md"
    if not path.exists():
        _SKILL_CACHE[key] = None
        return None
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 4000:
            content = content[:4000] + "\n... [truncated]"
        _SKILL_CACHE[key] = content
        return content
    except Exception:
        _SKILL_CACHE[key] = None
        return None


def resolve_skills(context: str, max_skills: int = 2) -> List[str]:
    """Given an error message or context string, return relevant skill contents.

    Returns at most *max_skills* skill bodies, deduplicated, in priority order.
    """
    found: List[str] = []
    seen_names: set = set()
    for pattern, skill_name, skill_root in _TRIGGER_MAP:
        if skill_name in seen_names:
            continue
        if re.search(pattern, context):
            body = _read_skill(skill_name, skill_root)
            if body:
                found.append(f"[Skill: {skill_name}]\n{body}")
                seen_names.add(skill_name)
                if len(found) >= max_skills:
                    break
    return found


def build_skill_hint(context: str) -> str:
    """Build a compact skill hint string for injection into feedback.

    Returns empty string if no skills match.
    """
    skills = resolve_skills(context)
    if not skills:
        return ""
    header = (
        "\n\n--- Relevant Skills (auto-loaded) ---\n"
        "Read these carefully before your next action.\n\n"
    )
    return header + "\n\n---\n\n".join(skills)
