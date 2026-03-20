"""
Skills Marketplace — browse, search, and install skills from external sources.

Sources include the ClawHub registry (OpenClaw ecosystem) and curated
GitHub repositories. Downloaded skills are converted to our SKILL.md
format with YAML frontmatter and saved to the project's skills/ directory.
"""
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

CLAWHUB_API = "https://topclawhubskills.com/api"
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "skills"
MARKETPLACE_CACHE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "_" / "runtime" / "_" / "eco" / "experience" / "marketplace_cache.json"

SOURCES = [
    {
        "id": "clawhub",
        "name": "ClawHub (OpenClaw)",
        "type": "clawhub_api",
        "url": CLAWHUB_API,
        "description": "Official OpenClaw skill marketplace with 3000+ community skills.",
    },
    {
        "id": "openclaw-master",
        "name": "OpenClaw Master Skills",
        "type": "github_repo",
        "url": "https://api.github.com/repos/LeoYeAI/openclaw-master-skills/contents/skills",
        "description": "Curated weekly-updated collection of 127+ best OpenClaw skills.",
    },
]


def _http_get(url, timeout=15):
    """Make a GET request and return parsed JSON or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AITerminalTools-SKILLS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, Exception):
        return None


def _http_get_text(url, timeout=15):
    """Make a GET request and return raw text or None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AITerminalTools-SKILLS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def _http_get_bytes(url, timeout=30):
    """Make a GET request and return raw bytes or None. Falls back to curl."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AITerminalTools-SKILLS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        pass
    try:
        import subprocess
        result = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), "-o", "-", url],
            capture_output=True, timeout=timeout + 5,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception:
        pass
    return None


def _update_cache(data):
    """Write marketplace cache."""
    MARKETPLACE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(MARKETPLACE_CACHE, "w") as f:
        json.dump({"updated": datetime.now().isoformat(), "skills": data}, f, indent=2)


def _read_cache():
    """Read marketplace cache if recent (< 1 hour)."""
    if not MARKETPLACE_CACHE.exists():
        return None
    try:
        cache = json.loads(MARKETPLACE_CACHE.read_text())
        updated = datetime.fromisoformat(cache["updated"])
        if (datetime.now() - updated).total_seconds() < 3600:
            return cache.get("skills", [])
    except Exception:
        pass
    return None


def list_sources():
    """Return list of registered marketplace sources."""
    return SOURCES


def search_clawhub(query="", limit=20, endpoint="top-downloads"):
    """Search or browse ClawHub skills. Returns list of skill dicts."""
    if query:
        url = f"{CLAWHUB_API}/search?q={urllib.request.quote(query)}&limit={limit}"
    else:
        url = f"{CLAWHUB_API}/{endpoint}?limit={limit}"
    data = _http_get(url)
    if not data:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "data" in data:
            return data["data"] if isinstance(data["data"], list) else []
        if "skills" in data:
            return data["skills"] if isinstance(data["skills"], list) else []
    return []


def browse(source_id="clawhub", query="", limit=20, category="top-downloads"):
    """Browse skills from a source. Returns list of normalized skill dicts."""
    if source_id == "clawhub":
        raw = search_clawhub(query=query, limit=limit, endpoint=category)
        return [_normalize_clawhub(s) for s in (raw or [])]
    elif source_id == "openclaw-master":
        return _browse_github_repo(source_id)
    return []


def _normalize_clawhub(skill):
    """Normalize a ClawHub skill entry to a common format."""
    return {
        "source": "clawhub",
        "slug": skill.get("slug", ""),
        "name": skill.get("display_name", skill.get("slug", "unknown")),
        "description": skill.get("summary", ""),
        "downloads": skill.get("downloads", 0),
        "stars": skill.get("stars", 0),
        "owner": skill.get("owner_handle", ""),
        "certified": skill.get("is_certified", False),
        "url": skill.get("clawhub_url", ""),
        "updated": skill.get("updated_at", ""),
    }


def _browse_github_repo(source_id):
    """Browse skills from a GitHub repository."""
    source = next((s for s in SOURCES if s["id"] == source_id), None)
    if not source:
        return []
    data = _http_get(source["url"])
    if not data or not isinstance(data, list):
        return []
    skills = []
    for item in data:
        if item.get("type") == "dir":
            skills.append({
                "source": source_id,
                "slug": item["name"],
                "name": item["name"],
                "description": "",
                "downloads": 0,
                "stars": 0,
                "owner": source_id,
                "certified": False,
                "url": item.get("html_url", ""),
                "updated": "",
            })
    return skills


def fetch_skill_content(source_id, slug):
    """Fetch the full content of a skill from a source. Returns (content, metadata) or (None, error)."""
    if source_id == "clawhub":
        return _fetch_clawhub_skill(slug)
    elif source_id == "openclaw-master":
        return _fetch_github_skill(source_id, slug)
    return None, f"Unknown source: {source_id}"


def _fetch_clawhub_skill(slug):
    """Fetch a skill from ClawHub via their download API (returns zip).
    Returns (content_str, metadata_dict) or (None, error).
    """
    import zipfile
    import io
    url = f"https://clawhub.ai/api/v1/download?slug={slug}"
    data = _http_get_bytes(url)
    if not data:
        return None, f"Could not download skill '{slug}' from ClawHub."
    if data[:20].strip().startswith(b"Rate limit"):
        return None, f"Rate limited by ClawHub. Wait a minute and try again."
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        if "SKILL.md" in zf.namelist():
            content = zf.read("SKILL.md").decode("utf-8")
            extra_files = {n: zf.read(n) for n in zf.namelist() if n != "SKILL.md"}
            return content, {"source": "clawhub", "slug": slug, "extra_files": extra_files}
        for name in zf.namelist():
            if name.endswith(".md") and "SKILL" in name.upper():
                content = zf.read(name).decode("utf-8")
                return content, {"source": "clawhub", "slug": slug}
        return None, f"No SKILL.md found in downloaded zip for '{slug}'."
    except zipfile.BadZipFile:
        text_preview = data[:100].decode("utf-8", errors="replace").strip()
        return None, f"Invalid response for '{slug}': {text_preview}"


def _fetch_github_skill(source_id, slug):
    """Fetch a skill from a GitHub-based source."""
    source = next((s for s in SOURCES if s["id"] == source_id), None)
    if not source:
        return None, f"Source '{source_id}' not found."
    base = source["url"].replace("/contents/skills", "").replace("api.github.com/repos", "raw.githubusercontent.com").rstrip("/")
    for fname in ["SKILL.md", "instructions.md", "README.md"]:
        url = f"{base}/main/skills/{slug}/{fname}"
        content = _http_get_text(url)
        if content:
            return content, {"source": source_id, "slug": slug}
    return None, f"Could not fetch skill '{slug}' from {source_id}."


def convert_to_skill_md(content, slug, source_id, description=""):
    """Convert external skill content to our SKILL.md format with YAML frontmatter."""
    has_frontmatter = content.strip().startswith("---")
    if has_frontmatter:
        return content

    frontmatter = f"""---
