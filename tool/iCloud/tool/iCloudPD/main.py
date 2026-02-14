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
script_path = Path(__file__).resolve()
# tool/iCloud/tool/iCloudPD/main.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage

def main():
    tool = ToolBase("iCloudPD")
    
    parser = argparse.ArgumentParser(description="iCloud Photo Downloader", add_help=False)
    parser.add_argument("--since", help="Download photos from this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Download photos before this date (YYYY-MM-DD)")
    parser.add_argument("--output", default=".", help="Target directory for downloads")
    parser.add_argument("--force-rescan", action="store_true", help="Force rescan of iCloud photo library")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    BOLD, GREEN, BLUE, RESET, YELLOW = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET"), get_color("YELLOW")
    
    # 1. Login via iCloud interface
    from tool.iCloud.logic.interface.main import get_icloud_interface
    icloud = get_icloud_interface()
    
    print(f"{BOLD}{BLUE}Authenticating{RESET} with iCloud...")
    login_res = icloud["run_login_gui"]()
    
    if login_res.get("status") != "success":
        print(f"{BOLD}{get_color('RED')}Authentication failed{RESET}")
        sys.exit(1)
        
    creds = login_res["data"]
    apple_id = creds["apple_id"]
    password = creds["password"]
    
    # Initialize pyicloud (using standalone python if possible)
    from pyicloud import PyICloudService
    
    api = PyICloudService(apple_id, password)
    
    if api.requires_2fa:
        print(f"{BOLD}{YELLOW}Two-factor authentication required.{RESET}")
        from logic.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow
        from logic.gui.engine import setup_gui_environment
        setup_gui_environment()
        
        # Use our new 2FA blueprint
        win = TwoFactorAuthWindow(
            title="iCloud 2FA",
            timeout=300,
            internal_dir=str(script_path.parent / "logic"),
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
    data_dir = script_path.parent / "data" / apple_id
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_file = data_dir / "photos_cache.json"
    
    all_photos = []
    
    def scan_action(stage=None):
        nonlocal all_photos
        if not args.force_rescan and cache_file.exists():
            with open(cache_file, 'r') as f:
                all_photos = json.load(f)
            return True
            
        # Perform scan
        photos = api.photos.all
        count = 0
        for photo in photos:
            # Basic metadata
            all_photos.append({
                "id": photo.id,
                "filename": photo.filename,
                "created": photo.created.isoformat() if photo.created else None,
                "size": photo.size,
                "dimensions": photo.dimensions
            })
            count += 1
            if stage: stage.active_name = f"Scanning {count} photos"
            
        with open(cache_file, 'w') as f:
            json.dump(all_photos, f, indent=2)
        return True

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD")
    pm.add_stage(TuringStage(
        "scan", scan_action, 
        active_status="Scanning", active_name="iCloud photos",
        success_status="Indexed", success_name=f"{len(all_photos)} photos"
    ))
    pm.run()
    
    # 3. Filtering and Scheduling
    since_date = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    before_date = datetime.strptime(args.before, "%Y-%m-%d").date() if args.before else None
    
    to_download = []
    for p in all_photos:
        p_date = datetime.fromisoformat(p["created"]).date() if p["created"] else None
        if since_date and (not p_date or p_date < since_date): continue
        if before_date and (not p_date or p_date >= before_date): continue
        to_download.append(p)
        
    print(f"{BOLD}{BLUE}Scheduled{RESET} {len(to_download)} photos for download.")
    
    # 4. Downloading
    output_root = Path(args.output).resolve()
    
    count = 0
    scheduled_ids = {p["id"]: p for p in to_download}
    
    print(f"{BOLD}{BLUE}Downloading{RESET} photos...")
    
    # We iterate api.photos.all once and download those in our schedule
    for photo in api.photos.all:
        if photo.id in scheduled_ids:
            p = scheduled_ids[photo.id]
            p_date_str = photo.created.strftime("%Y-%m-%d") if photo.created else "unknown"
            target_dir = output_root / p_date_str
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / photo.filename
            
            if target_file.exists():
                count += 1
                continue
                
            try:
                download = photo.download()
                with open(target_file, 'wb') as f:
                    for chunk in download.iter_content(chunk_size=1024):
                        if chunk: f.write(chunk)
                count += 1
                sys.stdout.write(f"\r\033[K{BOLD}{BLUE}Downloading{RESET} ({count}/{len(to_download)}): {photo.filename}")
                sys.stdout.flush()
            except Exception as e:
                print(f"\n{BOLD}{get_color('RED')}Failed{RESET} to download {photo.filename}: {e}")
        
        if count >= len(to_download):
            break

    print(f"\n{BOLD}{GREEN}Successfully completed{RESET} download task.")

if __name__ == "__main__":
    main()
