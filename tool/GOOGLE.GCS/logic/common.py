#!/usr/bin/env python3 -u
import os
import json
import time
import requests
import jwt
from pathlib import Path
from typing import Tuple, Optional

def get_gcs_config(project_root: Path) -> dict:
    config_path = project_root / "data" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, 'r') as f:
        return json.load(f)

def get_service_account_creds(project_root: Path) -> dict:
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    if not key_path.exists():
        return {}
    with open(key_path, 'r') as f:
        return json.load(f)

def get_gdrive_access_token(creds_dict: dict) -> Optional[str]:
    try:
        now = int(time.time())
        payload = {
            "iss": creds_dict["client_email"],
            "scope": "https://www.googleapis.com/auth/drive",
            "aud": creds_dict["token_uri"],
            "exp": now + 3600,
            "iat": now
        }
        token_jwt = jwt.encode(payload, creds_dict["private_key"], algorithm="RS256")
        res = requests.post(creds_dict["token_uri"], data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": token_jwt
        }, timeout=20)
        if res.status_code == 200:
            return res.json()["access_token"]
    except Exception:
        pass
    return None

def get_folder_id(service_headers, folder_name, parent_id=None):
    import uuid
    if parent_id:
        q = f"'{parent_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    else:
        q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

    params = {
        "q": q,
        "fields": "files(id, name, mimeType)",
        "pageSize": 100,
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
        "quotaUser": f"refresh_{uuid.uuid4().hex[:8]}"
    }
    try:
        res = requests.get("https://www.googleapis.com/drive/v3/files", headers=service_headers, params=params, timeout=20)
        if res.status_code == 200:
            files = res.json().get("files", [])
            for f in files:
                if f.get("name") == folder_name:
                    return f["id"]
    except:
        pass
    return None

def _normalize_logical_path(path: str) -> str:
    """Normalize a logical path by resolving . and .. components."""
    if path.startswith("~/"):
        prefix, rest = "~", path[2:]
    elif path.startswith("@/"):
        prefix, rest = "@", path[2:]
    elif path in ("~", "@"):
        return path
    else:
        return path

    parts = rest.split("/")
    stack = []
    for part in parts:
        if not part or part == ".":
            continue
        elif part == "..":
            if stack:
                stack.pop()
        else:
            stack.append(part)

    if stack:
        return f"{prefix}/{'/'.join(stack)}"
    return prefix


def resolve_drive_path(headers: dict, path: str, config: dict, current_path: str = "~", current_folder_id: str = None) -> Tuple[Optional[str], str]:
    """
    Translate a virtual path to a Google Drive folder ID.
    ~ = root_folder_id, @ = env_folder_id.
    Supports nested paths like ~/sub/dir, @/models/v2, relative paths,
    and .. for parent navigation.
    Returns (folder_id, resolved_display_path) or (None, error_message).
    """
    home = os.path.expanduser("~")
    if path.startswith(home + "/") or path == home:
        path = "~" + path[len(home):]

    if not path.startswith("~") and not path.startswith("@"):
        if path in (".", "./"):
            path = current_path
        elif path == "..":
            path = current_path + "/.."
        elif path.startswith("../"):
            path = current_path + "/" + path
        elif path.startswith("./"):
            path = current_path + "/" + path[2:]
        else:
            path = current_path + "/" + path

    path = _normalize_logical_path(path)

    if path in ("~", "~/"):
        fid = config.get("root_folder_id")
        if not fid:
            return None, "Root folder not configured. Run 'setup-tutorial'."
        return fid, "~"

    if path in ("@", "@/"):
        fid = config.get("env_folder_id")
        if not fid:
            return None, "Env folder not configured. Run 'setup-tutorial'."
        return fid, "@"

    if path.startswith("~/"):
        base_id = config.get("root_folder_id")
        if not base_id:
            return None, "Root folder not configured. Run 'setup-tutorial'."
        base_display = "~"
        relative = path[2:]
    elif path.startswith("@/"):
        base_id = config.get("env_folder_id")
        if not base_id:
            return None, "Env folder not configured. Run 'setup-tutorial'."
        base_display = "@"
        relative = path[2:]
    else:
        return None, f"Invalid path '{path}'. Use ~ for root or @ for env."

    parts = [p for p in relative.split("/") if p]
    if not parts:
        return base_id, base_display

    current_id = base_id
    current_display = base_display
    for part in parts:
        child_id = get_folder_id(headers, part, parent_id=current_id)
        if not child_id:
            return None, f"Folder '{part}' not found under {current_display}/"
        current_id = child_id
        current_display = f"{current_display}/{part}"

    return current_id, current_display


