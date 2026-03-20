"""Symmetric commands for managing README, for_agent, and report files.

Provides create/view/list operations for documentation at any level
of the project hierarchy (root logic, tool logic, provider level, etc.).
"""

import os
from datetime import date
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_target(scope: str) -> Path:
    """Resolve a scope string to a directory path.

    Scope examples:
      'root'                  -> <project_root>/report/
      'openclaw'              -> <project_root>/report/openclaw/
      'tool/LLM'              -> <project_root>/tool/LLM/
      '/absolute/path'        -> as-is
    """
    if scope == "root":
        return _ROOT / "report"
    if scope.startswith("/"):
        return Path(scope)
    candidate = _ROOT / scope
    if candidate.exists():
        return candidate
    report_candidate = _ROOT / "report" / scope
    if report_candidate.exists():
        return report_candidate
    return candidate


def _ensure_report_dir(target: Path) -> Path:
    report_dir = target / "report" if target.name != "report" else target
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def _resolve_report_dir(target: Path) -> Path:
    """Determine report dir: if target is inside report/ hierarchy, use it directly."""
    report_root = _ROOT / "report"
    try:
        target.relative_to(report_root)
        return target
    except ValueError:
        pass
    if target.name == "report":
        return target
    sub = target / "report"
    return sub if sub.exists() else target


def list_reports(scope: str = "root") -> list:
    target = _resolve_target(scope)
    report_dir = _resolve_report_dir(target)
    if not report_dir.exists():
        return []
    files = sorted(
        (f for f in report_dir.glob("*.md") if f.name != "README.md"),
        reverse=True,
    )
    return [{"name": f.stem, "path": str(f), "size": f.stat().st_size} for f in files]


def view_file(scope: str, filename: str) -> Optional[str]:
    """Read a specific file (README.md, AGENT.md, or report/xxx.md)."""
    target = _resolve_target(scope)
    if filename.startswith("report/"):
        path = target / filename
    else:
        path = target / filename
    if path.exists():
        return path.read_text()
    return None


def create_report(scope: str, topic: str, content: str) -> str:
    """Create a date-prefixed report file. Returns the path."""
    target = _resolve_target(scope)
    report_dir = _ensure_report_dir(target)
    today = date.today().isoformat()
    slug = topic.lower().replace(" ", "-").replace("/", "-")[:60]
    filename = f"{today}_{slug}.md"
    path = report_dir / filename
    path.write_text(content)
    return str(path)


def edit_doc(scope: str, filename: str, content: str) -> str:
    """Write or overwrite a documentation file (README.md, AGENT.md, etc.)."""
    target = _resolve_target(scope)
    path = target / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


def find_provider_dir(model_or_vendor: str) -> Optional[Path]:
    """Search for a provider directory by model name or vendor name."""
    models_dir = _ROOT / "tool" / "LLM" / "logic" / "models"
    if not models_dir.exists():
        return None
    for model_dir in models_dir.iterdir():
        if not model_dir.is_dir():
            continue
        providers = model_dir / "providers"
        if not providers.exists():
            continue
        for vendor_dir in providers.iterdir():
            if vendor_dir.is_dir() and model_or_vendor.lower() in vendor_dir.name.lower():
                return vendor_dir
        if model_or_vendor.lower() in model_dir.name.lower():
            for vendor_dir in providers.iterdir():
                if vendor_dir.is_dir():
                    return vendor_dir
    return None


def provider_report(model_or_vendor: str, topic: str, content: str) -> str:
    """Create a report in a provider's report directory."""
    pdir = find_provider_dir(model_or_vendor)
    if not pdir:
        raise FileNotFoundError(f"Provider directory not found for: {model_or_vendor}")
    return create_report(str(pdir), topic, content)


def list_docs(scope: str) -> dict:
    """List all documentation files at a scope level."""
    target = _resolve_target(scope)
    result = {
        "scope": scope,
        "path": str(target),
        "readme": None,
        "for_agent": None,
        "reports": [],
    }
    readme = target / "README.md"
    if readme.exists():
        result["readme"] = str(readme)
    for_agent = target / "AGENT.md"
    if for_agent.exists():
        result["for_agent"] = str(for_agent)
    result["reports"] = list_reports(scope)
    return result
