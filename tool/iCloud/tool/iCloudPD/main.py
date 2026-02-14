#!/usr/bin/env python3
import sys
import argparse
import json
import os
import time
from pathlib import Path
from datetime import datetime, date
import subprocess

# Add project root to sys.path
def find_root():
    from pathlib import Path
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        # Root indicator: tool.json AND bin/TOOL exists
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    # Prioritize project root and remove shadowing local logic
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    
    # Remove script dir from path to avoid shadowing
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
else:
    # Manual fallback for debugging (4 levels up from main.py resolved parent)
    curr = Path(__file__).resolve().parent
    project_root = curr.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage

def main():
    tool = ToolBase("iCloudPD")
    
    parser = argparse.ArgumentParser(description="iCloud Photo Downloader", add_help=False)
    parser.add_argument("--apple-id", help="Apple ID to use for login")
    parser.add_argument("--since", help="Download photos from this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Download photos before this date (YYYY-MM-DD)")
    parser.add_argument("--output", help="Target directory for downloads (default: current)")
    parser.add_argument("--force-rescan", action="store_true", help="Force rescan of iCloud photo library")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel download workers (default: 3)")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    BOLD, GREEN, BLUE, RESET, YELLOW = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET"), get_color("YELLOW")
    
    # 1. Login via iCloud interface
    from tool.iCloud.logic.interface.main import get_icloud_interface
    icloud = get_icloud_interface()
    
    print(f"{BOLD}{BLUE}Authenticating{RESET} with iCloud...")
    # Support pre-filled Apple ID
    login_res = icloud["run_login_gui"](apple_id=args.apple_id)
    
    if login_res.get("status") != "success":
        print(f"{BOLD}{get_color('RED')}Authentication failed{RESET}")
        sys.exit(1)
        
    creds = login_res["data"]
    apple_id = creds["apple_id"]
    password = creds["password"]
    
    # Initialize pyicloud
    from pyicloud import PyiCloudService
    
    api = PyiCloudService(apple_id, password)
    
    if api.requires_2fa:
        print(f"{BOLD}{YELLOW}Two-factor authentication required.{RESET}")
        from logic.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow
        from logic.gui.engine import setup_gui_environment
        setup_gui_environment()
        
        # Use our new 2FA blueprint
        win = TwoFactorAuthWindow(
            title="iCloud 2FA",
            timeout=300,
            internal_dir=str(tool.tool_dir / "logic"),
            n=6
        )
        win.run(win.setup_ui)
        
        if win.result.get("status") == "success":
            code = win.result["data"]
            if not api.validate_2fa_code(code):
                print(f"{BOLD}{get_color('RED')}Invalid 2FA code.{RESET}")
                sys.exit(1)
        else:
            print(f"{BOLD}{get_color('RED')}2FA verification cancelled or timed out.{RESET}")
            sys.exit(1)

    # 2. Scanning / Caching
    data_dir = tool.get_data_dir() / apple_id
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_file = data_dir / "photos_cache.json"
    
    all_photos_meta = []
    
    def scan_action(stage=None):
        nonlocal all_photos_meta
        if not args.force_rescan and cache_file.exists():
            with open(cache_file, 'r') as f:
                all_photos_meta = json.load(f)
            return True
            
        # Perform scan
        photos = api.photos.all
        count = 0
        for photo in photos:
            # Basic metadata
            all_photos_meta.append({
                "id": photo.id,
                "filename": photo.filename,
                "created": photo.created.isoformat() if photo.created else None,
                "size": photo.size,
                "dimensions": photo.dimensions
            })
            count += 1
            if stage: stage.active_name = f"Scanning {count} photos"
            
        with open(cache_file, 'w') as f:
            json.dump(all_photos_meta, f, indent=2)
        return True

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD")
    pm.add_stage(TuringStage(
        "scan", scan_action, 
        active_status="Scanning", active_name="iCloud photos",
        success_status="Indexed", success_name=f"{len(all_photos_meta)} photos"
    ))
    pm.run()
    
    # 3. Filtering and Scheduling
    since_date = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    before_date = datetime.strptime(args.before, "%Y-%m-%d").date() if args.before else None
    
    scheduled_ids = set()
    for p in all_photos_meta:
        p_date = datetime.fromisoformat(p["created"]).date() if p["created"] else None
        if since_date and (not p_date or p_date < since_date): continue
        if before_date and (not p_date or p_date >= before_date): continue
        scheduled_ids.add(p["id"])
        
    print(f"{BOLD}{BLUE}Scheduled{RESET} {len(scheduled_ids)} photos for download.")
    if not scheduled_ids:
        print("No photos found matching the criteria.")
        return

    # 4. Parallel Downloading
    from logic.turing.models.worker import ParallelWorkerPool
    output_root = Path(args.output or ".").resolve()
    
    # We need photo objects for download. 
    # Iterate api.photos.all once and find the ones in scheduled_ids.
    to_download_objects = []
    print(f"{BOLD}{BLUE}Gathering{RESET} photo objects...")
    for photo in api.photos.all:
        if photo.id in scheduled_ids:
            to_download_objects.append(photo)
        if len(to_download_objects) >= len(scheduled_ids):
            break

    def download_worker(stage, photo, target_path):
        try:
            # We don't use stage.active_name here because the DynamicStatusBar handles it
            download = photo.download()
            with open(target_path, 'wb') as f:
                for chunk in download.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            return True
        except Exception as e:
            if stage: stage.report_error(f"Failed to download {photo.filename}", str(e))
            return False

    pool = ParallelWorkerPool(max_workers=args.workers, status_label="Downloading", project_root=tool.project_root, tool_name="iCloudPD")
    pool.status_bar.set_counts(len(to_download_objects))
    
    tasks = []
    for photo in to_download_objects:
        p_date_str = photo.created.strftime("%Y-%m-%d") if photo.created else "unknown"
        target_dir = output_root / p_date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / photo.filename
        
        if target_file.exists():
            pool.status_bar.increment_completed()
            continue
            
        # Task ID will be "yyyy-mm-dd/filename" as requested
        task_id = f"{p_date_str}/{photo.filename}"
        tasks.append({
            "id": task_id,
            "action": download_worker,
            "args": (photo, target_file)
        })

    def on_success(task_id, res):
        pool.status_bar.increment_completed()

    if tasks:
        success = pool.run(tasks, success_callback=on_success)
        if success:
            print(f"\n{BOLD}{GREEN}Successfully completed{RESET} download task.")
        else:
            print(f"\n{BOLD}{get_color('RED')}Completed{RESET} download task with some errors.")
    else:
        print(f"\n{BOLD}{GREEN}All photos{RESET} already downloaded.")

if __name__ == "__main__":
    main()
