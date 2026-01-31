import os
import re
import json
import subprocess
import argparse
import sys
import shutil
import hashlib
import threading
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
    from logic.utils import get_system_tag, regularize_version_name, run_with_progress
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
    TMP_INSTALL_DIR = PROJECT_ROOT / "tmp" / "install"
    DEFAULT_CONCURRENCY = 1

PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"

# Build full command for cache warning
full_cmd = "PYTHON --py-update"
if len(sys.argv) > 1:
    # Filter out internal flags if any, but usually we just want what user typed
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

def print_erasable(msg):
    sys.stdout.write(f"\r\033[K{msg}")
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

    fetch_msg = _("python_fetching_releases", "Fetching releases from GitHub project {owner} ({url})...", 
                  owner=PROJECT_OWNER, url=PROJECT_URL)
    print(fetch_msg)
    
    cmd = ["git", "ls-remote", "--tags", REPO_URL]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{BOLD}{RED}{_('label_error', 'Error')}{RESET}: Failed to fetch tags.")
        sys.exit(1)
    tags = []
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    
    tags = sorted(list(set(tags))) # Ascending (Oldest first)
    audit.save("tags_cache", {"tags": tags, "timestamp": datetime.now().isoformat()})
    return tags

def fetch_assets_for_tag(tag, use_cache=True, status_msg=None, silent=False):
    cache = audit.load(f"assets_{tag}")
    if use_cache and cache and "assets" in cache:
        if not silent:
            print_cache_warning_once()
        return cache["assets"]

    if not silent and status_msg:
        print_erasable(status_msg)

    url = f"{PROJECT_URL}/releases/expanded_assets/{tag}"
    cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assets = []
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
            
    audit.save(f"assets_{tag}", {"assets": assets, "timestamp": datetime.now().isoformat()})
    return assets

def get_remote_resources():
    try:
        from proj.git import list_remote_files, run_git_command
        run_git_command(["fetch", "origin", "tool"], cwd=str(PROJECT_ROOT))
        rel_path = str(RESOURCE_ROOT.relative_to(PROJECT_ROOT)) + "/"
        lines = list_remote_files("tool", rel_path, remote="origin", cwd=str(PROJECT_ROOT))
    except:
        subprocess.run(["git", "fetch", "origin", "tool"], cwd=str(PROJECT_ROOT), capture_output=True)
        rel_path = str(RESOURCE_ROOT.relative_to(PROJECT_ROOT)) + "/"
        cmd = ["git", "ls-tree", "-r", "origin/tool", rel_path]
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        lines = result.stdout.strip().split("\n") if result.returncode == 0 else []

    resources = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 4: continue
        file_path = parts[3]
        
        # Priority 1: PYTHON.json
        if "PYTHON.json" in line:
            try:
                cmd = ["git", "show", f"origin/tool:{file_path}"]
                res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
                if res.returncode == 0:
                    data = json.loads(res.stdout)
                    v_tag = Path(file_path).parent.name
                    resources[v_tag] = data
            except: pass
        # Priority 2: .tar.zst if not already seen via JSON
        elif ".tar.zst" in line:
            v_tag = Path(file_path).parent.name
            if v_tag not in resources:
                # Infer release from filename if possible
                filename = Path(file_path).name
                # cpython-VERSION-PLATFORM-TAG.tar.zst
                # Tag is usually after the last dash before .tar.zst
                match = re.search(r"-(\d{8}(?:T\d+)?)\.tar\.zst$", filename)
                release = match.group(1) if match else "0"
                resources[v_tag] = {"release": release, "asset": filename}
    return resources

