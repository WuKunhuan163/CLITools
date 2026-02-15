import os
import re
import json
import subprocess
import argparse
import sys
import shutil
import hashlib
import threading
import random
import string
import time
from pathlib import Path
from datetime import datetime
from queue import Queue

# Configuration
PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
PROJECT_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}"
REPO_URL = f"{PROJECT_URL}.git"

# Import shared utilities for translation and config
try:
    # Add project root to sys.path with HIGHEST priority to avoid 'logic' collision
    tool_core_dir = Path(__file__).resolve().parent
    python_tool_dir = tool_core_dir.parent
    project_root = python_tool_dir.parent.parent
    
    # Ensure root project is at index 0
    if str(project_root) in sys.path:
        sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))
    
    # Tool-specific logic at index 1
    if str(python_tool_dir) in sys.path:
        sys.path.remove(str(python_tool_dir))
    sys.path.insert(1, str(python_tool_dir))
    
    from logic.lang.utils import get_translation
    from logic.config import get_color
    from logic.utils import get_system_tag, regularize_version_name, run_with_progress, truncate_to_display_width
    from logic.worker import TuringWorker
    from logic.turing.logic import TuringTask, StepResult, WorkerState
    from logic.turing.display.manager import MultiLineManager
    from logic.audit.utils import AuditManager
    
    from tool.PYTHON.logic.config import DATA_DIR, AUDIT_DIR, RESOURCE_ROOT, TMP_INSTALL_DIR, PROJECT_ROOT, DEFAULT_CONCURRENCY
except ImportError as e:
    # Basic fallbacks
    def get_translation(dir, key, default): return default
    def get_color(name, default="\033[0m"): return default
    def get_system_tag(): return "unknown"
    def regularize_version_name(v, p): return f"{v}-{p}"
    def truncate_to_display_width(text, max_width): return text[:max_width]
    def run_with_progress(cmd, pref, **kwargs): return subprocess.run(cmd).returncode == 0
    class MultiLineManager:
        def update(self, w, t, is_final=False): print(t)
    class TuringWorker:
        def __init__(self, w, m): self.worker_id=w; self.manager=m
        def execute(self, t): pass
    class TuringTask:
        def __init__(self, n, s): pass
    class WorkerState: SUCCESS="SUCCESS"; ERROR="ERROR"; EXIT="EXIT"; CONTINUE="CONTINUE"
    class StepResult:
        def __init__(self, d, state=None, is_final=False): self.display_text=d; self.state=state; self.is_final=is_final
    class AuditManager:
        def __init__(self, d, **kwargs): self.audit_dir = Path(d).resolve()
        def load(self, n): return {}
        def save(self, n, d): pass
        def print_cache_warning(self, **kwargs): pass
    
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "tool" / "PYTHON" / "data"
    AUDIT_DIR = DATA_DIR / "audit"
    RESOURCE_ROOT = PROJECT_ROOT / "resource" / "tool" / "PYTHON" / "data" / "install"
    TMP_INSTALL_DIR = DATA_DIR / "tmp" / "install"
    DEFAULT_CONCURRENCY = 1

PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"

# Build full command for cache warning
full_cmd = "PYTHON --py-update"
if len(sys.argv) > 1:
    full_cmd += " " + " ".join(sys.argv[1:])

audit = AuditManager(AUDIT_DIR, component_name="PYTHON_UPDATE", audit_command=full_cmd)

TMP_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ANSI Colors
RED = get_color("RED", "\033[31m")
GREEN = get_color("GREEN", "\033[32m")
YELLOW = get_color("YELLOW", "\033[33m")
BLUE = get_color("BLUE", "\033[34m")
WHITE = get_color("WHITE", "\033[37m")
BOLD = get_color("BOLD", "\033[1m")
RESET = get_color("RESET", "\033[0m")

DEBUG_LOG_PATH = PROJECT_ROOT / "tmp" / "python_update_debug.log"

def log_debug(msg):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except: pass

