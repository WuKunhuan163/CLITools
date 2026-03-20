"""Guideline composition engine — merge base + layer guidelines.

Each guideline module (base/conventions.py, base/ecosystem.py, layers/openclaw.py)
exports a get_guidelines() function returning:

    {
        "conventions": {
            "development": ["guideline 1", "guideline 2"],
            "quality": ["guideline 3"],
            ...
        },
        "ecosystem": {
            "architecture": ["guideline 4"],
            "tools": ["guideline 5"],
            ...
        }
    }

The engine merges these by appending list values under each key.
"""
import importlib
from typing import Dict, List, Optional


GuidelineDict = Dict[str, Dict[str, List[str]]]


def _empty_guidelines() -> GuidelineDict:
    return {"conventions": {}, "ecosystem": {}}


def _merge(target: GuidelineDict, source: GuidelineDict):
    """Merge source into target by appending lists under each category/key."""
    for category in ("conventions", "ecosystem"):
        src_cat = source.get(category, {})
        tgt_cat = target.setdefault(category, {})
        for key, items in src_cat.items():
            tgt_cat.setdefault(key, []).extend(items)


def compose_guidelines(
    layers: Optional[List[str]] = None,
    project_root: Optional[str] = None,
) -> GuidelineDict:
    """Compose guidelines from base + specified layers.

    Args:
        layers: Layer names to stack on top of base (e.g. ["openclaw"]).
                None means base only.
        project_root: Project root path (for tool-specific brain loading).

    Returns:
        Merged guidelines dict with 'conventions' and 'ecosystem' categories.
    """
    result = _empty_guidelines()

    for base_module in ("conventions", "ecosystem"):
        try:
            mod = importlib.import_module(
                f"logic.agent.guidelines.base.{base_module}")
            _merge(result, mod.get_guidelines())
        except (ImportError, AttributeError):
            pass

    for layer_name in (layers or []):
        try:
            mod = importlib.import_module(
                f"logic.agent.guidelines.layers.{layer_name}")
            _merge(result, mod.get_guidelines())
        except (ImportError, AttributeError):
            pass

    return result


def format_guidelines(guidelines: GuidelineDict) -> str:
    """Format guidelines as readable text for injection into agent context."""
    parts = []
    for category, sections in guidelines.items():
        if not sections:
            continue
        parts.append(f"### {category.title()}")
        for section_name, items in sections.items():
            parts.append(f"**{section_name.replace('_', ' ').title()}**")
            for item in items:
                parts.append(f"- {item}")
        parts.append("")
    return "\n".join(parts)