def push_step(asset, tag, worker_id, manager):
    def logic():
        v_tag = regularize_version_name(asset['version'], asset['platform'])
        unique_str = f"{tag}-{asset['name']}"
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
            
            if not run_with_progress(curl_cmd, prefix, worker_id=worker_id, manager=manager):
                error_msg = f"{BOLD}{RED}Download failed{RESET} for {v_tag}"
                yield StepResult(error_msg, state=WorkerState.ERROR, is_final=True)
                return

            # 2. Metadata
            meta = {"release": tag, "asset": asset["name"], "version": asset["version"], "platform": asset["platform"]}
            with open(json_path, "w") as f: json.dump(meta, f, indent=2)
            
            # 3. Move to resource dir
            res_dir = RESOURCE_ROOT / v_tag
            res_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(zst_path), str(res_dir / asset["name"]))
            shutil.move(str(json_path), str(res_dir / "PYTHON.json"))
            
            # 4. Git
            rel_path = res_dir.relative_to(PROJECT_ROOT)
            prefix = f"{BOLD}{BLUE}Pushing{RESET} {v_tag}"
            manager.update(worker_id, f"{prefix}: 0.0%")
            
            subprocess.run(["git", "add", "-f", str(rel_path / "PYTHON.json")], cwd=str(PROJECT_ROOT), capture_output=True)
            subprocess.run(["git", "add", "-f", str(rel_path / asset["name"])], cwd=str(PROJECT_ROOT), capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Add Python {v_tag}"], cwd=str(PROJECT_ROOT), capture_output=True)
            
            success = False
            for i in range(3):
                if run_with_progress(["git", "push", "origin", "HEAD:tool"], prefix, worker_id=worker_id, manager=manager):
                    success = True
                    break
                subprocess.run(["git", "pull", "--rebase", "origin", "tool"], cwd=str(PROJECT_ROOT), capture_output=True)
                
            if success:
                shutil.rmtree(res_dir)
                success_status = _("python_migrated_success_status", "Successfully migrated")
                from_label = _("label_from", "from")
                msg = f"{BOLD}{GREEN}{success_status}{RESET} {v_tag} {from_label} {BOLD}{tag}{RESET}."
                yield StepResult(msg, state=WorkerState.SUCCESS, is_final=True)
            else:
                error_msg = f"{BOLD}{RED}Push failed{RESET} for {v_tag}"
                yield StepResult(error_msg, state=WorkerState.ERROR, is_final=True)
                
        except Exception as e:
            error_msg = f"{BOLD}{RED}Error{RESET} {v_tag}: {e}"
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
    args = parser.parse_args()

    tags = get_release_tags(use_cache=not args.force)
    if args.limit_releases: tags = tags[:args.limit_releases]
    
    remote_resources = get_remote_resources()
    
    if args.list:
        matrix = {}
        scan_label = f"{BOLD}{BLUE}Scanning{RESET}"
        for i, tag in enumerate(tags):
            print_erasable(f"{scan_label}: {tag} ({i+1}/{len(tags)})")
            assets = fetch_assets_for_tag(tag, use_cache=not args.force, silent=True)
            for a in assets:
                v_tag = regularize_version_name(a['version'], a['platform'])
                if v_tag not in matrix: matrix[v_tag] = set()
                matrix[v_tag].add(tag)
        sys.stdout.write("\r\033[K")
        
        sorted_versions = sorted(matrix.keys(), reverse=args.reverse)
        
        if args.simple:
            print(", ".join(sorted_versions))
        else:
            for v in sorted_versions:
                # Version name in white bold
                tag_list = sorted(list(matrix[v]))
                print(f"{BOLD}{WHITE}{v}{RESET}:{','.join(tag_list)}")
        
        # Save audit cache
        audit_releases_dir = AUDIT_DIR / "releases"
        audit_releases_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Categorize
        by_version = {}
        by_platform = {}
        for v_tag in sorted_versions:
            # Extract version and platform from v_tag (e.g. 3.11.1-macos)
            v_match = re.match(r"(\d+\.\d+)", v_tag)
            major_minor = v_match.group(1) if v_match else "unknown"
            
            platform_match = re.search(r"-([a-z0-9\-]+)$", v_tag)
            platform_name = platform_match.group(1) if platform_match else "unknown"
            
            if major_minor not in by_version: by_version[major_minor] = []
            by_version[major_minor].append(v_tag)
            
            if platform_name not in by_platform: by_platform[platform_name] = []
            by_platform[platform_name].append(v_tag)
            
        full_data = {v: sorted(list(matrix[v])) for v in sorted_versions}
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "full": full_data,
            "short": sorted_versions,
            "by_version": by_version,
            "by_platform": by_platform
        }
        
        report_path = audit_releases_dir / f"report_{timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        # Cleanup
        from logic.utils import cleanup_old_files
        cleanup_old_files(audit_releases_dir, "report_*.json", limit=1024, batch_size=512)
        
        print(f"\n{BOLD}{WHITE}Full report saved to{RESET}: {report_path}")
        return

    if args.all_latest and not args.tag:
        target_tags = tags
    else:
        target_tags = [args.tag] if args.tag else [tags[-1]]

        for tag in target_tags:
            # Use localized string for fetching message
            fetch_msg = _("python_fetching_assets", "Fetching assets for {tag}...", tag=tag)
            assets = fetch_assets_for_tag(tag, use_cache=not args.force, status_msg=fetch_msg)
            # Clear the "Fetching" message completely
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
            filtered = assets
            if args.version:
                filtered = [a for a in filtered if a["version"].startswith(args.version)]
            if args.platform:
                filtered = [a for a in filtered if a["platform"] == args.platform]
                
            def vp(n):
                if "pgo+lto-full" in n: return 0
                if "pgo-full" in n: return 1
                if "install_only" in n: return 2
                return 10
            filtered = sorted(filtered, key=lambda x: (x["patch"], -vp(x["name"])), reverse=True)
            
            to_migrate = []
            already_migrated = []
            seen = set()
            for a in filtered:
                v_tag = regularize_version_name(a['version'], a['platform'])
                # If force is not set, skip already migrated versions
                if not args.force and v_tag in remote_resources and str(tag) <= str(remote_resources[v_tag].get("release", "0")):
                    already_migrated.append(v_tag)
                    continue
                
                key = (a["minor"], a["platform"])
                if key not in seen:
                    to_migrate.append(a)
                    seen.add(key)
                    if not args.all_latest and not args.version: break

            if already_migrated:
                already_label = f"{BOLD}{WHITE}Already migrated{RESET}"
                assets_str = ", ".join(already_migrated)
                # Build force command
                force_cmd = f"PYTHON --py-update --force --limit-releases {args.limit_releases or 1}"
                if args.tag: force_cmd += f" --tag {args.tag}"
                if args.version: force_cmd += f" --version {args.version}"
                if args.platform: force_cmd += f" --platform {args.platform}"
                
                print(f"{already_label} {assets_str}. To force migration, run: {BOLD}{force_cmd}{RESET}")

            if not to_migrate:
                if not already_migrated:
                    print(f"{BOLD}{_('python_remote_up_to_date', 'Remote up to date')} for {tag}.{RESET}")
                continue

        asset_count = len(to_migrate)
        asset_word = _("label_assets", "assets")
        found_label = _("python_found_assets_count", "Found {count} {word}", count=asset_count, word=asset_word)
        v_display_tags = [regularize_version_name(a['version'], a['platform']) for a in to_migrate]
        to_msg = _("label_to_migrate", "to migrate from release")
        print(f"{BOLD}{found_label}{RESET} {to_msg} {BOLD}{tag}{RESET}: {', '.join(v_display_tags)}")
        
        manager = MultiLineManager()
        task_queue = Queue()
        for a in to_migrate: task_queue.put(a)
        
        def worker_loop(worker_id):
            worker = TuringWorker(worker_id, manager)
            while not task_queue.empty():
                try: a = task_queue.get_nowait()
                except: break
                t = TuringTask(a['name'], [lambda a=a: push_step(a, tag, worker_id, manager)])
                worker.execute(t)
                task_queue.task_done()

        threads = []
        for i in range(min(args.concurrency, len(to_migrate))):
            t = threading.Thread(target=worker_loop, args=(f"W{i+1}",))
            t.start()
            threads.append(t)
        for t in threads: t.join()

if __name__ == "__main__":
    main()
