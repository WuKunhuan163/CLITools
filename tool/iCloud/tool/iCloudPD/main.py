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
    parser.add_argument("--since", help="Download photos/videos from this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Download photos/videos before this date (YYYY-MM-DD)")
    parser.add_argument("--output", help="Target directory for downloads (default: current)")
    parser.add_argument("--force-rescan", action="store_true", help="Force rescan of iCloud photo/video library")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel download workers (default: 3)")
    parser.add_argument("--no-gui", action="store_true", help="Use CLI-only interaction (no GUI)")
    parser.add_argument("--only-photos", action="store_true", help="Only download photos")
    parser.add_argument("--only-videos", action="store_true", help="Only download videos")
    parser.add_argument("--formats", type=str, help="Filter by extensions, e.g. '*.png|*.jpg'")
    parser.add_argument("--regex", type=str, help="Regex filter for 'yyyy-mm-dd/filename'")
    parser.add_argument("--only-scan", action="store_true", help="Only scan and cache metadata, do not download")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    BOLD, GREEN, BLUE, RESET, YELLOW = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET"), get_color("YELLOW")
    
    # 1. Login and Authentication Flow
    from tool.iCloud.logic.interface.main import get_icloud_interface
    from pyicloud import PyiCloudService
    
    icloud = get_icloud_interface()
    api = None
    final_apple_id = None
    
    def save_session(apple_id, api):
        import pickle
        cookie_dir = tool.get_data_dir() / "session" / apple_id
        cookie_dir.mkdir(parents=True, exist_ok=True)
        cookie_file = cookie_dir / "session.pkl"
        with open(cookie_file, 'wb') as f:
            pickle.dump(api.session.cookies, f)

    def save_photos_cache(apple_id, all_photos_meta):
        """Helper to atomically save the grouped photos metadata."""
        data_dir = tool.get_data_dir() / "scan" / apple_id
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_file = data_dir / "photos_cache.json"
        try:
            tmp_cache = cache_file.with_suffix(".json.tmp")
            with open(tmp_cache, 'w', encoding='utf-8') as f:
                json.dump(all_photos_meta, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp_cache), str(cache_file))
        except Exception:
            pass

    def auth_action(stage=None):
        nonlocal api, final_apple_id
        
        # 1. CLI-only mode logic
        if args.no_gui:
            import getpass
            import pickle
            
            try:
                apple_id = args.apple_id or input("\nEnter Apple ID: ").strip()
            except (EOFError, KeyboardInterrupt) as e:
                msg = "Operation not supported by device (Non-interactive terminal)" if isinstance(e, EOFError) else "Cancelled by user"
                if stage: stage.report_error(f"Input Error: {msg}", msg)
                return False

            # Try session reuse first
            cookie_dir = tool.get_data_dir() / "session" / apple_id
            cookie_dir.mkdir(parents=True, exist_ok=True)
            cookie_file = cookie_dir / "session.pkl"
            
            if cookie_file.exists():
                try:
                    if stage: stage.active_name = f"reusing session for {apple_id}"
                    api = PyiCloudService(apple_id, "")
                    with open(cookie_file, 'rb') as f:
                        api.session.cookies.update(pickle.load(f))
                    _ = api.account.devices
                    final_apple_id = apple_id
                    if stage: 
                        # UI Request: Reused session bold, default color
                        stage.success_status = f"{BOLD}Reused session{RESET}"
                        stage.success_name = f"for {final_apple_id}"
                    return True
                except:
                    pass
            
            # Full login via CLI
            try:
                # Erase current progress line to show getpass prompt cleanly
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                password = getpass.getpass(f"Enter password for {apple_id}: ")
            except (EOFError, Exception) as e:
                # Capture specific EOF or TTY error
                msg = str(e) or "Operation not supported by device (Non-interactive terminal)"
                if stage: stage.report_error(f"CLI Error: {msg}", msg)
                return False

            try:
                if stage: stage.active_name = f"authenticating {apple_id}"
                api = PyiCloudService(apple_id, password)
                
                if api.requires_2fa:
                    print(f"\n{BOLD}{YELLOW}Two-factor authentication required.{RESET}")
                    try:
                        code = input("Enter 6-digit 2FA code: ").strip()
                    except EOFError:
                        if stage: stage.report_error("CLI Error: Input stream closed (EOF)", "Failed to get 2FA code input (EOF).")
                        return False
                        
                    if not api.validate_2fa_code(code):
                        if stage: stage.report_error("2FA Failed: Invalid code", "The code you entered was incorrect.")
                        return False
                
                save_session(apple_id, api)
                final_apple_id = apple_id
                
                # Erase the getpass line before showing success
                sys.stdout.write("\033[F\033[K")
                sys.stdout.flush()
                
                if stage: 
                    # UI Request: iCloud green bold
                    stage.success_status = f"{BOLD}{GREEN}iCloud{RESET}"
                    stage.success_name = f"authenticated as {final_apple_id}"
                return True
            except Exception as e:
                # Ensure we have a non-empty reason
                err_msg = str(e)
                if not err_msg:
                    err_msg = f"Unknown internal error ({type(e).__name__})"
                if stage: stage.report_error(f"Login Failed: {err_msg}", err_msg)
                return False

        # 2. GUI mode logic
        # The login GUI now handles retries and validation internally
        login_res = icloud["run_login_gui"](apple_id=args.apple_id)
        
        if login_res.get("status") != "success":
            # If status is 'error', 'data' contains the full history log
            error_detail = login_res.get("data") or login_res.get("message") or "Login cancelled."
            reason = "Maximum attempts (5) exceeded" if login_res.get("reason") == "max_attempts_exceeded" else "Login cancelled"
            if stage: stage.report_error(reason, error_detail)
            return False
            
        creds = login_res["data"]
        apple_id = creds["apple_id"]
        # mode might be 'session_reuse' or 'full_login'
        mode = creds.get("mode")
        
        if mode == "session_reuse":
            # Re-initialize API object from cookies
            import pickle
            try:
                if stage: stage.active_name = f"Finalizing session for {apple_id}"
                api = PyiCloudService(apple_id, "")
                cookie_file = tool.get_data_dir() / "session" / apple_id / "session.pkl"
                with open(cookie_file, 'rb') as f:
                    api.session.cookies.update(pickle.load(f))
                final_apple_id = apple_id
                if stage: 
                    # UI Request: Reused session bold
                    stage.success_status = f"{BOLD}Reused session{RESET}"
                    stage.success_name = f"for {final_apple_id}"
                return True
            except Exception as e:
                # If reuse failed unexpectedly, fallback to full login or error
                if stage: stage.report_error("Session Error", f"Failed to restore session: {e}")
                return False

        # Full login (credentials provided by GUI)
        password = creds["password"]
        try:
            if stage: stage.active_name = f"Finalizing session for {apple_id}"
            api = PyiCloudService(apple_id, password)
            
            # Handle 2FA if needed
            if api.requires_2fa:
                if stage: stage.active_status = "2FA Required"
                from logic.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow
                from logic.gui.engine import setup_gui_environment
                setup_gui_environment()
                
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
                        if stage: stage.report_error("2FA Failed", "Invalid 2FA code.")
                        return False
                else:
                    if stage: stage.report_error("2FA Cancelled", "Verification interrupted.")
                    return False
            
            # Success! save session
            save_session(apple_id, api)
            final_apple_id = apple_id
            if stage: 
                # UI Request: iCloud green bold
                stage.success_status = f"{BOLD}{GREEN}iCloud{RESET}"
                stage.success_name = f"authenticated as {final_apple_id}"
            return True
            
        except Exception as e:
            if stage: stage.report_error("Session Error", str(e))
            return False

    pm = ProgressTuringMachine(
        project_root=tool.project_root, 
        tool_name="iCloudPD",
        log_dir=tool.get_log_dir()
    )
    pm.add_stage(TuringStage(
        "auth", auth_action,
        active_status="Authenticating", active_name="iCloud",
        success_status="Authenticated",
        fail_status="Failed",
    ))
    
    if not pm.run():
        sys.exit(1)

    apple_id = final_apple_id

    # 2. Scanning / Caching
    data_dir = tool.get_data_dir() / "scan" / apple_id
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_file = data_dir / "photos_cache.json"
    
    # Organized by YYYY-MM-DD -> list of assets
    all_photos_meta = {}
    used_cache = False
    
    def scan_action(stage=None):
        nonlocal all_photos_meta, used_cache
        if not args.force_rescan and cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    all_photos_meta = json.load(f)
                
                used_cache = True
                if stage:
                    # Flatten nested dict (Year -> Month -> Day -> [assets]) to count total
                    total = 0
                    for y in all_photos_meta.values():
                        if isinstance(y, dict):
                            for m in y.values():
                                for d in m.values():
                                    total += len(d)
                    # UI Request: Found bold only (default color)
                    stage.success_status = f"{BOLD}Found{RESET}"
                    stage.success_name = f"{total} photos/videos in {apple_id}'s iCloud Photos"
                return True
            except Exception:
                pass
            
        # Perform scan across all available libraries
        total_count = 0
        libs = {}
        try:
            libs = api.photos.libraries
            for lib in libs.values():
                try: total_count += len(lib.all)
                except: pass
        except:
            try:
                total_count = len(api.photos.all)
                libs = {"root": api.photos}
            except:
                total_count = 0
                libs = {}

        count = 0
        start_time = time.time()
        last_save_time = start_time
        last_seen_date = None # Track date changes for flushing
        
        from logic.utils import calculate_eta
        from pyicloud.services.photos import DirectionEnum
        
        for lib_name, lib in libs.items():
            if not hasattr(lib, "all"): continue
                
            if stage: stage.active_name = f"Preparing library: {lib_name}"
            
            album = lib.all
            # DESCENDING for newest-to-oldest scanning
            album._direction = DirectionEnum.DESCENDING
            offset = 0
            page_size = 100
            
            while True:
                try:
                    batch = list(album._get_photos_at(offset, album._direction, page_size))
                except Exception as e:
                    if stage: stage.report_error("Scan Error", f"Failed to fetch batch at offset {offset}: {e}")
                    break
                    
                if not batch: break
                    
                num_results = 0
                batch_dates = set()
                
                for photo in batch:
                    created = photo.created
                    if created:
                        year = str(created.year)
                        month = f"{created.month:02d}"
                        day = f"{created.day:02d}"
                        date_str = f"{year}-{month}-{day}"
                    else:
                        year, month, day = "unknown", "unknown", "unknown"
                        date_str = "unknown"
                    
                    batch_dates.add(date_str)
                        
                    asset = {
                        "id": photo.id,
                        "filename": photo.filename,
                        "created": created.isoformat() if created else None,
                        "size": photo.size,
                        "dimensions": photo.dimensions,
                        "library": lib_name,
                        "item_type": photo.item_type
                    }
                    
                    if year not in all_photos_meta: all_photos_meta[year] = {}
                    if month not in all_photos_meta[year]: all_photos_meta[year][month] = {}
                    if day not in all_photos_meta[year][month]: all_photos_meta[year][month][day] = []
                    
                    # Update or append
                    existing_ids = {a["id"] for a in all_photos_meta[year][month][day]}
                    if asset["id"] not in existing_ids:
                        all_photos_meta[year][month][day].append(asset)
                    
                    count += 1
                    num_results += 1
                
                # Logic: If batch has multiple dates, or if current date != last date,
                # it means previous dates are likely finished. 
                # We trigger a save if:
                # 1. More than 1 date in this batch
                # 2. Latest date in batch != last_seen_date
                # 3. 30 seconds since last save
                
                current_time = time.time()
                should_save = False
                
                if len(batch_dates) > 1:
                    should_save = True
                
                latest_in_batch = sorted(list(batch_dates), reverse=True)[0]
                if last_seen_date and latest_in_batch != last_seen_date:
                    should_save = True
                last_seen_date = latest_in_batch
                
                if current_time - last_save_time > 30:
                    should_save = True
                
                if should_save:
                    save_photos_cache(apple_id, all_photos_meta)
                    last_save_time = current_time

                # Update progress
                elapsed = current_time - start_time
                elapsed_str, remaining_str = calculate_eta(count, total_count, elapsed)
                
                status = f"iCloud photos/videos ({count}/{total_count or '???'}) [{elapsed_str}>{remaining_str}]"
                if stage: 
                    stage.active_name = status
                    stage.refresh()
                
                offset += num_results
            
        # Final save
        save_photos_cache(apple_id, all_photos_meta)
        
        if stage:
            total = 0
            for y in all_photos_meta.values():
                if isinstance(y, dict):
                    for m in y.values():
                        for d in m.values():
                            total += len(d)
            # UI Request: Found bold only
            stage.success_status = f"{BOLD}Found{RESET}"
            stage.success_name = f"{total} photos/videos in {apple_id}'s iCloud Photos"
        return True

    pm = ProgressTuringMachine(
        project_root=tool.project_root, 
        tool_name="iCloudPD",
        log_dir=tool.get_log_dir()
    )
    pm.add_stage(TuringStage(
        "scan", scan_action, 
        active_status="Scanning", active_name="iCloud photos/videos",
        success_status=f"{BOLD}Found{RESET}", 
    ))
    pm.run()
    
    # Show warning if cache was used, AFTER the scan stage but BEFORE "Scan completed"
    if used_cache:
        YELLOW_BOLD = get_color("YELLOW", "\033[33m") + BOLD
        sys.stdout.write(f"\r\033[K{YELLOW_BOLD}Warning{RESET}: Using cached scan results. "
                         f"Run with {BOLD}--force-rescan{RESET} to refresh metadata (which may take some time).\n")
        sys.stdout.flush()

    if args.only_scan:
        print(f"{BOLD}{GREEN}Scan completed{RESET}. Metadata saved to {cache_file}")
        return
    
    # 3. Filtering and Scheduling
    since_date = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    before_date = datetime.strptime(args.before, "%Y-%m-%d").date() if args.before else None
    
    import fnmatch
    import re
    format_patterns = args.formats.split("|") if args.formats else None
    regex_pattern = re.compile(args.regex) if args.regex else None

    scheduled_ids = set()
    
    # Flatten nested dict (Year -> Month -> Day -> [assets]) for processing
    for y, y_data in all_photos_meta.items():
        if not isinstance(y_data, dict): continue
        for m, m_data in y_data.items():
            if not isinstance(m_data, dict): continue
            for d, day_assets in m_data.items():
                date_str = f"{y}-{m}-{d}"
                for p in day_assets:
                    # Regex Filter (on 'yyyy-mm-dd/filename')
                    full_path = f"{date_str}/{p['filename']}"
                    if regex_pattern and not regex_pattern.search(full_path):
                        continue
                        
                    # Date Filter
                    p_date = datetime.fromisoformat(p["created"]).date() if p["created"] else None
                    if since_date and (not p_date or p_date < since_date): continue
                    if before_date and (not p_date or p_date >= before_date): continue
                    
                    # Type Filter
                    item_type = p.get("item_type", "image")
                    if args.only_photos and item_type not in ["photo", "image"]: continue
                    if args.only_videos and item_type != "video": continue
                    
                    # Format Filter
                    if format_patterns:
                        filename = p.get("filename", "")
                        if not any(fnmatch.fnmatch(filename, pat) for pat in format_patterns):
                            continue

                    scheduled_ids.add(p["id"])
        
    print(f"{BOLD}Scheduled{RESET} {len(scheduled_ids)} photos/videos for download.")
    if not scheduled_ids:
        print("No photos/videos found matching the criteria.")
        return

    # 4. Parallel Downloading
    from logic.turing.models.worker import ParallelWorkerPool
    output_root = Path(args.output or ".").resolve()
    
    # We need photo objects for download. 
    to_download_objects = []
    
    def gather_action(stage=None):
        nonlocal to_download_objects
        total_scheduled = len(scheduled_ids)
        count = 0
        start_time = time.time()
        
        try:
            libs = api.photos.libraries
        except:
            libs = {"root": api.photos}
            
        from pyicloud.services.photos import DirectionEnum
        from logic.utils import calculate_eta
        
        for lib_name, lib in libs.items():
            if not hasattr(lib, "all"): continue
                
            album = lib.all
            # Use DESCENDING to find recent photos quickly
            album._direction = DirectionEnum.DESCENDING
            
            # Use iterator for more robust fetching
            for photo in album:
                if photo.id in scheduled_ids:
                    # Check for duplicates
                    if not any(p.id == photo.id for p in to_download_objects):
                        to_download_objects.append(photo)
                        count += 1
                        
                        # Update progress
                        if count % 10 == 0 or count == total_scheduled:
                            elapsed = time.time() - start_time
                            elapsed_str, remaining_str = calculate_eta(count, total_scheduled, elapsed)
                            status = f"photo/video objects ({count}/{total_scheduled}) [{elapsed_str}>{remaining_str}]"
                            if stage: 
                                stage.active_name = status
                                stage.refresh()
                            
                if len(to_download_objects) >= total_scheduled:
                    break
            
            if len(to_download_objects) >= total_scheduled:
                break
        return len(to_download_objects) > 0

    pm = ProgressTuringMachine(
        project_root=tool.project_root, 
        tool_name="iCloudPD",
        log_dir=tool.get_log_dir()
    )
    pm.add_stage(TuringStage(
        "gathering_objects", gather_action,
        active_status="Gathering", active_name="photo/video objects",
        success_status="\r\033[K", success_name=" " # Silent success
    ))
    if not pm.run():
        sys.exit(1)

    def download_worker(stage, photo, target_path):
        try:
            # Bypass photo.download() because it returns bytes and can be unstable for large files
            if 'original' not in photo.versions:
                if stage: stage.report_error("No original", f"Original version not found for {photo.filename}")
                return False
            
            download_url = photo.versions['original']['url']
            # Access the underlying session from the service
            response = photo._service.session.get(download_url, stream=True)
            
            if response.status_code != 200:
                if stage: stage.report_error(f"HTTP {response.status_code}", f"Failed to download {photo.filename}")
                return False
                
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: f.write(chunk)
            
            # Verify file size
            actual_size = target_path.stat().st_size
            if actual_size == 0:
                if stage: stage.report_error("0-byte file", f"Downloaded file {photo.filename} is empty.")
                return False
            
            return True
        except Exception as e:
            if stage: stage.report_error(f"Download Error", f"{photo.filename}: {e}")
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

    download_success = True
    if tasks:
        download_success = pool.run(tasks, success_callback=on_success)
        if download_success:
            # First and Last asset info for success message
            first_asset = to_download_objects[0]
            last_asset = to_download_objects[-1]
            first_str = f"{first_asset.created.strftime('%Y-%m-%d')}/{first_asset.filename}"
            last_str = f"{last_asset.created.strftime('%Y-%m-%d')}/{last_asset.filename}"
            
            print(f"{BOLD}{GREEN}Successfully downloaded{RESET} {len(tasks)} photos/videos "
                  f"from {BOLD}{first_str}{RESET} to {BOLD}{last_str}{RESET}.")
        else:
            print(f"\n{BOLD}{get_color('RED')}Completed{RESET} download task with some errors.")
    else:
        # Only show this if the previous stages were successful
        print(f"{BOLD}{GREEN}All photos/videos{RESET} already downloaded.")

if __name__ == "__main__":
    main()
