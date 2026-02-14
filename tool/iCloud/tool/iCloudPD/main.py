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
        cookie_dir = tool.get_data_dir() / apple_id
        cookie_dir.mkdir(parents=True, exist_ok=True)
        cookie_file = cookie_dir / "session.pkl"
        with open(cookie_file, 'wb') as f:
            pickle.dump(api.session.cookies, f)

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
            cookie_dir = tool.get_data_dir() / apple_id
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
                        stage.success_status = "Successfully"
                        stage.success_name = f"reused session for {final_apple_id}"
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
                    stage.success_status = "Successfully"
                    stage.success_name = f"authenticated {final_apple_id}"
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
                cookie_file = tool.get_data_dir() / apple_id / "session.pkl"
                with open(cookie_file, 'rb') as f:
                    api.session.cookies.update(pickle.load(f))
                final_apple_id = apple_id
                if stage: 
                    stage.success_status = "Successfully"
                    stage.success_name = f"reused session for {final_apple_id}"
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
                stage.success_status = "Successfully"
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
    
    all_photos_meta = []
    
    def scan_action(stage=None):
        nonlocal all_photos_meta
        if not args.force_rescan and cache_file.exists():
            with open(cache_file, 'r') as f:
                all_photos_meta = json.load(f)
            if stage:
                stage.success_name = f"{len(all_photos_meta)} photos/videos in {apple_id}'s iCloud Photos (cached)"
            return True
            
        # Perform scan across all available libraries (Private, Shared, etc.)
        total_count = 0
        try:
            # api.photos.libraries returns a dict of libraries
            libs = api.photos.libraries
            for lib in libs.values():
                try:
                    total_count += len(lib.all)
                except:
                    pass
        except:
            # Fallback to single library if libraries property fails
            try:
                total_count = len(api.photos.all)
                libs = {"root": api.photos}
            except:
                total_count = 0
                libs = {}

        count = 0
        start_time = time.time()
        from logic.utils import calculate_eta
        
        # Iterate through each library
        from pyicloud.services.photos import DirectionEnum
        
        for lib_name, lib in libs.items():
            # Skip shared streams for now as they use a different structure (no .all)
            if not hasattr(lib, "all"):
                continue
                
            if stage: stage.active_name = f"Preparing library: {lib_name}"
            
            album = lib.all
            # Use ASCENDING for more robust linear scanning from the beginning
            album._direction = DirectionEnum.ASCENDING
            offset = 0
            page_size = 100
            
            while True:
                # Call _get_photos_at directly to bypass pyicloud's buggy 
                # 'num_results < page_size // 2' termination condition
                try:
                    batch = list(album._get_photos_at(offset, album._direction, page_size))
                except Exception as e:
                    if stage: stage.report_error("Scan Error", f"Failed to fetch batch at offset {offset}: {e}")
                    break
                    
                if not batch:
                    # Actually reached the end
                    break
                    
                num_results = 0
                for photo in batch:
                    all_photos_meta.append({
                        "id": photo.id,
                        "filename": photo.filename,
                        "created": photo.created.isoformat() if photo.created else None,
                        "size": photo.size,
                        "dimensions": photo.dimensions,
                        "library": lib_name,
                        "item_type": photo.item_type # 'photo' or 'video'
                    })
                    count += 1
                    num_results += 1
                
                # Update progress and save incrementally after each batch
                elapsed = time.time() - start_time
                elapsed_str, remaining_str = calculate_eta(count, total_count, elapsed)
                
                if total_count > 0:
                    status = f"iCloud photos/videos ({count}/{total_count}) [{elapsed_str}>{remaining_str}]"
                else:
                    status = f"iCloud photos/videos ({count}/???) [{elapsed_str}>??:??]"
                
                if stage: 
                    stage.active_name = status
                    stage.refresh()
                
                # Incremental save
                with open(cache_file, 'w') as f:
                    json.dump(all_photos_meta, f, indent=2)
                
                offset += num_results
                # Do NOT break if num_results < page_size; only break if batch is empty.
            
        if stage:
            stage.success_name = f"{len(all_photos_meta)} photos/videos in {apple_id}'s iCloud Photos"
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
    
    # 3. Filtering and Scheduling
    since_date = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    before_date = datetime.strptime(args.before, "%Y-%m-%d").date() if args.before else None
    
    import fnmatch
    format_patterns = args.formats.split("|") if args.formats else None

    scheduled_ids = set()
    for p in all_photos_meta:
        # Date Filter
        p_date = datetime.fromisoformat(p["created"]).date() if p["created"] else None
        if since_date and (not p_date or p_date < since_date): continue
        if before_date and (not p_date or p_date >= before_date): continue
        
        # Type Filter
        item_type = p.get("item_type", "photo")
        if args.only_photos and item_type != "photo": continue
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
    # Iterate all libraries to find the ones in scheduled_ids using robust paging.
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
        for lib_name, lib in libs.items():
            if not hasattr(lib, "all"):
                continue
                
            album = lib.all
            album._direction = DirectionEnum.ASCENDING
            offset = 0
            page_size = 100
            
            while True:
                try:
                    batch = list(album._get_photos_at(offset, album._direction, page_size))
                except:
                    break
                    
                if not batch:
                    break
                    
                for photo in batch:
                    if photo.id in scheduled_ids:
                        to_download_objects.append(photo)
                        count += 1
                        
                        # Update progress
                        if count % 10 == 0 or count == total_scheduled:
                            now = time.time()
                            elapsed = now - start_time
                            elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed))
                            rate = count / elapsed if elapsed > 0 else 0
                            remaining = (total_scheduled - count) / rate if rate > 0 else 0
                            remaining_str = time.strftime("%M:%S", time.gmtime(remaining))
                            status = f"photo/video objects ({count}/{total_scheduled}) [{elapsed_str}>{remaining_str}]"
                            if stage: 
                                stage.active_name = status
                                stage.refresh()
                            
                    if len(to_download_objects) >= total_scheduled:
                        break
                
                if len(to_download_objects) >= total_scheduled:
                    break
                
                offset += len(batch)
                if len(batch) < page_size:
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
        "gather", gather_action,
        active_status="Gathering", active_name="photo/video objects",
        success_status="Ready", success_name=f"{len(scheduled_ids)} photos/videos"
    ))
    pm.run()

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
