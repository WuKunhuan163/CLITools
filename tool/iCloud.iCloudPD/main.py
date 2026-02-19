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
import signal
from pathlib import Path
from datetime import datetime, date
import subprocess

def log_debug(msg):
    try:
        with open("/tmp/icloudpd_debug.log", "a") as f:
            f.write(f"[{time.time()}] {msg}\n")
            f.flush()
    except: pass

def global_sigint_handler(sig, frame):
    log_debug(f"SIGINT caught at {time.time()}")
    
    # Release keyboard suppression BEFORE exiting
    from logic.terminal.keyboard import get_global_suppressor
    try:
        get_global_suppressor().stop(force=True)
        log_debug("Keyboard suppressor stopped in signal handler.")
    except Exception as e:
        log_debug(f"Error stopping suppressor in SIGINT handler: {e}")
        
    # Use hardcoded codes for reliability
    sys.stdout.write("\r\033[K\033[1;31mOperation cancelled\033[0m by user.\n")
    sys.stdout.flush()
    os._exit(130)

signal.signal(signal.SIGINT, global_sigint_handler)
log_debug("Global SIGINT handler registered")

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
    parser.add_argument("--output", default="/Applications/AITerminalTools/tmp/tmp_iCloudPD_photos/", help="Target directory for downloads (default: tmp/tmp_iCloudPD_photos/)")
    parser.add_argument("--force-rescan", action="store_true", help="Force rescan of iCloud photo/video library")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel download workers (default: 3)")
    parser.add_argument("--no-gui", action="store_true", default=True, help="Use CLI-only interaction (default: True)")
    parser.add_argument("--only-photos", action="store_true", help="Only download photos")
    parser.add_argument("--only-videos", action="store_true", help="Only download videos")
    parser.add_argument("--formats", type=str, help="Filter by extensions, e.g. '*.png|*.jpg'")
    parser.add_argument("--regex", type=str, help="Regex filter for 'yyyy-mm-dd/filename'")
    parser.add_argument("--only-scan", action="store_true", help="Only scan and cache metadata, do not download")
    parser.add_argument("--no-warning", action="store_true", help="Suppress warning messages in progress display")
    parser.add_argument("--local-photos", nargs='?', const='default', help="Check local Photos Library before downloading from iCloud. If path is omitted, the default ~/Pictures/Photos Library.photoslibrary is used.")
    parser.add_argument("--prefix", type=str, default="", help="Prefix for the photo filename (supports placeholders: <YYYY>, <MM>, <DD>, <hh>, <mm>, <ss>, <ID>, <FILENAME>)")
    parser.add_argument("--suffix", type=str, default="", help="Suffix for the photo filename (supports placeholders)")
    parser.add_argument("--grouping", type=str, default="<YYYY>-<MM>-<DD>", help="Directory grouping rule (default: <YYYY>-<MM>-<DD>)")
    parser.add_argument("--ignore-gather-cache", action="store_true", help="Ignore gathered metadata fields in cache and force fresh gathering from iCloud")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    BOLD, GREEN, BLUE, RESET, YELLOW, RED = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET"), get_color("YELLOW"), get_color("RED")
    
    # 0. Local Photos Library Setup
    local_library = None
    if args.local_photos:
        library_path = None
        if args.local_photos == 'default':
            if not args.no_gui:
                from logic.gui.manager import run_gui_subprocess
                fd_tool = ToolBase("FILEDIALOG")
                fd_script = str(project_root / "tool" / "FILEDIALOG" / "main.py")
                
                # Default path
                default_lib = Path.home() / "Pictures" / "Photos Library.photoslibrary"
                
                # Build arguments for FILEDIALOG
                fd_args = [
                    "--title", "Select Apple Photos Library (.photoslibrary)",
                    "--dir", str(default_lib.parent),
                    "--directory"
                ]
                
                res = run_gui_subprocess(fd_tool, sys.executable, fd_script, 300, args=fd_args)
                if res.get("status") == "success":
                    library_path = Path(res["data"])
            
            if not library_path:
                # Fallback to default if no GUI or cancelled
                library_path = Path.home() / "Pictures" / "Photos Library.photoslibrary"
        else:
            library_path = Path(args.local_photos)
            
        if library_path and library_path.exists():
            from tool.iCloud.logic.local.photos import LocalPhotosLibrary # Moved to shared logic
            local_library = LocalPhotosLibrary(library_path)
            if not local_library.is_valid():
                print(f"{BOLD}{YELLOW}Warning{RESET}: '{library_path}' does not appear to be a valid Photos Library (missing 'originals' folder).")
                local_library = None
            else:
                pass # Local library confirmed
        else:
            print(f"{BOLD}{RED}Error{RESET}: Local photos library path '{library_path}' does not exist.")
            sys.exit(1)
    
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
        from logic.terminal.keyboard import get_global_suppressor
        suppressor = get_global_suppressor()
        
        if args.no_gui:
            import getpass
            import pickle
            
            was_suppressed = suppressor.is_suppressed()
            try:
                if was_suppressed: suppressor.stop()
                apple_id = args.apple_id or input("\nEnter Apple ID: ").strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt
            finally:
                if was_suppressed: suppressor.start()

            cookie_file = tool.get_data_dir() / "session" / apple_id / "session.pkl"
            if cookie_file.exists():
                # ... session reuse logic ...
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
                except KeyboardInterrupt:
                    raise
                except Exception: pass
            
            try:
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                # User wants a key icon for security feel in CLI mode
                prompt = f"Enter password for {apple_id}: "
                
                was_suppressed = suppressor.is_suppressed()
                if was_suppressed: suppressor.stop()
                try:
                    password = getpass.getpass(prompt)
                finally:
                    if was_suppressed: suppressor.start()
            except KeyboardInterrupt:
                raise
            except (EOFError, Exception) as e:
                msg = str(e) or "Non-interactive terminal"
                if stage: stage.report_error(f"CLI Error: {msg}", msg)
                return False

            try:
                if stage: stage.active_name = f"authenticating {apple_id}"
                api = PyiCloudService(apple_id, password)
                if api.requires_2fa:
                    print(f"\n{BOLD}{YELLOW}Two-factor authentication required.{RESET}")
                    
                    was_suppressed = suppressor.is_suppressed()
                    if was_suppressed: suppressor.stop()
                    try:
                        code = input("Enter 6-digit 2FA code: ").strip()
                    finally:
                        if was_suppressed: suppressor.start()
                    
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
                res = win.result
                if win.root:
                    try: win.root.destroy()
                    except: pass
                if res.get("status") != "success":
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

    def substitute_tags(template, date_obj, asset_id, filename):
        if not template: return ""
        res = template
        if date_obj:
            res = res.replace("<YYYY>", date_obj.strftime("%Y"))
            res = res.replace("<MM>", date_obj.strftime("%m"))
            res = res.replace("<DD>", date_obj.strftime("%d"))
            res = res.replace("<hh>", date_obj.strftime("%H"))
            res = res.replace("<mm>", date_obj.strftime("%M"))
            res = res.replace("<ss>", date_obj.strftime("%S"))
        res = res.replace("<ID>", asset_id)
        res = res.replace("<FILENAME>", filename)
        return res

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
                    p_datetime = datetime.fromisoformat(p["created"]) if p["created"] else None
                    p_date = p_datetime.date() if p_datetime else None
                    if since_date and (not p_date or p_date < since_date): continue
                    if before_date and (not p_date or p_date > before_date): continue
                    item_type = p.get("item_type", "image")
                    if args.only_photos and item_type not in ["photo", "image"]: continue
                    if args.only_videos and item_type != "video": continue
                    if format_patterns and not any(fnmatch.fnmatch(p.get("filename", ""), pat) for pat in format_patterns): continue
                    scheduled_id_info[p["id"]] = {"lib_name": p.get("library", "root"), "created": p_datetime, "filename": p.get("filename")}
        
    def get_target_path(photo_id, filename, created_time):
        """Helper to consistently resolve target path for a photo."""
        dir_name = substitute_tags(args.grouping, created_time, photo_id, filename)
        target_dir = output_root / dir_name
        
        prefix = substitute_tags(args.prefix, created_time, photo_id, filename)
        suffix = substitute_tags(args.suffix, created_time, photo_id, filename)
        
        name, ext = os.path.splitext(filename)
        base_name = f"{prefix}{name}{suffix}{ext}"
        return target_dir / base_name

    # Filter out already downloaded files BEFORE gathering
    final_scheduled_info = {}
    output_root = Path(args.output or ".").resolve()
    already_downloaded_count = 0
    for aid, info in scheduled_id_info.items():
        # Correctly resolve the target path
        target_file = get_target_path(aid, info["filename"], info["created"])
        
        if target_file.exists():
            already_downloaded_count += 1
            continue
        final_scheduled_info[aid] = info
    
    if already_downloaded_count > 0:
        print(f"{BOLD}Skipped{RESET} {already_downloaded_count} photos/videos already downloaded.")
    
    scheduled_id_info = final_scheduled_info
    print(f"{BOLD}Scheduled{RESET} {len(scheduled_id_info)} photos/videos for download.")
    if not scheduled_id_info: return

    # Display local library usage just before gathering
    if local_library:
        print(f"{BOLD}Using local library{RESET}: {local_library.library_path}")

    # 4. Parallel Downloading
    from logic.turing.models.worker import ParallelWorkerPool
    output_root = Path(args.output or ".").resolve()
    to_download_objects = []

    class LocalAssetStub:
        def __init__(self, asset_id, filename, created):
            self.id = asset_id
            self.filename = filename
            self.created = created
            self.versions = {} # Prevent AttributeError in fallback
            self._service = None
    
    def gather_action(stage=None):
        log_debug("Starting gather_action")
        nonlocal to_download_objects, all_photos_meta
        total_scheduled = len(scheduled_id_info)
        count, start_time = 0, time.time()
        last_cache_save = start_time
        
        # Build a fast lookup map for already gathered records in cache
        gathering_lookup = {}
        if not args.ignore_gather_cache:
            log_debug(f"Building gathering lookup from all_photos_meta (years: {list(all_photos_meta.keys())})")
            for y, y_data in all_photos_meta.items():
                if not isinstance(y_data, dict): continue
                for m, m_data in y_data.items():
                    if not isinstance(m_data, dict): continue
                    for d, day_assets in m_data.items():
                        for ca in day_assets:
                            if "full_record" in ca:
                                gathering_lookup[ca["id"]] = ca["full_record"]
            log_debug(f"Lookup built: {len(gathering_lookup)} items")
        
        # Split IDs into resolved (local or gathering-cache) and needs-iCloud-lookup
        needs_lookup_ids = {} # lib_name -> [ids]
        
        # Preload mappings if using local library
        if local_library:
            log_debug("Preloading local library mappings")
            local_library.preload_mappings(list(scheduled_id_info.keys()))
            
        from pyicloud.services.photos import PhotoAsset
        log_debug(f"Iterating through {total_scheduled} scheduled IDs")
        for aid, info in scheduled_id_info.items():
            lib_name = info["lib_name"]
            is_resolved = False
            
            # 1. Check local library first if available
            if local_library:
                local_res = local_library.find_photo(aid, filename=info["filename"], created_dt=info["created"])
                if local_res:
                    _, local_dt = local_res
                    to_download_objects.append(LocalAssetStub(aid, info["filename"], local_dt))
                    count += 1
                    is_resolved = True
            
            # 2. Check gathering cache (lookup map built from photos_cache.json)
            if not is_resolved and aid in gathering_lookup:
                try:
                    asset = PhotoAsset(api.photos, gathering_lookup[aid], gathering_lookup[aid])
                    asset._cached_date = info["created"]
                    to_download_objects.append(asset)
                    count += 1
                    is_resolved = True
                except: pass
            
            if is_resolved:
                # Update progress for resolved items periodically
                if count % 100 == 0 or count == total_scheduled:
                    from logic.utils import calculate_eta
                    e_str, r_str = calculate_eta(count, total_scheduled, time.time() - start_time)
                    if stage: stage.active_name = f"photo/video objects ({count}/{total_scheduled}) [{e_str}>{r_str}]"; stage.refresh()
            else:
                if lib_name not in needs_lookup_ids: needs_lookup_ids[lib_name] = []
                needs_lookup_ids[lib_name].append(aid)
        
        # Warning if resolved count is incomplete
        missing_count = sum(len(ids) for ids in needs_lookup_ids.values())
        log_debug(f"Resolved {count} items, {missing_count} items need iCloud lookup")
        if missing_count > 0:
            # Erase current line
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            if local_library:
                print(f"{BOLD}{YELLOW}Warning{RESET}: {missing_count} photos not found in local library (and not in gather cache). Gathering metadata from iCloud...")
            else:
                print(f"{BOLD}{YELLOW}Warning{RESET}: {missing_count} photos not in gather cache. Gathering metadata from iCloud...")
            if stage: stage.refresh() # Restore active line below warning

        if not needs_lookup_ids:
            log_debug("All items resolved, finishing gather_action")
            return len(to_download_objects) > 0
            
        for lib_name, ids in needs_lookup_ids.items():
            try: lib_obj = api.photos.libraries[lib_name]
            except: 
                log_debug(f"Library {lib_name} not found")
                continue
            base_url = lib_obj.url.split("/query")[0]
            lookup_url = f"{base_url}/lookup"
            log_debug(f"Starting iCloud lookup for {len(ids)} items from {lib_name}")
            for i in range(0, len(ids), 100):
                batch_ids = ids[i:i+100]
                query = {"records": [{"recordName": rid} for rid in batch_ids], "zoneID": lib_obj.zone_id}
                
                max_retries = 3
                last_error_details = ""
                success_batch = False
                
                log_debug(f"Requesting batch {i//100 + 1}/{(len(ids)-1)//100 + 1} ({len(batch_ids)} items)")
                for attempt in range(max_retries):
                    try:
                        resp = api.photos.session.post(lookup_url, json=query, headers={"Content-Type": "text/plain"}, timeout=30)
                        if resp.status_code == 200:
                            log_debug(f"Batch success, parsing {len(resp.json().get('records', []))} records")
                            for record in resp.json().get("records", []):
                                asset = PhotoAsset(api.photos, record, record)
                                aid = record["recordName"]
                                if aid in scheduled_id_info:
                                    dt = scheduled_id_info[aid]["created"]
                                    asset._cached_date = dt
                                    
                                    # Update cache with full_record and better metadata
                                    y, m, d = str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}"
                                    if y in all_photos_meta and m in all_photos_meta[y] and d in all_photos_meta[y][m]:
                                        for ca in all_photos_meta[y][m][d]:
                                            if ca["id"] == aid:
                                                ca["item_type"] = asset.item_type
                                                ca["size"] = asset.size
                                                ca["dimensions"] = asset.dimensions
                                                ca["full_record"] = record # Store record for future runs
                                                break
                                                
                                to_download_objects.append(asset)
                                count += 1
                                if count % 10 == 0 or count == total_scheduled:
                                    from logic.utils import calculate_eta
                                    e_str, r_str = calculate_eta(count, total_scheduled, time.time() - start_time)
                                    if stage: stage.active_name = f"photo/video objects ({count}/{total_scheduled}) [{e_str}>{r_str}]"; stage.refresh()
                                    
                            # Save cache after each batch of 100 (as requested by user)
                            save_photos_cache(apple_id, all_photos_meta)
                            last_cache_save = time.time()
                                    
                            success_batch = True
                            break
                        else:
                            last_error_details = f"HTTP {resp.status_code}: {resp.text}"
                    except Exception as e:
                        last_error_details = str(e)
                    
                    if attempt < max_retries - 1:
                        log_debug(f"Batch retry {attempt+1} due to {last_error_details}")
                        time.sleep(1)
                
                if not success_batch:
                    log_debug(f"Batch FAILED after {max_retries} attempts: {last_error_details}")
                    if stage: 
                        stage.report_error("Gather Error", f"Request failed to iCloud after {max_retries} attempts: {last_error_details}")
                    return False
        
        log_debug("Gathering finished, saving final cache")
        save_photos_cache(apple_id, all_photos_meta)
        
        # Final safety: Ensure uniqueness in to_download_objects by asset ID
        seen_ids = set()
        unique_objs = []
        for obj in to_download_objects:
            if obj.id not in seen_ids:
                unique_objs.append(obj)
                seen_ids.add(obj.id)
        to_download_objects = unique_objs
        log_debug(f"Final to_download_objects count: {len(to_download_objects)}")
        
        return len(to_download_objects) > 0

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="iCloudPD", log_dir=tool.get_log_dir(), no_warning=args.no_warning)
    pm.add_stage(TuringStage(
        "photo/video objects", gather_action, 
        active_status="Gathering", success_status="Successfully gathered", fail_status="Failed to gather",
        bold_part="Gathering photo/video objects"
    ))
    if not pm.run(ephemeral=True, final_newline=False): sys.exit(1)

    def download_worker(stage, photo, target_path, local_library=None):
        # First try local library if available
        if local_library:
            try:
                # Pass filename and date for robust fetch
                filename = getattr(photo, "filename", None)
                created_dt = getattr(photo, "created", None)
                if local_library.fetch_photo(photo.id, target_path, filename=filename, created_dt=created_dt):
                    return True
            except Exception:
                pass # Fallback to iCloud
        
        # If it was a LocalAssetStub and local fetch failed, we can't fallback to iCloud
        if isinstance(photo, LocalAssetStub):
            if stage: stage.report_error("Local Fetch Failed", f"Could not find {photo.filename} in local library originals.")
            return False
                
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
    
    tasks, failed_tasks = [], []
    used_paths = set()
    already_on_disk_count = 0
    baseline_count = 0 # Items that don't need remote time (local or already on disk)
    
    for photo in to_download_objects:
        # Resolve creation date
        created_time = photo.created # Default to UTC from iCloud
        
        # If photo.created is None or epoch (common fallback for failed parsing), use cached date
        if not created_time or created_time.year <= 1970:
            created_time = getattr(photo, "_cached_date", None)
            
        if local_library:
            res = local_library.find_photo(photo.id)
            if res:
                _, local_dt = res
                if local_dt and local_dt.year > 1970:
                    created_time = local_dt # Use local time if found
        
        # If still None, use a safe default (today)
        if not created_time:
            created_time = datetime.now()
        
        # Consistently resolve target_file using helper
        target_file = get_target_path(photo.id, photo.filename, created_time)
        target_dir = target_file.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = target_file.name
        if str(target_file) in used_paths:
            name_part, ext_part = os.path.splitext(base_name)
            counter = 1
            while True:
                target_file = target_dir / f"{name_part}_{counter}{ext_part}"
                if str(target_file) not in used_paths:
                    break
                counter += 1
        
        used_paths.add(str(target_file))
        
        is_local = isinstance(photo, LocalAssetStub)
        exists_on_disk = target_file.exists()
        
        if exists_on_disk:
            already_on_disk_count += 1
            
        if is_local or exists_on_disk:
            baseline_count += 1
            
        if exists_on_disk:
            continue
            
        tasks.append({"id": f"{target_dir.name}/{target_file.name}", "action": download_worker, "args": (photo, target_file, local_library)})

    # Initialize status bar with correct counts
    pool.status_bar.set_counts(len(to_download_objects), completed=already_on_disk_count, baseline=baseline_count)

    def on_task_result(task_id, res):
        # res should now always be a dict if wrapper is used correctly
        if (isinstance(res, dict) and not res.get("success", True)) or res is False:
            error_msg = res.get("error_brief", "Unknown error") if isinstance(res, dict) else "Download failed"
            log_path = res.get("log_path") if isinstance(res, dict) else None
            failed_tasks.append({"id": task_id, "error": error_msg, "log": log_path})
            
            # Print failure warning above status bar
            pool.status_bar.print_above(f"{BOLD}{RED}Failed{RESET} to download {BOLD}{task_id}{RESET}: {error_msg}")
        else:
            pool.status_bar.increment_completed()

    all_success = pool.run(tasks, success_callback=on_task_result)
    
    # Handle the case where the pool finished but we need to check final counts
    if not tasks and not failed_tasks and not already_downloaded_count:
        # No work was scheduled
        return
    
    if all_success and not failed_tasks and tasks:
        first, last = to_download_objects[0], to_download_objects[-1]
        
        def get_best_date(photo):
            return getattr(photo, "_cached_date", None) or getattr(photo, "created", None)
            
        f_d, l_d = get_best_date(first), get_best_date(last)
        f_s, l_s = f"{f_d.strftime('%Y-%m-%d') if f_d else 'unknown'}/{first.filename}", f"{l_d.strftime('%Y-%m-%d') if l_d else 'unknown'}/{last.filename}"
        print(f"{BOLD}{GREEN}Successfully downloaded{RESET} {len(tasks)} photos/videos from {BOLD}{f_s}{RESET} to {BOLD}{l_s}{RESET}.")
    elif failed_tasks:
        print(f"{BOLD}{RED}Failed to download{RESET} {len(failed_tasks)} photos/videos.")
        summary_log = tool.get_log_dir() / f"fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}_download_summary.log"
        with open(summary_log, 'w', encoding='utf-8') as f:
            for ft in failed_tasks:
                f.write(f"ID: {ft['id']} | Error: {ft['error']} | Detail: {ft['log']}\n")
        print(f"{BOLD}Reason:{RESET} {failed_tasks[0]['error']}... {BOLD}Full log saved to:{RESET} {summary_log}")

if __name__ == "__main__":
    from logic.terminal.keyboard import get_global_suppressor
    
    # Try to restore terminal in case it was left in a bad state by a previous run
    try:
        get_global_suppressor().stop(force=True)
    except:
        pass
    
    try:
        main()
    except KeyboardInterrupt:
        # Standard quiet exit for Ctrl+C.
        # Turing machines/workers already print the "Operation cancelled" message.
        sys.exit(130)
    except Exception:
        # Unexpected crash cleanup
        try:
            get_global_suppressor().stop(force=True)
        except:
            pass
        raise