def _write_debug_log(project_root: Path, msg: str):
    try:
        log_dir = project_root / "tool" / "GOOGLE.GCS" / "data" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "wait_for_file_debug.log"
        with open(log_file, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def wait_for_gdrive_file(project_root: Path, filename: str, timeout: int = 60, stage = None) -> Tuple[bool, str, Optional[dict]]:
    """
    Unified interface to wait for a file to appear on Google Drive.
    Updates the provided Turing Machine stage with progress.
    """
    creds = get_service_account_creds(project_root)
    if not creds: return False, "Service account key not found", None
    
    _write_debug_log(project_root, f"START: looking for '{filename}', timeout={timeout}s")
    
    start_time = time.time()
    last_tm_update = 0
    tmp_folder_id = None
    remote_root_id = None
    last_error = ""
    
    config = get_gcs_config(project_root)
    remote_root_id = config.get("root_folder_id")
    
    while time.time() - start_time < timeout:
        token = get_gdrive_access_token(creds)
        if not token:
            _write_debug_log(project_root, "WARN: failed to get access token, retrying...")
            time.sleep(2)
            continue
            
        headers = {"Authorization": f"Bearer {token}"}
        
        if not tmp_folder_id:
            if not remote_root_id:
                remote_root_id = get_folder_id(headers, "REMOTE_ROOT")
            if remote_root_id:
                tmp_folder_id = get_folder_id(headers, "tmp", parent_id=remote_root_id)
                if tmp_folder_id:
                    _write_debug_log(project_root, f"RESOLVED: tmp_folder_id={tmp_folder_id}")
                else:
                    _write_debug_log(project_root, f"WARN: could not find 'tmp' under root={remote_root_id}")
            else:
                _write_debug_log(project_root, "WARN: could not resolve REMOTE_ROOT folder ID")
                
        import uuid
        if tmp_folder_id:
            q = f"'{tmp_folder_id}' in parents and trashed = false"
        elif remote_root_id:
            q = f"'{remote_root_id}' in parents and trashed = false"
        else:
            q = f"name = '{filename}' and trashed = false"
            
        params = {
            "q": q,
            "fields": "files(id, name, createdTime, size)",
            "pageSize": 200,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "quotaUser": f"refresh_{uuid.uuid4().hex[:8]}"
        }
        
        try:
            res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=20)
            if res.status_code == 200:
                all_files = res.json().get("files", [])
                target_files = [f for f in all_files if f.get("name") == filename]
                
                if target_files:
                    file_id = target_files[0]['id']
                    _write_debug_log(project_root, f"FOUND: {filename} (id={file_id}), downloading...")
                    content_res = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers, timeout=20)
                    if content_res.status_code == 200:
                        try:
                            _write_debug_log(project_root, "SUCCESS: file retrieved as JSON")
                            return True, "File retrieved", content_res.json()
                        except:
                            _write_debug_log(project_root, "SUCCESS: file retrieved as raw text")
                            return True, "File retrieved (raw)", {"raw": content_res.text}
                    else:
                        last_error = f"File found but download failed ({content_res.status_code})"
                        _write_debug_log(project_root, f"WARN: {last_error}")
                else:
                    elapsed = int(time.time() - start_time)
                    _write_debug_log(project_root, f"POLL ({elapsed}s): {len(all_files)} files seen, '{filename}' not found yet")
            else:
                last_error = f"API error ({res.status_code})"
                _write_debug_log(project_root, f"ERROR: {last_error}: {res.text[:200]}")
            
            now = time.time()
            if now - last_tm_update > 5:
                if stage:
                    elapsed = int(now - start_time)
                    stage.active_name = f"the result file ({elapsed}s elapsed)"
                    stage.refresh()
                last_tm_update = now
                
        except Exception as e:
            last_error = str(e)
            _write_debug_log(project_root, f"EXCEPTION: {last_error}")
            
        time.sleep(2)
        
    _write_debug_log(project_root, f"TIMEOUT after {timeout}s. Last error: {last_error}")
    detail = f"Timed out waiting for file ({timeout}s)"
    if last_error:
        detail += f". {last_error}"
    return False, detail, None