def print_erasable(msg):
    from logic.turing.display.manager import _get_configured_width
    width = _get_configured_width()
    if width > 0:
        display_text = truncate_to_display_width(msg, max(1, width - 2))
    else:
        display_text = msg
    sys.stdout.write(f"\r\033[K{display_text}")
    sys.stdout.flush()

def _(key, default, **kwargs):
    return get_translation(str(PYTHON_TOOL_DIR / "logic"), key, default).format(**kwargs)

def resolve_platform(asset_name):
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

_warning_printed = False

def print_cache_warning_once():
    global _warning_printed
    if not _warning_printed:
        audit.print_cache_warning()
        _warning_printed = True

def get_release_tags(use_cache=True):
    if use_cache:
        cache = audit.load("tags_cache")
        if cache and "tags" in cache and (datetime.now() - datetime.fromisoformat(cache["timestamp"])).days < 1:
            print_cache_warning_once()
            return cache["tags"]

    fetch_label = f"{BOLD}{BLUE}" + _("label_fetching_releases", "Fetching releases") + f"{RESET}"
    owner_label = f"{BOLD}{PROJECT_OWNER}{RESET}"
    fetch_msg = f"{fetch_label} from GitHub project {owner_label} ({PROJECT_URL})..."
    print_erasable(fetch_msg)
    log_debug(f"Fetching tags from {REPO_URL}...")
    
    cmd = ["/usr/bin/git", "ls-remote", "--tags", REPO_URL]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n{BOLD}{RED}{_('label_error', 'Error')}{RESET}: Failed to fetch tags.")
        log_debug(f"Failed to fetch tags: {result.stderr}")
        sys.exit(1)
    tags = []
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    
    tags = sorted(list(set(tags)), reverse=True) # NEWEST FIRST
    audit.save("tags_cache", {"tags": tags, "timestamp": datetime.now().isoformat()})
    log_debug(f"Found {len(tags)} tags.")
    return tags

def fetch_assets_for_tag(tag, use_cache=True, status_msg=None, silent=False):
    asset_cache_dir = AUDIT_DIR / "assets"
    asset_cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_path = asset_cache_dir / f"assets_{tag}.json"
    if use_cache and cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            if "assets" in cache:
                if not silent:
                    print_cache_warning_once()
                return cache["assets"]
        except: pass

    if not silent and status_msg:
        print_erasable(status_msg)

    log_debug(f"Fetching assets for tag {tag}...")
    # Use GitHub API for full asset list (avoids 100-asset limit of expanded_assets scraping)
    api_url = f"https://api.github.com/repos/{PROJECT_OWNER}/{PROJECT_NAME}/releases/tags/{tag}"
    cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", api_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assets = []
    try:
        data = json.loads(result.stdout)
        if "assets" in data:
            for item in data["assets"]:
                name = item["name"]
                if not name.endswith(".tar.zst") or name.endswith(".sha256"):
                    continue
                
                v_match = re.search(r"(\d+\.\d+\.\d+)", name)
                if not v_match: continue
                
                full_v = v_match.group(1)
                minor_v = ".".join(full_v.split(".")[:2])
                patch_str = full_v.split(".")[2]
                try: patch = int(patch_str)
                except ValueError: patch = 0
                
                platform = resolve_platform(name)
                if platform:
                    assets.append({
                        "name": name,
                        "url": item["browser_download_url"],
                        "version": full_v,
                        "minor": minor_v,
                        "patch": patch,
                        "platform": platform,
                        "tag": tag
                    })
        else:
            # Trigger fallback if assets not in data (e.g. rate limit error)
            raise ValueError("No assets in API response")
    except:
        # Fallback to scraping if API fails or rate limited
        url = f"{PROJECT_URL}/releases/expanded_assets/{tag}"
        cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        matches = re.findall(r'cpython-([\w\+\-\.]+)\.tar\.zst', result.stdout)
        for name_core in set(matches):
            name = f"cpython-{name_core}.tar.zst"
            v_match = re.search(r"(\d+\.\d+\.\d+)", name)
            if not v_match: continue
            full_v = v_match.group(1)
            minor_v = ".".join(full_v.split(".")[:2])
            patch_str = full_v.split(".")[2]
            try: patch = int(patch_str)
            except ValueError: patch = 0
            platform = resolve_platform(name)
            if platform:
                assets.append({
                    "name": name,
                    "url": f"{PROJECT_URL}/releases/download/{tag}/{name}",
                    "version": full_v,
                    "minor": minor_v,
                    "patch": patch,
                    "platform": platform,
                    "tag": tag
                })
            
    with open(cache_path, "w") as f:
        json.dump({"assets": assets, "timestamp": datetime.now().isoformat()}, f, indent=2)
    try:
        from logic.utils import cleanup_old_files
        cleanup_old_files(asset_cache_dir, "assets_*.json", limit=1000, batch_size=500)
    except: pass
    log_debug(f"Found {len(assets)} compatible assets for tag {tag}.")
    return assets

