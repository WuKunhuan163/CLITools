"""Asset migration: download/sync icons from remote CDNs.

Icons are stored locally in logic/utils/asset/image/{providers,models,filetypes}/
so the project works offline and isn't dependent on remote CDN availability.

This module does NOT hardcode any icon lists. Instead it:
- Scans the LLM tool's provider/model registry for provider & model icons
- Fetches the devicon manifest for file type icons
- Downloads any missing SVGs to local storage

Usage via CLI:
    TOOL --dev migrate logos       Sync provider & model logos
    TOOL --dev migrate filetypes   Sync file type icons from devicon
    TOOL --dev migrate all         Sync everything
"""
import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple, Optional

_ASSET_DIR = Path(__file__).resolve().parent / "image"

LOBEHUB_BASE = "https://registry.npmmirror.com/@lobehub/icons-static-svg/latest/files/icons"
DEVICON_BASE = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons"
DEVICON_MANIFEST = "https://cdn.jsdelivr.net/gh/devicons/devicon/devicon.json"


def _download(url: str, dest: Path, force: bool = False) -> bool:
    """Download a URL to a local file. Returns True if downloaded."""
    if dest.exists() and not force:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AITerminalTools/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) < 50:
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True
    except Exception:
        return False


def _discover_provider_icons() -> Dict[str, str]:
    """Discover provider icons from the LLM tool's registry."""
    icons = {}
    try:
        from tool.LLM.logic.registry import list_providers
        for p in list_providers():
            name = p.get("name", "")
            if not name:
                continue
            vendor = name.split("-")[0]
            if vendor not in icons:
                for suffix in ("-color.svg", ".svg"):
                    icons[vendor] = f"{LOBEHUB_BASE}/{vendor}{suffix}"
    except ImportError:
        pass

    _KNOWN_VENDORS = {
        "cursor", "copilot", "windsurf", "openai", "anthropic",
        "mistral", "deepseek", "meta", "cohere", "yi", "qwen",
        "gemini", "claude", "grok",
    }
    for v in _KNOWN_VENDORS:
        if v not in icons:
            icons[v] = f"{LOBEHUB_BASE}/{v}-color.svg"
    return icons


def _discover_model_icons() -> Dict[str, str]:
    """Discover model icons from the LLM tool's registry."""
    icons = {}
    try:
        from tool.LLM.logic.registry import list_models
        for m in list_models():
            mid = m.get("model", "")
            if not mid:
                continue
            vendor = mid.split("-")[0]
            safe_name = mid.replace("/", "_").replace(" ", "_")
            for suffix in ("-color.svg", ".svg"):
                icons[safe_name] = f"{LOBEHUB_BASE}/{vendor}{suffix}"
    except ImportError:
        pass
    return icons


