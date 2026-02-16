import os
import re
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# Import shared utilities
try:
    from logic.utils import get_system_tag, regularize_version_name, truncate_to_display_width
    from logic.turing.models.progress import ProgressTuringMachine, TuringStage
    from logic.audit.utils import AuditManager
    from tool.PYTHON.logic.config import DATA_DIR, AUDIT_DIR, PROJECT_ROOT
except ImportError:
    # Basic fallbacks for standalone usage/testing
    def get_system_tag(): return "unknown"
    def regularize_version_name(v, p): return f"{v}-{p}"
    def truncate_to_display_width(text, max_width): return text[:max_width]
    
    class AuditManager:
        def __init__(self, *args, **kwargs): pass
        def print_cache_warning(self, *args, **kwargs): pass
        
    class ProgressTuringMachine:
        def __init__(self, *args, **kwargs): pass
        def add_stage(self, *args, **kwargs): pass
        def run(self, *args, **kwargs): return True
        
    class TuringStage:
        def __init__(self, *args, **kwargs): 
            self.active_name = ""
        def refresh(self, *args, **kwargs): pass

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "tool" / "PYTHON" / "data"
    AUDIT_DIR = DATA_DIR / "audit"

# Configuration
PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
PROJECT_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}"
REPO_URL = f"{PROJECT_URL}.git"
RELEASE_ASSET_CACHE = DATA_DIR / "release_asset.json"