def get_remote_resources():
    log_debug("Fetching remote resources status from 'tool' branch...")
    try:
        subprocess.run(["/usr/bin/git", "fetch", "origin", "tool"], cwd=str(PROJECT_ROOT), capture_output=True)
        rel_path = str(RESOURCE_ROOT.relative_to(PROJECT_ROOT)) + "/"
        cmd = ["/usr/bin/git", "ls-tree", "-r", "origin/tool", rel_path]
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        lines = result.stdout.strip().split("\n") if result.returncode == 0 else []
    except Exception as e:
        log_debug(f"Git fetch error: {e}")
        lines = []

    resources = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 4: continue
        file_path = parts[3]
        
        if "PYTHON.json" in line:
            try:
                cmd = ["/usr/bin/git", "show", f"origin/tool:{file_path}"]
                res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    v_tag = Path(file_path).parent.name
                    resources[v_tag] = data
            except: pass
        elif ".tar.zst" in line:
            v_tag = Path(file_path).parent.name
            if v_tag not in resources:
                filename = Path(file_path).name
                match = re.search(r"-(\d{8}(?:T\d+)?)\.tar\.zst$", filename)
                release = match.group(1) if match else "0"
                resources[v_tag] = {"release": release, "asset": filename}
    log_debug(f"Identified {len(resources)} resources already on remote.")
    return resources

def log_failure(asset_name, tag, error_msg):
    """Log a migration failure to a JSON report."""
    try:
        report_dir = AUDIT_DIR / "failures"
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        report_path = report_dir / f"failure_{timestamp}_{rand_id}.json"
        
        failure_data = {
            "timestamp": datetime.now().isoformat(),
            "asset": asset_name,
            "release": tag,
            "error": error_msg
        }
        
        with open(report_path, "w") as f:
            json.dump(failure_data, f, indent=2)
            
        from logic.utils import cleanup_old_files
        cleanup_old_files(report_dir, "failure_*.json", limit=1000, batch_size=500)
    except: pass

