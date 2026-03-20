"""Brain interface: pluggable agent memory system.

Provides access to the three-tier brain (working/knowledge/episodic)
through the configured backend. Import from here, not from logic._.brain.

Usage:
    from interface.brain import get_brain, load_blueprint, get_guidance_doc

    brain = get_brain()
    brain.store("working", "context", "# Current state...")
    brain.search("provider bug", tier="knowledge")
    brain.append("knowledge", "lessons", {"lesson": "...", "tool": "LLM"})
"""
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent


def load_blueprint(root: Optional[Path] = None, merge_base: bool = True):
    """Load the active brain blueprint, merged with base ecosystem rules."""
    from logic._.brain.loader import load_blueprint as _load
    return _load(root or _ROOT, merge_base=merge_base)


def load_base(root: Optional[Path] = None):
    """Load the shared base ecosystem rules (logic/_/brain/blueprint/base.json)."""
    from logic._.brain.loader import load_base as _load_base
    return _load_base(root or _ROOT)


def list_blueprints() -> List[Dict]:
    """List all available brain blueprint definitions."""
    from logic._.brain.loader import list_blueprints as _list
    return _list()


def resolve_blueprint(name: str) -> Optional[Path]:
    """Resolve a blueprint name to its directory path."""
    from logic._.brain.loader import resolve_blueprint as _resolve
    return _resolve(name)


def get_brain(root: Optional[Path] = None):
    """Get the configured brain backend instance."""
    from logic._.brain.loader import create_backend
    return create_backend(root or _ROOT)


def get_guidance_doc(doc_key: str, root: Optional[Path] = None):
    """Get the path to a guidance document from the blueprint."""
    from logic._.brain.loader import get_guidance_doc as _get
    return _get(root or _ROOT, doc_key)


def get_session_manager(root: Optional[Path] = None):
    """Get the brain instance (session) manager."""
    from logic._.brain.instance import BrainSessionManager
    return BrainSessionManager(root or _ROOT)


def audit_blueprint(name: str) -> Dict:
    """Audit a blueprint for potential issues (path errors, missing fields)."""
    from logic._.brain.utils.audit import audit_blueprint as _audit
    return _audit(name)


def check_procedural_triggers(action_text: str, blueprint_name: Optional[str] = None,
                               root: Optional[Path] = None,
                               lessons_path: Optional[Path] = None) -> Optional[str]:
    """Check if an agent action triggers any procedural reflex arcs.

    Returns injection-ready text if triggers matched, None otherwise.
    Useful in postToolUse hooks to inject relevant procedures before the
    agent continues.
    """
    from logic._.brain.utils.procedural import check_action
    r = root or _ROOT
    if blueprint_name:
        bp_path = r / "logic" / "brain" / "blueprint" / blueprint_name / "blueprint.json"
    else:
        bp_path = r / "logic" / "brain" / "blueprint" / "openclaw-20260316" / "blueprint.json"
    if not bp_path.exists():
        return None
    return check_action(action_text, bp_path, lessons_path=lessons_path)


def build_action_graph(root: Optional[Path] = None):
    """Build/rebuild the ecosystem action-consequence graph.

    Pre-seeds the graph with known action→system→file associations
    for multi-hop reflex arc reasoning.
    """
    from logic._.brain.utils.graph import build_ecosystem_graph
    return build_ecosystem_graph(root or _ROOT)


def upgrade_lesson_to_trigger(lesson_index: int, patterns: List[str],
                               lessons_path: Optional[Path] = None) -> bool:
    """Upgrade a passive lesson to an active reflex arc by adding trigger patterns.

    This enables the lesson to automatically surface when the agent performs
    an action matching one of the patterns.

    Args:
        lesson_index: 0-based line index in lessons.jsonl
        patterns: Regex patterns that should activate this lesson
        lessons_path: Path to lessons.jsonl (auto-resolved if None)
    """
    from logic._.brain.utils.procedural import add_trigger_patterns
    if lessons_path is None:
        candidates = [
            _ROOT / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "sessions" / "default" / "knowledge" / "lessons.jsonl",
            _ROOT / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "lessons.jsonl",
        ]
        for c in candidates:
            if c.exists():
                lessons_path = c
                break
    if lessons_path is None:
        return False
    return add_trigger_patterns(lessons_path, lesson_index, patterns)


__all__ = [
    "load_blueprint",
    "load_base",
    "list_blueprints",
    "resolve_blueprint",
    "get_brain",
    "get_guidance_doc",
    "get_session_manager",
    "audit_blueprint",
    "check_procedural_triggers",
    "upgrade_lesson_to_trigger",
    "build_action_graph",
]
