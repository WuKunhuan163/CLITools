"""Brain blueprint loader and validator.

Blueprint definitions live in logic/_/brain/blueprint/ (versioned packages).
The active instance config is data/_/runtime/_/eco/brain/blueprint.json.

To add a new brain blueprint:
1. Create logic/_/brain/blueprint/<name>-<YYYYMMDD>/blueprint.json
2. Implement any new backends in logic/_/brain/backends/
3. Register backends in BACKEND_REGISTRY below
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from logic._.brain.base import BrainBackend

BACKEND_REGISTRY = {
    "flatfile": "logic._.brain.backends.flatfile.FlatFileBrainBackend",
}

_BLUEPRINT_PKG = Path(__file__).resolve().parent / "blueprint"


def blueprints_dir() -> Path:
    """Return the directory containing blueprint definitions."""
    return _BLUEPRINT_PKG


def load_base(root: Optional[Path] = None) -> Dict:
    """Load the shared base rules from logic/_/brain/blueprint/base.json."""
    base_path = _BLUEPRINT_PKG / "base.json"
    if not base_path.exists():
        return {}
    with open(base_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_blueprints() -> List[Dict]:
    """List all available blueprint definitions."""
    results = []
    if not _BLUEPRINT_PKG.exists():
        return results
    for d in sorted(_BLUEPRINT_PKG.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        bp_file = d / "blueprint.json"
        info = {"name": d.name, "path": str(d)}
        if bp_file.exists():
            try:
                bp = json.loads(bp_file.read_text(encoding="utf-8"))
                info["description"] = bp.get("description", "")
                info["version"] = bp.get("version", "")
                info["inherits"] = bp.get("inherits", "")
            except Exception:
                pass
        readme = d / "README.md"
        if readme.exists():
            info["has_readme"] = True
        results.append(info)
    return results


def resolve_blueprint(name: str) -> Optional[Path]:
    """Resolve a blueprint name to its directory path."""
    bp_dir = _BLUEPRINT_PKG / name
    if bp_dir.is_dir() and (bp_dir / "blueprint.json").exists():
        return bp_dir
    return None


def load_blueprint_type(name: str) -> Dict:
    """Load a specific blueprint type definition by name."""
    bp_dir = resolve_blueprint(name)
    if bp_dir is None:
        available = [d.name for d in _BLUEPRINT_PKG.iterdir() if d.is_dir() and not d.name.startswith("_")]
        raise FileNotFoundError(f"Blueprint '{name}' not found. Available: {', '.join(available)}")
    with open(bp_dir / "blueprint.json", "r", encoding="utf-8") as f:
        bp = json.load(f)
    base = load_base()
    if base and bp.get("inherits") == "base":
        bp = _merge_base(base, bp)
    return bp


def load_blueprint(root: Path, merge_base: bool = True) -> Dict:
    """Load the active brain blueprint from data/_/runtime/_/eco/brain/blueprint.json.

    If merge_base is True, the base.json ecosystem rules are merged in
    (blueprint values take precedence for overlapping keys).
    """
    bp_path = root / "data" / "_" / "runtime" / "_" / "eco" / "brain" / "blueprint.json"
    if not bp_path.exists():
        bp = _default_blueprint()
    else:
        with open(bp_path, "r", encoding="utf-8") as f:
            bp = json.load(f)

    if merge_base:
        base = load_base(root)
        if base:
            bp = _merge_base(base, bp)
    return bp


def _merge_base(base: Dict, blueprint: Dict) -> Dict:
    """Merge base ecosystem rules into a brain-type-specific blueprint.

    Blueprint values take precedence. Base provides defaults for keys
    not present in the blueprint (guidance, hooks, directory_conventions, etc.).
    """
    merged = dict(base)
    for key, value in blueprint.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _default_blueprint() -> Dict:
    """Fallback blueprint when no blueprint.json exists."""
    return {
        "name": "default",
        "version": "1.0",
        "tiers": {
            "working": {"backend": "flatfile", "path": "data/_/runtime/_/eco/brain/"},
            "knowledge": {"backend": "flatfile", "path": "data/_/runtime/_/eco/experience/"},
            "episodic": {"backend": "flatfile", "path": "data/_/runtime/_/eco/experience/default/"},
        },
        "guidance": {
            "bootstrap": "AGENT.md",
            "reflection": "skills/_/meta-agent/SKILL.md",
        },
    }


def create_backend(root: Path, blueprint: Optional[Dict] = None) -> BrainBackend:
    """Instantiate the brain backend from the blueprint.

    Currently all tiers use the same backend. Future: per-tier backends.
    """
    if blueprint is None:
        blueprint = load_blueprint(root)

    backend_name = "flatfile"
    for tier_config in blueprint.get("tiers", {}).values():
        backend_name = tier_config.get("backend", "flatfile")
        break

    backend_path = BACKEND_REGISTRY.get(backend_name)
    if not backend_path:
        raise ValueError(f"Unknown brain backend: {backend_name}. Available: {list(BACKEND_REGISTRY.keys())}")

    module_path, class_name = backend_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(root, blueprint)


def get_guidance_doc(root: Path, doc_key: str, blueprint: Optional[Dict] = None) -> Optional[Path]:
    """Get the path to a guidance document from the blueprint."""
    if blueprint is None:
        blueprint = load_blueprint(root)
    guidance = blueprint.get("guidance", {})
    filename = guidance.get(doc_key)
    if not filename:
        return None
    path = root / filename
    return path if path.exists() else None