def push_step(asset, tag, worker_id, manager, git_lock=None, force=False):
    def logic():
        v_tag = regularize_version_name(asset['version'], asset['platform'])
        log_debug(f"[{worker_id}] Starting migration for {v_tag} from release {tag}...")
        unique_str = f"{tag}-{asset['name']}-{worker_id}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"
        dir_hash = hashlib.md5(unique_str.encode()).hexdigest()[:8]
        tmp_path = TMP_INSTALL_DIR / f"migrate_{v_tag}_{dir_hash}"
        if tmp_path.exists(): shutil.rmtree(tmp_path)
        tmp_path.mkdir(parents=True)
        
        zst_path = tmp_path / asset["name"]
        json_path = tmp_path / "PYTHON.json"
        
        try:
            # 1. Download
            prefix = f"{BOLD}{BLUE}Downloading{RESET} {v_tag}"
            curl_cmd = ["curl", "-L", asset["url"], "-o", str(zst_path)]
            yield StepResult(f"{prefix}: 0.0%", state=WorkerState.CONTINUE)
            
            success, err = run_with_progress(curl_cmd, prefix, worker_id=worker_id, manager=manager)
            if not success:
                error_msg = f"{BOLD}{RED}Download failed{RESET} for {v_tag}: {err}"
                log_debug(f"[{worker_id}] {error_msg}")
                log_failure(asset["name"], tag, err)
                yield StepResult(error_msg, state=WorkerState.ERROR, is_final=True)
                return

            # 2. Metadata
            meta = {"release": tag, "asset": asset["name"], "version": asset["version"], "platform": asset["platform"]}
            with open(json_path, "w") as f: json.dump(meta, f, indent=2)
            
            # Also update local installation if it exists
            local_install_dir = DATA_DIR / "install" / v_tag
            if local_install_dir.exists():
                try:
                    shutil.copy2(str(json_path), str(local_install_dir / "PYTHON.json"))
                except: pass

            # 3. Git Operations (must be serial due to .git/index lock)
            if git_lock: git_lock.acquire()
            try:
                env = os.environ.copy()
                side_index = PROJECT_ROOT / ".git" / f"index_migrate_{worker_id}_{dir_hash}"
                env["GIT_INDEX_FILE"] = str(side_index)
                
                log_debug(f"[{worker_id}] Performing Git operations for {v_tag}...")
                # Fetch latest tool branch to ensure we are up to date
                subprocess.run(["/usr/bin/git", "fetch", "origin", "tool"], cwd=str(PROJECT_ROOT), capture_output=True, env=env)
                
                # Check if it already exists on remote with SAME release tag
                res_rel_path = f"resource/tool/PYTHON/data/install/{v_tag}"
                if not force:
                    check_cmd = ["/usr/bin/git", "ls-tree", "-r", "origin/tool", res_rel_path]
                    res = subprocess.run(check_cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                    if res.returncode == 0 and f"{v_tag}/PYTHON.json" in res.stdout:
                        # Check release tag
                        show_cmd = ["/usr/bin/git", "show", f"origin/tool:{res_rel_path}/PYTHON.json"]
                        res_json = subprocess.run(show_cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                        if res_json.returncode == 0:
                            try:
                                remote_meta = json.loads(res_json.stdout)
                                if str(remote_meta.get("release")) >= str(tag):
                                    log_debug(f"[{worker_id}] Version {v_tag} already on remote with tag {remote_meta.get('release')}.")
                                    yield StepResult(f"{BOLD}Already migrated{RESET} {v_tag} (tag {tag}).", state=WorkerState.SUCCESS, is_final=True)
                                    return
                            except: pass

                # Initialize side index with current tool branch tree
                subprocess.run(["/usr/bin/git", "read-tree", "origin/tool"], cwd=str(PROJECT_ROOT), capture_output=True, env=env)
                
                # Add metadata to side index
                def git_add_file(file_path, repo_path):
                    res = subprocess.run(["/usr/bin/git", "hash-object", "-w", str(file_path)], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                    sha = res.stdout.strip()
                    subprocess.run(["/usr/bin/git", "update-index", "--add", "--cacheinfo", "100644", sha, repo_path], cwd=str(PROJECT_ROOT), capture_output=True, env=env)

                git_add_file(json_path, f"{res_rel_path}/PYTHON.json")
                # git_add_file(zst_path, f"{res_rel_path}/{asset['name']}") # Stop pushing binaries to save LFS budget
                
                # Write tree
                res = subprocess.run(["/usr/bin/git", "write-tree"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                tree_sha = res.stdout.strip()
                
                # Create commit
                commit_msg = f"Add Python {v_tag} from release {tag} [{worker_id}]"
                res = subprocess.run(["/usr/bin/git", "commit-tree", tree_sha, "-p", "origin/tool", "-m", commit_msg], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                commit_sha = res.stdout.strip()
                
                prefix = f"{BOLD}{BLUE}Pushing{RESET} {v_tag}"
                manager.update(worker_id, f"{prefix}: 0.0%")
                
                success = False
                last_err = "Push failed"
                for i in range(5):
                    log_debug(f"[{worker_id}] Push attempt {i+1} for {v_tag}...")
                    res = subprocess.run(["/usr/bin/git", "push", "origin", f"{commit_sha}:refs/heads/tool"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                    if res.returncode == 0:
                        success = True
                        break
                    
                    last_err = res.stderr.strip()
                    log_debug(f"[{worker_id}] Push failed: {last_err}")
                    time.sleep(1 + random.random() * 2)
                    subprocess.run(["/usr/bin/git", "fetch", "origin", "tool"], cwd=str(PROJECT_ROOT), capture_output=True, env=env)
                    res = subprocess.run(["/usr/bin/git", "commit-tree", tree_sha, "-p", "origin/tool", "-m", commit_msg], cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=env)
                    commit_sha = res.stdout.strip()
                
                if success:
                    success_status = _("python_migrated_success_status", "Successfully migrated")
                    from_label = _("label_from", "from")
                    msg = f"{BOLD}{GREEN}{success_status}{RESET} {v_tag} {from_label} {BOLD}{tag}{RESET}."
                    log_debug(f"[{worker_id}] {msg}")
                    yield StepResult(msg, state=WorkerState.SUCCESS, is_final=True)
                else:
                    error_msg = f"{BOLD}{RED}Push failed{RESET} for {v_tag}: {last_err}"
                    log_debug(f"[{worker_id}] {error_msg}")
                    log_failure(asset["name"], tag, last_err)
                    yield StepResult(error_msg, state=WorkerState.ERROR, is_final=True)
            finally:
                if side_index.exists(): side_index.unlink()
                if git_lock: git_lock.release()
                # Clean up local resource dir
                res_dir = RESOURCE_ROOT / v_tag
                if res_dir.exists():
                    try: shutil.rmtree(res_dir)
                    except: pass
                
        except Exception as e:
            error_msg = f"{BOLD}{RED}Error{RESET} {v_tag}: {e}"
            log_debug(f"[{worker_id}] {error_msg}")
            log_failure(asset["name"], tag, str(e))
            yield StepResult(error_msg, state=WorkerState.ERROR, is_final=True)
        finally:
            if tmp_path.exists(): shutil.rmtree(tmp_path)
    return logic()

def main():
    parser = argparse.ArgumentParser(description="PYTHON Resource Update Tool")
    parser.add_argument("--version", help="Version to migrate")
    parser.add_argument("--platform", help="Platform to migrate")
    parser.add_argument("--tag", help="Specific tag")
    parser.add_argument("--all-latest", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true", help="List available versions from releases")
    parser.add_argument("--limit-releases", type=int, help="Limit number of releases to scan")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--simple", action="store_true", help="One-line comma-separated list of versions")
    parser.add_argument("--reverse", action="store_true", help="Reverse sort order (newest first)")
    parser.add_argument("--count", type=int, help="Stop scanning once this many target assets are found")
    
    args, unknown = parser.parse_known_args()

    log_debug(f"--- PYTHON --py-update command started: {' '.join(sys.argv)} ---")

    # Precise tag:version pair support (e.g., 20211017:3.10.0-windows-x86)
    precise_targets = [] # List of (tag, version)
    
    # Combined list of all positional/version arguments
    all_raw_args = []
    if args.version:
        all_raw_args.extend([p.strip().strip('"').strip("'").strip(",") for p in args.version.split(",")])
    for arg in unknown:
        all_raw_args.extend([p.strip().strip('"').strip("'").strip(",") for p in arg.split(",")])
    
    target_versions = []
    for arg in all_raw_args:
        if ":" in arg:
            parts = arg.split(":")
            if len(parts) == 2:
                precise_targets.append((parts[0], parts[1]))
        else:
            target_versions.append(arg)
    
    target_versions = list(set([v for v in target_versions if v]))
    log_debug(f"Target versions: {target_versions}, Precise targets: {precise_targets}")

    tags = get_release_tags(use_cache=not args.force)
    
    if args.tag:
        if args.tag in tags:
            tags = [args.tag]
        else:
            print(f"{BOLD}{RED}{_('label_error', 'Error')}{RESET}: Tag {args.tag} not found.")
            sys.exit(1)
    
    if args.limit_releases and not args.tag: tags = tags[:args.limit_releases]
    
    if not target_versions and not precise_targets and not args.tag and not args.list:
        args.all_latest = True
        
    all_to_migrate = [] # List of (asset_dict, tag)
    already_migrated_total = set()
    remote_resources = {}

    if target_versions or args.all_latest or args.tag or args.list:
        # UI Setup for scanning/listing
        scan_manager = MultiLineManager()
        worker_id = "SCAN"
        start_time = time.time()
        scan_label = f"{BOLD}{BLUE}" + _("label_fetching_assets", "Scanning releases") + f"{RESET}"
        
        # 1. Get remote resources status with UI feedback
        scan_manager.update(worker_id, f"{BOLD}{BLUE}Syncing{RESET} remote status from 'tool' branch...")
        remote_resources = get_remote_resources()
        
        if args.list:
            # ... (omitted listing logic) ...
            # ...
            print(f"\n{BOLD}{WHITE}Full report saved to{RESET}: {report_path}")
            return

        # 1. Handle precise targets first
        if precise_targets:
            tag_to_v = {}
            for t, v in precise_targets:
                if t not in tag_to_v: tag_to_v[t] = []
                tag_to_v[t].append(v)
            
            for t, versions in tag_to_v.items():
                fetch_label = f"{BOLD}{BLUE}" + _("label_fetching_assets", "Fetching assets") + f"{RESET}"
                date_label = f"{BOLD}{WHITE}{t}{RESET}"
                fetch_msg = f"{fetch_label} for {date_label}..."
                assets = fetch_assets_for_tag(t, use_cache=not args.force, status_msg=fetch_msg)
                
                for v in versions:
                    found = False
                    for a in assets:
                        v_tag = regularize_version_name(a['version'], a['platform'])
                        if v_tag == v or a["version"] == v:
                            if not args.force and v_tag in remote_resources and str(t) <= str(remote_resources[v_tag].get("release", "0")):
                                already_migrated_total.add(v_tag)
                            else:
                                all_to_migrate.append((a, t))
                            found = True
                            break
                    if not found:
                        error_msg = f"\n{BOLD}{RED}{_('label_error', 'Error')}{RESET}: Asset {v} not found in release {t}."
                        print(error_msg)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        # 2. Handle version prefix / tag filters
        if target_versions or args.all_latest or args.tag:
            log_debug(f"Scanning {len(tags)} tags for matching versions...")
            
            # Optimization: keep track of which versions we've already found to stop scanning tags early
            remaining_targets = set(target_versions)
            found_count = 0

            for i, tag in enumerate(tags):
                # Check if we can stop scanning
                if target_versions and not args.all_latest and not remaining_targets:
                    log_debug("All target versions found. Stopping tag scan.")
                    break
                
                elapsed = int(time.time() - start_time)
                status = f"{scan_label} from GitHub ({tag}) (found: {found_count})({elapsed}s)..."
                scan_manager.update(worker_id, status)
                
                assets = fetch_assets_for_tag(tag, use_cache=not args.force, silent=True)
                
                current_filtered = assets
                if target_versions:
                    match_in_tag = []
                    for a in current_filtered:
                        v_tag = regularize_version_name(a['version'], a['platform'])
                        match = False
                        for tv in target_versions:
                            if "-" in tv:
                                if v_tag == tv: match = True; break
                            else:
                                if a["version"].startswith(tv): match = True; break
                        if match:
                            match_in_tag.append(a)
                    current_filtered = match_in_tag
                    
                if args.platform:
                    current_filtered = [a for a in current_filtered if a["platform"] == args.platform]
                    
                if not current_filtered:
                    continue

                # If we found matches in this tag, mark those versions as satisfied if they are newest
                found_in_this_tag = 0
                for a in current_filtered:
                    v_tag = regularize_version_name(a['version'], a['platform'])
                    for tv in list(remaining_targets):
                        if tv == v_tag or a["version"].startswith(tv):
                            remaining_targets.discard(tv)

                def vp(n):
                    if "pgo+lto-full" in n: return 0
                    if "pgo-full" in n: return 1
                    if "install_only" in n: return 2
                    return 10
                current_filtered = sorted(current_filtered, key=lambda x: (x["patch"], -vp(x["name"])), reverse=True)
                
                seen_in_tag = set()
                for a in current_filtered:
                    v_tag = regularize_version_name(a['version'], a['platform'])
                    if not args.force and v_tag in remote_resources and str(tag) <= str(remote_resources[v_tag].get("release", "0")):
                        already_migrated_total.add(v_tag)
                        continue
                    
                    # key should be the full version-platform to allow multiple patches in one tag
                    key = (a["version"], a["platform"])
                    if key not in seen_in_tag:
                        all_to_migrate.append((a, tag))
                        seen_in_tag.add(key)
                        found_count += 1
                        found_in_this_tag += 1
                        if not args.all_latest and not target_versions: 
                            # If just looking for "latest" (no filters), stop at first tag with assets
                            break
                
                if found_in_this_tag > 0:
                    elapsed = int(time.time() - start_time)
                    status = f"{scan_label} from GitHub ({tag}) (found: {found_count})({elapsed}s)..."
                    scan_manager.update(worker_id, status)

                # Early exit if enough assets found
                if args.count and found_count >= args.count:
                    log_debug(f"Reached count limit ({args.count}). Stopping tag scan.")
                    break

                if not args.all_latest and not target_versions: break

            elapsed = int(time.time() - start_time)
            scan_manager.update(worker_id, f"{scan_label}: {BOLD}{GREEN}Found {found_count} new assets{RESET} in {elapsed}s", is_final=True)

    # 3. Execution
    if already_migrated_total and not all_to_migrate:
        print(f"{BOLD}Already migrated{RESET} {', '.join(sorted(list(already_migrated_total)))}. {BOLD}{_('python_remote_up_to_date', 'Remote up to date')}.{RESET}")
        return
    if already_migrated_total:
        print(f"{BOLD}Already migrated{RESET} {', '.join(sorted(list(already_migrated_total)))}.")

    # Filter all_to_migrate to only keep the LATEST tag for each unique version-platform
    latest_per_vtag = {}
    for a, t in all_to_migrate:
        v_tag = regularize_version_name(a['version'], a['platform'])
        if v_tag not in latest_per_vtag or str(t) > str(latest_per_vtag[v_tag][1]):
            latest_per_vtag[v_tag] = (a, t)
    
    all_to_migrate = list(latest_per_vtag.values())

    if not all_to_migrate:
        print(f"{BOLD}{_('python_remote_up_to_date', 'Remote up to date')}.{RESET}")
        return

    asset_count = len(all_to_migrate)
    asset_word = _("label_assets", "assets")
    found_label = _("python_found_assets_count", "Found {count} {word}", count=asset_count, word=asset_word)
    v_display_tags = [f"{t}:{regularize_version_name(a['version'], a['platform'])}" for a, t in all_to_migrate]
    to_msg = _("label_to_migrate", "to migrate")
    print(f"{BOLD}{found_label}{RESET} {to_msg}: {', '.join(v_display_tags)}")
    
    manager = MultiLineManager()
    task_queue = Queue()
    for a, t in all_to_migrate: task_queue.put((a, t))
    
    git_lock = threading.Lock()

    def worker_loop(worker_id):
        worker = TuringWorker(worker_id, manager)
        while not task_queue.empty():
            try: a, t = task_queue.get_nowait()
            except: break
            t_task = TuringTask(a['name'], [lambda a=a, t=t: push_step(a, t, worker_id, manager, git_lock, force=args.force)])
            worker.execute(t_task)
            task_queue.task_done()

    threads = []
    for i in range(min(args.concurrency, len(all_to_migrate))):
        t = threading.Thread(target=worker_loop, args=(f"W{i+1}",))
        t.start()
        threads.append(t)
    for t in threads: t.join()

    # Post-migration maintenance: prune local LFS objects to avoid repository bloat
    if all_to_migrate:
        log_debug("Starting post-migration maintenance: LFS prune...")
        # Run pruning in background to avoid blocking user if it's very large
        # But here we can run it since the tasks are done.
        try:
            subprocess.run(["/usr/bin/git", "lfs", "prune", "--force"], cwd=str(PROJECT_ROOT), capture_output=True)
            log_debug("LFS prune complete.")
        except: pass

if __name__ == "__main__":
    main()
