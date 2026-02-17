#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
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
    tool = ToolBase("iCloud.iCloudPD")
    
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
    parser.add_argument("--no-warning", action="store_true", help="Suppress warning messages in progress display")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    BOLD, GREEN, BLUE, RESET, YELLOW, RED = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET"), get_color("YELLOW"), get_color("RED")
    
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
        
        if args.no_gui:
            import getpass
            import pickle
            try:
                apple_id = args.apple_id or input("\nEnter Apple ID: ").strip()
            except (EOFError, KeyboardInterrupt) as e:
                msg = "Operation not supported by device" if isinstance(e, EOFError) else "Cancelled by user"
                if stage: stage.report_error(f"Input Error: {msg}", msg)
                return False

            cookie_file = tool.get_data_dir() / "session" / apple_id / "session.pkl"
            if cookie_file.exists():
                try:
                    if stage: stage.active_name = f"reusing session for {apple_id}"
                    api = PyiCloudService(apple_id, "")
                    with open(cookie_file, 'rb') as f:
                        api.session.cookies.update(pickle.load(f))
                    _ = api.account.devices
                    final_apple_id = apple_id
                    if stage: 
                        stage.success_status = "Reused session"
                        stage.success_color = "BOLD"
                        stage.success_name = f"for {final_apple_id}"
                    return True
                except: pass
            
            try:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                # User wants a key icon for security feel in CLI mode
                prompt = f"Enter password for {apple_id}: "
                password = getpass.getpass(prompt)
            except (EOFError, Exception) as e:
                msg = str(e) or "Non-interactive terminal"
                if stage: stage.report_error(f"CLI Error: {msg}", msg)
                return False

            try:
                if stage: stage.active_name = f"authenticating {apple_id}"
                api = PyiCloudService(apple_id, password)
                if api.requires_2fa:
                    print(f"\n{BOLD}{YELLOW}Two-factor authentication required.{RESET}")
                    try: code = input("Enter 6-digit 2FA code: ").strip()
                    except EOFError: return False
                    if not api.validate_2fa_code(code): return False
                
                save_session(apple_id, api)
                final_apple_id = apple_id
                sys.stdout.write("\033[F\033[K")
                sys.stdout.flush()
                if stage: 
                    stage.success_status = "iCloud"
                    stage.success_color = "GREEN"
                    stage.success_name = f"authenticated as {final_apple_id}"
                return True
            except Exception as e:
                if stage: stage.report_error("Login Failed", str(e))
                return False

        login_res = icloud["run_login_gui"](apple_id=args.apple_id)
        if login_res.get("status") != "success":
            if stage: stage.report_error("Login cancelled", "Login cancelled.")
            return False
            
        creds = login_res["data"]
        apple_id = creds["apple_id"]
        if creds.get("mode") == "session_reuse":
            import pickle
            try:
                api = PyiCloudService(apple_id, "")
                cookie_file = tool.get_data_dir() / "session" / apple_id / "session.pkl"
                with open(cookie_file, 'rb') as f:
                    api.session.cookies.update(pickle.load(f))
                final_apple_id = apple_id
                if stage: 
                    stage.success_status = "Reused session"
                    stage.success_color = "BOLD"
                    stage.success_name = f"for {final_apple_id}"
                return True
            except: return False

        password = creds["password"]
        try:
            api = PyiCloudService(apple_id, password)
            if api.requires_2fa:
                from logic.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow
                from logic.gui.engine import setup_gui_environment
                setup_gui_environment()
                
                def v_handler(code):
                    if api.validate_2fa_code(code):
                        return {"status": "success", "data": code}
                    else:
                        return {"status": "error", "message": "Invalid 2FA code."}

                win = TwoFactorAuthWindow(title="iCloud 2FA", timeout=300, internal_dir=str(tool.tool_dir / "logic"), n=6, verify_handler=v_handler)
                win.run(win.setup_ui)
                if win.result.get("status") != "success":
                    return False
            
            save_session(apple_id, api)
            final_apple_id = apple_id
            if stage: 
                stage.success_status = "iCloud"
                stage.success_color = "GREEN"
                stage.success_name = f"authenticated as {final_apple_id}"
            return True
        except Exception as e:
            if stage: stage.report_error("Session Error", str(e))
            return False

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD", log_dir=tool.get_log_dir(), no_warning=args.no_warning)
    pm.add_stage(TuringStage(
        "iCloud account", auth_action, 
        active_status="Authenticating", active_name="iCloud", 
        success_status="Successfully authenticated", success_name="iCloud", 
        fail_status="Failed to authenticate",
        bold_part="Authenticating iCloud"
    ))
    if not pm.run(): sys.exit(1)

    apple_id = final_apple_id

    # 2. Scanning / Caching
    cache_file = tool.get_data_dir() / "scan" / apple_id / "photos_cache.json"
    all_photos_meta = {}
    used_cache = False
    
    def scan_action(stage=None):
        nonlocal all_photos_meta, used_cache
        if not args.force_rescan and cache_file.exists():
            try:
                with open(cache_file, 'r') as f: all_photos_meta = json.load(f)
                used_cache = True
                if stage:
                    total = sum(len(d) for y in all_photos_meta.values() for m in y.values() for d in m.values() if isinstance(y, dict) and isinstance(m, dict))
                    stage.success_status, stage.success_color = "Found", "BOLD"
                    stage.success_name = f"{total} photos/videos in {apple_id}'s iCloud Photos"
                return True
            except: pass
            
        total_count = 0
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
                total_count, libs = 0, {}

        count, start_time = 0, time.time()
        last_save_time, last_seen_date = start_time, None
        from logic.utils import calculate_eta
        from pyicloud.services.photos import DirectionEnum
        
        for lib_name, lib in libs.items():
            if not hasattr(lib, "all"): continue
            album = lib.all
            album._direction = DirectionEnum.ASCENDING # Newest first in this version
            offset, page_size = 0, 100
            
            while True:
                try: batch = list(album._get_photos_at(offset, album._direction, page_size))
                except Exception as e:
                    if stage: stage.report_error("Scan Error", str(e))
                    break
                if not batch: break
                    
                batch_dates = set()
                for photo in batch:
                    created = photo.created
                    if created:
                        year, month, day = str(created.year), f"{created.month:02d}", f"{created.day:02d}"
                        date_str = f"{year}-{month}-{day}"
                    else: year, month, day, date_str = "unknown", "unknown", "unknown", "unknown"
                    
                    batch_dates.add(date_str)
                    asset = {"id": photo.id, "filename": photo.filename, "created": created.isoformat() if created else None,
                             "size": photo.size, "dimensions": photo.dimensions, "library": lib_name, "item_type": photo.item_type}
                    
                    if year not in all_photos_meta: all_photos_meta[year] = {}
                    if month not in all_photos_meta[year]: all_photos_meta[year][month] = {}
                    if day not in all_photos_meta[year][month]: all_photos_meta[year][month][day] = []
                    
                    existing_ids = {a["id"] for a in all_photos_meta[year][month][day]}
                    if asset["id"] not in existing_ids: all_photos_meta[year][month][day].append(asset)
                    count += 1
                
                curr_t = time.time()
                should_save = len(batch_dates) > 1 or (last_seen_date and sorted(list(batch_dates), reverse=True)[0] != last_seen_date) or (curr_t - last_save_time > 30)
                if should_save:
                    save_photos_cache(apple_id, all_photos_meta)
                    last_save_time = curr_t
                last_seen_date = sorted(list(batch_dates), reverse=True)[0]

                elapsed = curr_t - start_time
                e_str, r_str = calculate_eta(count, total_count, elapsed)
                if stage: 
                    stage.active_name = f"iCloud photos/videos ({count}/{total_count or '???'}) [{e_str}>{r_str}]"
                    stage.refresh()
                offset += len(batch)
            
        save_photos_cache(apple_id, all_photos_meta)
        if stage:
            total = sum(len(d) for y in all_photos_meta.values() for m in y.values() for d in m.values() if isinstance(y, dict) and isinstance(m, dict))
            stage.success_status, stage.success_color = "Found", "BOLD"
            stage.success_name = f"{total} photos/videos in {apple_id}'s iCloud Photos"
        return True

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD", log_dir=tool.get_log_dir(), no_warning=args.no_warning)
    pm.add_stage(TuringStage(
        "iCloud photos/videos", scan_action, 
        active_status="Scanning", success_status="Successfully scanned", fail_status="Failed to scan",
        bold_part="Scanning iCloud photos/videos"
    ))
    pm.run()
    
    if used_cache:
        YELLOW_BOLD = get_color("YELLOW", "\033[33m") + BOLD
        sys.stdout.write(f"\r\033[K{YELLOW_BOLD}Warning{RESET}: Using cached scan results. Run with {BOLD}--force-rescan{RESET} to refresh metadata (which may take some time).\n")
        sys.stdout.flush()

    if args.only_scan:
        print(f"{BOLD}{GREEN}Scan completed{RESET}. Metadata saved to {cache_file}")
        return
    
    # 3. Filtering and Scheduling
    since_date = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    before_date = datetime.strptime(args.before, "%Y-%m-%d").date() if args.before else None
    import fnmatch, re
    format_patterns = args.formats.split("|") if args.formats else None
    regex_pattern = re.compile(args.regex) if args.regex else None

    scheduled_id_info = {}
    for y, y_data in all_photos_meta.items():
        if not isinstance(y_data, dict): continue
        for m, m_data in y_data.items():
            if not isinstance(m_data, dict): continue
            for d, day_assets in m_data.items():
                date_str = f"{y}-{m}-{d}"
                for p in day_assets:
                    full_path = f"{date_str}/{p['filename']}"
                    if regex_pattern and not regex_pattern.search(full_path): continue
                    p_date = datetime.fromisoformat(p["created"]).date() if p["created"] else None
                    if since_date and (not p_date or p_date < since_date): continue
                    if before_date and (not p_date or p_date > before_date): continue
                    item_type = p.get("item_type", "image")
                    if args.only_photos and item_type not in ["photo", "image"]: continue
                    if args.only_videos and item_type != "video": continue
                    if format_patterns and not any(fnmatch.fnmatch(p.get("filename", ""), pat) for pat in format_patterns): continue
                    scheduled_id_info[p["id"]] = {"lib_name": p.get("library", "root"), "created": p_date, "filename": p.get("filename")}
        
    # Filter out already downloaded files BEFORE gathering
    final_scheduled_info = {}
    output_root = Path(args.output or ".").resolve()
    already_downloaded_count = 0
    for aid, info in scheduled_id_info.items():
        p_date_str = info["created"].strftime("%Y-%m-%d") if info["created"] else "unknown"
        target_file = output_root / p_date_str / info["filename"]
        # Note: Collision protection might change final filename, but if the original exists, we skip.
        if target_file.exists():
            already_downloaded_count += 1
            continue
        final_scheduled_info[aid] = info
    
    if already_downloaded_count > 0:
        print(f"{BOLD}Skipped{RESET} {already_downloaded_count} photos/videos already downloaded.")
    
    scheduled_id_info = final_scheduled_info
    print(f"{BOLD}Scheduled{RESET} {len(scheduled_id_info)} photos/videos for download.")
    if not scheduled_id_info: return

    # 4. Parallel Downloading
    from logic.turing.models.worker import ParallelWorkerPool
    output_root = Path(args.output or ".").resolve()
    to_download_objects = []
    
    def gather_action(stage=None):
        nonlocal to_download_objects
        total_scheduled = len(scheduled_id_info)
        count, start_time = 0, time.time()
        lib_to_ids = {}
        for aid, info in scheduled_id_info.items():
            lib_name = info["lib_name"]
            if lib_name not in lib_to_ids: lib_to_ids[lib_name] = []
            lib_to_ids[lib_name].append(aid)
            
        from pyicloud.services.photos import PhotoAsset
        for lib_name, ids in lib_to_ids.items():
            try: lib_obj = api.photos.libraries[lib_name]
            except: continue
            base_url = lib_obj.url.split("/query")[0]
            lookup_url = f"{base_url}/lookup"
            for i in range(0, len(ids), 100):
                batch_ids = ids[i:i+100]
                query = {"records": [{"recordName": rid} for rid in batch_ids], "zoneID": lib_obj.zone_id}
                
                max_retries = 3
                last_error_details = ""
                success_batch = False
                
                for attempt in range(max_retries):
                    try:
                        resp = api.photos.session.post(lookup_url, json=query, headers={"Content-Type": "text/plain"}, timeout=30)
                        if resp.status_code == 200:
                            for record in resp.json().get("records", []):
                                asset = PhotoAsset(api.photos, record, record)
                                aid = record["recordName"]
                                if aid in scheduled_id_info: asset._cached_date = scheduled_id_info[aid]["created"]
                                to_download_objects.append(asset)
                                count += 1
                                if count % 10 == 0 or count == total_scheduled:
                                    from logic.utils import calculate_eta
                                    e_str, r_str = calculate_eta(count, total_scheduled, time.time() - start_time)
                                    if stage: stage.active_name = f"photo/video objects ({count}/{total_scheduled}) [{e_str}>{r_str}]"; stage.refresh()
                            success_batch = True
                            break
                        else:
                            last_error_details = f"HTTP {resp.status_code}: {resp.text}"
                    except Exception as e:
                        last_error_details = str(e)
                    
                    if attempt < max_retries - 1:
                        time.sleep(1)
                
                if not success_batch:
                    if stage: 
                        stage.report_error("Gather Error", f"Request failed to iCloud after {max_retries} attempts: {last_error_details}")
                    return False
        return len(to_download_objects) > 0

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD", log_dir=tool.get_log_dir(), no_warning=args.no_warning)
    pm.add_stage(TuringStage(
        "photo/video objects", gather_action, 
        active_status="Gathering", success_status="Successfully gathered", fail_status="Failed to gather",
        bold_part="Gathering photo/video objects"
    ))
    if not pm.run(ephemeral=True, final_newline=False): sys.exit(1)

    def download_worker(stage, photo, target_path):
        max_attempts, last_err = 3, ""
        for attempt in range(max_attempts):
            try:
                if 'original' not in photo.versions: return False
                resp = photo._service.session.get(photo.versions['original']['url'], stream=True)
                if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
                with open(target_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                if target_path.stat().st_size == 0: raise Exception("0-byte file")
                return True
            except Exception as e:
                last_err = str(e)
                if attempt < max_attempts - 1: time.sleep(1)
        if stage: stage.report_error(f"Failed after {max_attempts} retries", last_err)
        return False

    pool = ParallelWorkerPool(max_workers=args.workers, status_label="Downloading", project_root=tool.project_root, tool_name="iCloudPD")
    pool.status_bar.set_counts(len(to_download_objects))
    tasks, failed_tasks = [], []
    used_paths = set()
    
    for photo in to_download_objects:
        p_date = getattr(photo, "_cached_date", None)
        p_date_str = p_date.strftime("%Y-%m-%d") if p_date else "unknown"
        target_dir = output_root / p_date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle filename collisions within the same date folder
        base_name = photo.filename
        target_file = target_dir / base_name
        
        if str(target_file) in used_paths:
            name, ext = os.path.splitext(base_name)
            counter = 1
            while True:
                target_file = target_dir / f"{name}_{counter}{ext}"
                if str(target_file) not in used_paths:
                    break
                counter += 1
        
        used_paths.add(str(target_file))
        
        if target_file.exists():
            pool.status_bar.increment_completed()
            continue
            
        tasks.append({"id": f"{p_date_str}/{target_file.name}", "action": download_worker, "args": (photo, target_file)})

    def on_task_result(task_id, res):
        if isinstance(res, dict) and not res.get("success", True):
            failed_tasks.append({"id": task_id, "error": res.get("error_brief", "Unknown error"), "log": res.get("log_path")})
        else: pool.status_bar.increment_completed()

    all_success = pool.run(tasks, success_callback=on_task_result)
    
    if not tasks and not failed_tasks:
        if already_downloaded_count > 0:
            print(f"{BOLD}{GREEN}All scheduled photos/videos are already downloaded.{RESET}")
        return

    if all_success and not failed_tasks:
        first, last = to_download_objects[0], to_download_objects[-1]
        f_d, l_d = getattr(first, "_cached_date", None), getattr(last, "_cached_date", None)
        f_s, l_s = f"{f_d.strftime('%Y-%m-%d') if f_d else 'unknown'}/{first.filename}", f"{l_d.strftime('%Y-%m-%d') if l_d else 'unknown'}/{last.filename}"
        print(f"{BOLD}{GREEN}Successfully downloaded{RESET} {len(tasks)} photos/videos from {BOLD}{f_s}{RESET} to {BOLD}{l_s}{RESET}.")
    elif failed_tasks:
        print(f"{BOLD}{RED}Failed to download{RESET} {len(failed_tasks)} photos/videos.")
        summary_log = tool.get_log_dir() / f"fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_download_summary.log"
        with open(summary_log, 'w') as f:
            for ft in failed_tasks: f.write(f"ID: {ft['id']} | Error: {ft['error']} | Detail: {ft['log']}\n")
        print(f"{BOLD}Reason:{RESET} {failed_tasks[0]['error']}... {BOLD}Full log saved to:{RESET} {summary_log}")

if __name__ == "__main__":
    main()