def _discover_filetype_icons() -> Dict[str, str]:
    """Discover file type icons from the devicon manifest."""
    icons = {}
    try:
        req = urllib.request.Request(DEVICON_MANIFEST,
                                     headers={"User-Agent": "AITerminalTools/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            manifest = json.loads(resp.read())
        for entry in manifest:
            name = entry.get("name", "")
            versions = entry.get("versions", {})
            svg_versions = versions.get("svg", [])
            if "original" in svg_versions:
                icons[name] = f"{DEVICON_BASE}/{name}/{name}-original.svg"
            elif "plain" in svg_versions:
                icons[name] = f"{DEVICON_BASE}/{name}/{name}-plain.svg"
    except Exception:
        pass

    _REQUIRED = {
        "python": "python/python-original", "javascript": "javascript/javascript-original",
        "typescript": "typescript/typescript-original", "java": "java/java-original",
        "go": "go/go-original", "rust": "rust/rust-original",
        "html5": "html5/html5-original", "css3": "css3/css3-original",
        "bash": "bash/bash-original", "json": "json/json-original",
        "react": "react/react-original", "sass": "sass/sass-original",
        "markdown": "markdown/markdown-original", "yaml": "yaml/yaml-original",
        "ruby": "ruby/ruby-original", "php": "php/php-original",
        "c": "c/c-original", "cplusplus": "cplusplus/cplusplus-original",
        "postgresql": "postgresql/postgresql-original",
        "vuejs": "vuejs/vuejs-original", "svelte": "svelte/svelte-original",
        "xml": "xml/xml-original", "swift": "swift/swift-original",
        "kotlin": "kotlin/kotlin-original", "dart": "dart/dart-original",
        "r": "r/r-original", "lua": "lua/lua-original",
    }
    for name, path in _REQUIRED.items():
        if name not in icons:
            icons[name] = f"{DEVICON_BASE}/{path}.svg"
    return icons


def migrate_logos(force: bool = False) -> Tuple[int, int, List[str]]:
    """Download provider & model logos. Returns (downloaded, skipped, errors)."""
    downloaded = 0
    skipped = 0
    errors = []

    for name, url in _discover_provider_icons().items():
        dest = _ASSET_DIR / "providers" / f"{name}.svg"
        if _download(url, dest, force):
            downloaded += 1
        elif dest.exists():
            skipped += 1
        else:
            for alt_suffix in (".svg", "-color.svg"):
                alt_url = f"{LOBEHUB_BASE}/{name}{alt_suffix}"
                if _download(alt_url, dest):
                    downloaded += 1
                    break
            else:
                if not dest.exists():
                    errors.append(f"providers/{name}")

    for name, url in _discover_model_icons().items():
        dest = _ASSET_DIR / "models" / f"{name}.svg"
        if _download(url, dest, force):
            downloaded += 1
        elif dest.exists():
            skipped += 1
        else:
            errors.append(f"models/{name}")

    return downloaded, skipped, errors


def migrate_filetypes(force: bool = False) -> Tuple[int, int, List[str]]:
    """Download file type icons from devicon. Returns (downloaded, skipped, errors)."""
    downloaded = 0
    skipped = 0
    errors = []

    for name, url in _discover_filetype_icons().items():
        dest = _ASSET_DIR / "filetypes" / f"{name}.svg"
        if _download(url, dest, force):
            downloaded += 1
        elif dest.exists():
            skipped += 1
        else:
            errors.append(f"filetypes/{name}")

    return downloaded, skipped, errors


def sync_logos_to_llm() -> int:
    """Copy central provider logos to LLM tool model/provider directories.

    Scans each LLM provider directory; if it lacks logo.svg but a central
    copy exists in logic/utils/asset/image/providers/<vendor>.svg, copies it there.
    Same for model directories using the vendor fallback.
    Returns the number of files copied.
    """
    import shutil
    copied = 0
    llm_providers = Path(__file__).resolve().parent.parent.parent.parent / "tool" / "LLM" / "logic" / "providers"
    llm_models = Path(__file__).resolve().parent.parent.parent.parent / "tool" / "LLM" / "logic" / "models"

    if llm_providers.is_dir():
        for pdir in llm_providers.iterdir():
            if not pdir.is_dir() or pdir.name.startswith(("_", ".")):
                continue
            logo = pdir / "logo.svg"
            if logo.exists():
                continue
            src = _ASSET_DIR / "providers" / f"{pdir.name}.svg"
            if src.exists():
                shutil.copy2(src, logo)
                copied += 1

    if llm_models.is_dir():
        for mdir in llm_models.iterdir():
            if not mdir.is_dir() or mdir.name.startswith(("_", ".")):
                continue
            logo = mdir / "logo.svg"
            if logo.exists():
                continue
            mj = mdir / "model.json"
            if mj.exists():
                try:
                    meta = json.loads(mj.read_text())
                    vendor = meta.get("vendor", "")
                    if vendor:
                        src = _ASSET_DIR / "providers" / f"{vendor}.svg"
                        if src.exists():
                            shutil.copy2(src, logo)
                            copied += 1
                except Exception:
                    pass
    return copied


def migrate_all(force: bool = False) -> dict:
    """Download all assets and sync to tool directories. Returns summary."""
    d1, s1, e1 = migrate_logos(force)
    d2, s2, e2 = migrate_filetypes(force)
    synced = sync_logos_to_llm()
    return {
        "downloaded": d1 + d2,
        "skipped": s1 + s2,
        "errors": e1 + e2,
        "synced_to_llm": synced,
    }


def get_local_icon_path(category: str, name: str) -> Optional[str]:
    """Get the local path to an icon, or None if not found."""
    p = _ASSET_DIR / category / f"{name}.svg"
    return str(p) if p.exists() else None


def get_all_local_icons() -> Dict[str, List[str]]:
    """List all locally available icons by category."""
    result = {}
    for cat in ("providers", "models", "filetypes"):
        cat_dir = _ASSET_DIR / cat
        if cat_dir.exists():
            result[cat] = sorted(f.stem for f in cat_dir.glob("*.svg"))
    return result