name: {slug}
description: {description or f'Imported from {source_id}'}
source: {source_id}
imported: {datetime.now().strftime('%Y-%m-%d')}
---

"""
    return frontmatter + content


def install_skill(source_id, slug, target_dir=None, description=""):
    """Download and install a skill. Returns (success, message, path)."""
    if target_dir is None:
        target_dir = SKILLS_DIR / "marketplace" / source_id

    content, meta_or_error = fetch_skill_content(source_id, slug)
    if content is None:
        return False, meta_or_error, None

    skill_dir = Path(target_dir) / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"

    converted = convert_to_skill_md(content, slug, source_id, description)
    skill_file.write_text(converted)

    extra_files = meta_or_error.get("extra_files", {}) if isinstance(meta_or_error, dict) else {}
    saved_extras = 0
    for rel_path, file_bytes in extra_files.items():
        if rel_path.startswith("_meta") or rel_path.startswith("."):
            continue
        out = skill_dir / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(file_bytes)
        saved_extras += 1

    extra_msg = f" (+{saved_extras} extra files)" if saved_extras else ""
    return True, f"Installed '{slug}' from {source_id}{extra_msg}.", skill_file


def list_installed_marketplace_skills():
    """List skills installed from the marketplace."""
    market_dir = SKILLS_DIR / "marketplace"
    if not market_dir.exists():
        return []
    installed = []
    for skill_file in market_dir.rglob("SKILL.md"):
        skill_dir = skill_file.parent
        source = skill_dir.parent.name
        installed.append({
            "source": source,
            "slug": skill_dir.name,
            "path": str(skill_file),
        })
    return installed


def uninstall_skill(source_id, slug):
    """Remove an installed marketplace skill. Returns (success, message)."""
    import shutil
    skill_dir = SKILLS_DIR / "marketplace" / source_id / slug
    if not skill_dir.exists():
        return False, f"Skill '{slug}' from {source_id} not found."
    shutil.rmtree(skill_dir)
    return True, f"Removed '{slug}' from {source_id}."