class PythonScanner:
    def __init__(self, force=False, silent=False):
        self.force = force
        self.silent = silent
        self.audit = AuditManager(AUDIT_DIR, component_name="PYTHON_SCANNER")
        self.asset_cache_dir = AUDIT_DIR / "assets"
        self.asset_cache_dir.mkdir(parents=True, exist_ok=True)
        self._warning_printed = False

    def print_cache_warning_once(self):
        if not self._warning_printed and not self.silent:
            self.audit.print_cache_warning()
            self._warning_printed = True

    def resolve_platform(self, asset_name: str) -> Optional[str]:
        mappings = {
            "macos-arm64": ["aarch64-apple-darwin", "macos-aarch64", "macos-arm64"],
            "macos": ["x86_64-apple-darwin", "macos-x86_64", "macosx", "macos"],
            "linux64-musl": ["x86_64-unknown-linux-musl", "linux-musl"],
            "linux64": ["x86_64-unknown-linux-gnu", "linux64", "linux-x86_64"],
            "windows-amd64": ["x86_64-pc-windows-msvc", "windows-x86_64", "win64"],
            "windows-x86": ["i686-pc-windows-msvc", "windows-i686", "win32"],
            "windows-arm64": ["aarch64-pc-windows-msvc", "windows-aarch64"],
        }
        if "linux-musl" in asset_name or "unknown-linux-musl" in asset_name:
            return "linux64-musl"
        for platform, keys in mappings.items():
            if any(key in asset_name for key in keys):
                return platform
        return None

    def get_release_tags(self) -> List[str]:
        """Fetches release tags from GitHub using git ls-remote."""
        cmd = ["/usr/bin/git", "ls-remote", "--tags", REPO_URL]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return []
        tags = []
        for line in result.stdout.strip().split("\n"):
            match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
            if match:
                tags.append(match.group(1))
        return sorted(list(set(tags)), reverse=True)

    def fetch_assets_for_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Fetches assets for a specific tag, using cache if available."""
        cache_path = self.asset_cache_dir / f"assets_{tag}.json"
        if not self.force and cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    cache = json.load(f)
                if "assets" in cache:
                    self.print_cache_warning_once()
                    return cache["assets"]
            except: pass

        # Fetch from GitHub API
        api_url = f"https://api.github.com/repos/{PROJECT_OWNER}/{PROJECT_NAME}/releases/tags/{tag}"
        cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", api_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assets = []
        try:
            data = json.loads(result.stdout)
            if "assets" in data:
                for item in data["assets"]:
                    name = item["name"]
                    if not name.endswith(".tar.zst") or name.endswith(".sha256"): continue
                    
                    v_match = re.search(r"(\d+\.\d+\.\d+)", name)
                    if not v_match: continue
                    
                    full_v = v_match.group(1)
                    platform = self.resolve_platform(name)
                    if platform:
                        assets.append({
                            "name": name,
                            "url": item["browser_download_url"],
                            "version": full_v,
                            "platform": platform,
                            "tag": tag
                        })
            else:
                raise ValueError("No assets in API response")
        except:
            # Fallback to scraping
            url = f"{PROJECT_URL}/releases/expanded_assets/{tag}"
            cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            matches = re.findall(r'cpython-([\w\+\-\.]+)\.tar\.zst', result.stdout)
            for name_core in set(matches):
                name = f"cpython-{name_core}.tar.zst"
                v_match = re.search(r"(\d+\.\d+\.\d+)", name)
                if not v_match: continue
                full_v = v_match.group(1)
                platform = self.resolve_platform(name)
                if platform:
                    assets.append({
                        "name": name,
                        "url": f"{PROJECT_URL}/releases/download/{tag}/{name}",
                        "version": full_v,
                        "platform": platform,
                        "tag": tag
                    })
            
        # Save to cache
        with open(cache_path, "w") as f:
            json.dump({"assets": assets, "timestamp": datetime.now().isoformat()}, f, indent=2)
        
        return assets

    def scan_all(self, limit_releases: Optional[int] = None) -> Dict[str, Any]:
        """Scans all releases and builds a comprehensive matrix."""
        tags = self.get_release_tags()
        if limit_releases:
            tags = tags[:limit_releases]
        
        matrix = {}
        start_time = time.time()

        def scan_action(stage: TuringStage):
            for i, tag in enumerate(tags):
                elapsed = int(time.time() - start_time)
                stage.active_name = f"from GitHub ({tag}) (found: {len(matrix)})({elapsed}s)"
                stage.refresh()
                
                assets = self.fetch_assets_for_tag(tag)
                for a in assets:
                    v_tag = regularize_version_name(a['version'], a['platform'])
                    if v_tag not in matrix: matrix[v_tag] = {}
                    matrix[v_tag][tag] = a["url"]
            return True

        if not self.silent:
            tm = ProgressTuringMachine(project_root=PROJECT_ROOT, tool_name="PYTHON")
            tm.add_stage(TuringStage(
                name="GitHub releases",
                action=scan_action,
                active_status="Scanning",
                success_status="Successfully fetched",
                success_name="GitHub releases",
                fail_status="Failed to fetch",
                bold_part="GitHub releases"
            ))
            if not tm.run(ephemeral=True, final_newline=False):
                sys.exit(1)
        else:
            scan_action(None)

        return self.finalize_matrix(matrix)

    def finalize_matrix(self, matrix: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """Calculates 'latest' fields and sorts the matrix."""
        def version_key(v_str):
            v_num = re.search(r"(\d+\.\d+\.\d+)", v_str)
            if v_num: return [int(x) for x in v_num.group(1).split(".")]
            v_min = re.search(r"(\d+\.\d+)", v_str)
            if v_min: return [int(x) for x in v_min.group(1).split(".")] + [0]
            return [0, 0, 0]

        sorted_v_tags = sorted(matrix.keys(), key=version_key, reverse=True)
        
        by_version_latest = {}
        by_platform_latest = {}
        
        for v_tag in sorted_v_tags:
            # Add namespaced _latest
            latest_tag = sorted(list(matrix[v_tag].keys()))[-1]
            namespaced_v = f"{latest_tag}:{v_tag}"
            matrix[v_tag]["_latest"] = namespaced_v
            
            # Platform/Version grouping
            v_match = re.match(r"(\d+\.\d+)", v_tag)
            major_minor = v_match.group(1) if v_match else "unknown"
            platform_match = re.search(r"-([a-z0-9\-]+)$", v_tag)
            platform_name = platform_match.group(1) if platform_match else "unknown"
            
            if major_minor not in by_version_latest: by_version_latest[major_minor] = namespaced_v
            if platform_name not in by_platform_latest: by_platform_latest[platform_name] = namespaced_v

        report = {
            "timestamp": datetime.now().isoformat(),
            "full": matrix,
            "by_version_latest": by_version_latest,
            "by_platform_latest": by_platform_latest
        }
        
        with open(RELEASE_ASSET_CACHE, "w") as f:
            json.dump(report, f, indent=2)
            
        return report

    def load_cache(self) -> Dict[str, Any]:
        if RELEASE_ASSET_CACHE.exists():
            try:
                with open(RELEASE_ASSET_CACHE, "r") as f:
                    return json.load(f)
            except: pass
        return {}

    def get_filtered_assets(self, tag_filter=None, version_filter=None, platform_filter=None) -> List[Dict[str, Any]]:
        """Loads cache and applies filters."""
        data = self.load_cache()
        if not data and not self.silent:
            print(f"Cache missing. Running full scan...")
            data = self.scan_all()
        
        full_matrix = data.get("full", {})
        all_assets = []
        
        for v_tag, tag_dict in full_matrix.items():
            # Apply version filter
            if version_filter and not (v_tag == version_filter or v_tag.startswith(version_filter)):
                continue
            
            # Apply platform filter
            platform = self.resolve_platform(v_tag)
            if platform_filter and platform != platform_filter:
                continue
            
            for tag, url in tag_dict.items():
                if tag == "_latest": continue
                # Apply tag filter
                if tag_filter and tag != tag_filter:
                    continue
                
                v_match = re.search(r"(\d+\.\d+\.\d+)", v_tag)
                full_v = v_match.group(1) if v_match else "unknown"
                minor_v = ".".join(full_v.split(".")[:2]) if v_match else "unknown"
                patch_str = full_v.split(".")[2] if v_match else "0"
                try: patch = int(patch_str)
                except: patch = 0
                
                all_assets.append({
                    "name": url.split("/")[-1],
                    "url": url,
                    "version": full_v,
                    "v_tag": v_tag,
                    "minor": minor_v,
                    "patch": patch,
                    "platform": platform or "unknown",
                    "tag": tag
                })
        return all_assets

