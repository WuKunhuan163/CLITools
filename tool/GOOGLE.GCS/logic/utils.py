#!/usr/bin/env python3 -u
import os
import sys
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

def normalize_input_path(path: str, current_path: str = "~") -> str:
    """Convert a user-supplied path (possibly shell-expanded) to a logical path."""
    home = os.path.expanduser("~")
    if path.startswith(home + "/") or path == home:
        path = "~" + path[len(home):]
    if not path.startswith("~") and not path.startswith("@") and not path.startswith("/"):
        path = current_path + "/" + path
    return _normalize_logical_path(path)


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


def logical_to_mount_path(logical_path: str) -> str:
    """Convert a logical path (~/tmp) to a Colab mount path (/content/drive/MyDrive/REMOTE_ROOT/tmp)."""
    if logical_path == "~" or logical_path == "~/":
        return "/content/drive/MyDrive/REMOTE_ROOT"
    if logical_path == "@" or logical_path == "@/":
        return "/content/drive/MyDrive/REMOTE_ENV"
    if logical_path.startswith("~/"):
        return f"/content/drive/MyDrive/REMOTE_ROOT/{logical_path[2:]}"
    if logical_path.startswith("@/"):
        return f"/content/drive/MyDrive/REMOTE_ENV/{logical_path[2:]}"
    return logical_path


def expand_remote_paths(command: str, remote_root: str, remote_env: str) -> str:
    """
    Expand unquoted ~ and @ in a command string to remote mount paths,
    respecting bash quoting rules. Characters inside single or double
    quotes are NOT expanded.

    Examples:
        expand_remote_paths('echo ~', R, E)           → 'echo R'
        expand_remote_paths('echo "~ is not \'~\'"', R, E) → 'echo "~ is not \'~\'"'
        expand_remote_paths('ls ~/tmp', R, E)          → 'ls R/tmp'
        expand_remote_paths('ls @/env', R, E)          → 'ls E/env'
    """
    import re, uuid

    placeholders = {}

    # Step 1: Protect double-quoted strings (supports escaped quotes \")
    protected = command
    for pattern in [r'"(?:[^"\\]|\\.)*"', r"'[^']*'"]:
        for match in reversed(list(re.finditer(pattern, protected))):
            ph = f"__QS_{uuid.uuid4().hex[:8]}__"
            placeholders[ph] = match.group(0)
            protected = protected[:match.start()] + ph + protected[match.end():]

    # Step 2: Expand unquoted ~ and @ (path-like contexts)
    # ~/... → remote_root/...   ~ (standalone) → remote_root
    # @/... → remote_env/...    @ (standalone) → remote_env
    # Only expand ~ and @ that appear at word boundaries (not inside identifiers)
    protected = re.sub(r'(?<![/\w])~(?=/)', remote_root, protected)
    protected = re.sub(r'(?<![/\w])~(?=\s|$)', remote_root, protected)
    protected = re.sub(r'(?<![/\w])@(?=/)', remote_env, protected)
    protected = re.sub(r'(?<![/\w])@(?=\s|$)', remote_env, protected)

    # Step 3: Restore quoted strings
    for ph, original in placeholders.items():
        protected = protected.replace(ph, original)

    return protected


def run_drive_api_script(project_root: Path, script_body: str, timeout: int = 30) -> Tuple[bool, dict]:
    """
    Execute a Drive API operation via a tmp script with timeout.
    script_body should be a Python snippet that writes JSON result to result_path.
    Returns (success, result_dict).
    """
    import subprocess, hashlib
    ts = str(int(time.time()))
    h = hashlib.md5(f"{ts}_{script_body[:50]}".encode()).hexdigest()[:6]
    
    tmp_dir = project_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    script_path = tmp_dir / f"gcs_api_{ts}_{h}.py"
    result_path = tmp_dir / f"gcs_api_{ts}_{h}.json"
    
    creds = get_service_account_creds(project_root)
    config = get_gcs_config(project_root)
    
    full_script = f'''#!/usr/bin/env python3
import json, time, os, sys
import socket
try:
    import urllib3.util.connection as _uc
    _uc.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass
import requests, jwt
from pathlib import Path

result_path = {repr(str(result_path))}

def get_token(info):
    now = int(time.time())
    payload = {{"iss": info["client_email"], "scope": "https://www.googleapis.com/auth/drive", "aud": info["token_uri"], "exp": now + 3600, "iat": now}}
    t = jwt.encode(payload, info["private_key"], algorithm="RS256")
    r = requests.post(info["token_uri"], data={{"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": t}}, timeout=20)
    if r.status_code != 200:
        raise Exception(f"Auth failed: {{r.text}}")
    return r.json()["access_token"]

def api_get(url, headers, params=None, timeout=20, max_retries=3):
    """GET with automatic retry on transient errors (500/502/503/504)."""
    last_err = None
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code in (500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(1)
                continue
            return r
        except requests.exceptions.Timeout:
            last_err = f"Request timed out (attempt {{attempt + 1}}/{{max_retries}})"
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise Exception(last_err)
    return r

try:
    creds = {json.dumps(creds)}
    config = {json.dumps(config)}
    token = get_token(creds)
    headers = {{"Authorization": f"Bearer {{token}}"}}
    
{script_body}
    
    with open(result_path, "w") as f:
        json.dump(result, f)
except Exception as e:
    with open(result_path, "w") as f:
        json.dump({{"error": str(e)}}, f)
'''
    
    with open(script_path, 'w') as f:
        f.write(full_script)
    
    try:
        python_exec = sys.executable
        python_tool = project_root / "tool" / "PYTHON"
        if python_tool.exists():
            try:
                from logic.utils import get_logic_dir
                import importlib.util
                utils_path = get_logic_dir(python_tool) / "utils.py"
                if utils_path.exists():
                    spec = importlib.util.spec_from_file_location("py_utils", str(utils_path))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    python_exec = mod.get_python_exec()
            except:
                pass
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        proc = subprocess.run(
            [python_exec, str(script_path)],
            env=env, timeout=timeout,
            capture_output=True, text=True
        )
        
        if result_path.exists():
            with open(result_path, 'r') as f:
                result = json.load(f)
            if "error" in result:
                return False, result
            return True, result
        else:
            return False, {"error": f"Script failed: {proc.stderr[:200]}"}
    except subprocess.TimeoutExpired:
        return False, {"error": f"Timed out after {timeout}s"}
    except Exception as e:
        return False, {"error": str(e)}
    finally:
        if script_path.exists():
            script_path.unlink()
        if result_path.exists():
            result_path.unlink()


def resolve_path_via_api(project_root: Path, path: str, current_path: str = "~", current_folder_id: str = None, timeout: int = 60) -> Tuple[Optional[str], str]:
    """
    Resolve a virtual path to a Drive folder ID using a tmp script.
    Non-interactive: runs an isolated subprocess with timeout.
    Returns (folder_id, display_path) or (None, error_message).
    """
    config = get_gcs_config(project_root)
    
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
            return None, "Root folder not configured. Run 'GCS --setup-tutorial'."
        return fid, "~"

    if path in ("@", "@/"):
        fid = config.get("env_folder_id")
        if not fid:
            return None, "Env folder not configured. Run 'GCS --setup-tutorial'."
        return fid, "@"

    if path.startswith("~/"):
        base_id = config.get("root_folder_id")
        if not base_id:
            return None, "Root folder not configured. Run 'GCS --setup-tutorial'."
        base_display = "~"
        relative = path[2:]
    elif path.startswith("@/"):
        base_id = config.get("env_folder_id")
        if not base_id:
            return None, "Env folder not configured. Run 'GCS --setup-tutorial'."
        base_display = "@"
        relative = path[2:]
    else:
        return None, f"Invalid path '{path}'. Use ~ for root or @ for env."

    parts = [p for p in relative.split("/") if p]
    if not parts:
        return base_id, base_display

    script_body = f'''    import uuid
    base_id = {repr(base_id)}
    parts = {repr(parts)}
    base_display = {repr(base_display)}
    
    current_id = base_id
    current_display = base_display
    for part in parts:
        q = f"'{{current_id}}' in parents and name = '{{part}}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        params = {{"q": q, "fields": "files(id, name)", "pageSize": 100, "supportsAllDrives": "true", "includeItemsFromAllDrives": "true", "quotaUser": f"r_{{uuid.uuid4().hex[:8]}}"}}
        r = api_get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
        if r.status_code != 200:
            result = {{"error": f"API error {{r.status_code}}: {{r.text[:200]}}"}}
            break
        files = r.json().get("files", [])
        found = None
        for ff in files:
            if ff.get("name") == part:
                found = ff["id"]
                break
        if not found:
            result = {{"error": f"Folder '{{part}}' not found under {{current_display}}/"}}
            break
        current_id = found
        current_display = f"{{current_display}}/{{part}}"
    else:
        result = {{"folder_id": current_id, "display_path": current_display}}'''

    ok, data = run_drive_api_script(project_root, script_body, timeout=timeout)
    if not ok:
        return None, data.get("error", "Unknown error")
    return data.get("folder_id"), data.get("display_path", path)


def list_folder_via_api(project_root: Path, folder_id: str, long_format: bool = False, timeout: int = 60) -> Tuple[bool, list]:
    """
    List contents of a Drive folder using a tmp script.
    Returns (success, items_list) where items are dicts with name, type, id.
    """
    script_body = f'''    import uuid
    folder_id = {repr(folder_id)}
    all_items = []
    page_token = None
    while True:
        params = {{
            "q": f"'{{folder_id}}' in parents and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            "pageSize": 100,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "orderBy": "folder, name",
            "quotaUser": f"ls_{{uuid.uuid4().hex[:8]}}"
        }}
        if page_token:
            params["pageToken"] = page_token
        r = api_get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
        if r.status_code != 200:
            result = {{"error": f"API error {{r.status_code}}: {{r.text[:200]}}"}}
            break
        data = r.json()
        for f in data.get("files", []):
            is_folder = f.get("mimeType") == "application/vnd.google-apps.folder"
            all_items.append({{
                "name": f["name"],
                "type": "folder" if is_folder else "file",
                "id": f["id"],
                "modified": f.get("modifiedTime", ""),
                "size": f.get("size", "")
            }})
        page_token = data.get("nextPageToken")
        if not page_token:
            result = {{"items": all_items}}
            break
    else:
        pass'''

    ok, data = run_drive_api_script(project_root, script_body, timeout=timeout)
    if not ok:
        return False, data.get("error", "Unknown error")
    return True, data.get("items", [])


def read_file_via_api(project_root: Path, folder_id: str, filename: str, timeout: int = 30) -> Tuple[bool, dict]:
    """
    Read a file's content from Google Drive by name within a specific folder.
    Returns (success, {"content": str}) or (success, {"error": str}).
    """
    script_body = f'''    import uuid
    folder_id = {repr(folder_id)}
    target_name = {repr(filename)}
    q = f"'{{folder_id}}' in parents and name = '{{target_name}}' and trashed = false"
    params = {{"q": q, "fields": "files(id, name, mimeType)", "pageSize": 10,
               "supportsAllDrives": "true", "includeItemsFromAllDrives": "true",
               "quotaUser": f"rf_{{uuid.uuid4().hex[:8]}}"}}
    r = api_get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params)
    if r.status_code != 200:
        result = {{"error": f"API error {{r.status_code}}: {{r.text[:200]}}"}}
    else:
        files = r.json().get("files", [])
        target = None
        for ff in files:
            if ff.get("name") == target_name:
                target = ff
                break
        if not target:
            result = {{"error": f"File '{{target_name}}' not found"}}
        elif target.get("mimeType", "").startswith("application/vnd.google-apps."):
            result = {{"error": f"'{{target_name}}' is a Google Apps document, not a regular file"}}
        else:
            cr = requests.get(f"https://www.googleapis.com/drive/v3/files/{{target['id']}}?alt=media", headers=headers, timeout=20)
            if cr.status_code == 200:
                result = {{"content": cr.text, "file_id": target["id"]}}
            else:
                result = {{"error": f"Download failed ({{cr.status_code}}): {{cr.text[:200]}}"}}'''

    return run_drive_api_script(project_root, script_body, timeout=timeout)


def resolve_file_path(project_root: Path, path: str, state_mgr, load_logic) -> Tuple[Optional[str], str, str]:
    """
    Resolve a file path like ~/tmp/foo.py or @/bar.txt into (folder_id, filename, display_path).
    Returns (folder_id, filename, display_path) or (None, error_msg, "").
    """
    import os

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    current_path = info.get("current_path", "~") if info else "~"

    if '/' in path:
        dir_path = os.path.dirname(path)
        filename = os.path.basename(path)
    else:
        dir_path = current_path
        filename = path

    folder_id, display_path = resolve_path_via_api(
        project_root, dir_path, current_path=current_path
    )
    if not folder_id:
        return None, display_path, ""
    return folder_id, filename, display_path


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
    env_parent_id = None
    last_error = ""
    
    config = get_gcs_config(project_root)
    env_parent_id = config.get("env_folder_id")
    root_parent_id = config.get("root_folder_id")
    
    env_tmp_id = None
    root_tmp_id = None

    while time.time() - start_time < timeout:
        token = get_gdrive_access_token(creds)
        if not token:
            _write_debug_log(project_root, "WARN: failed to get access token, retrying...")
            time.sleep(2)
            continue
            
        headers = {"Authorization": f"Bearer {token}"}
        
        if not env_tmp_id:
            if env_parent_id:
                env_tmp_id = get_folder_id(headers, "tmp", parent_id=env_parent_id)
                if env_tmp_id:
                    _write_debug_log(project_root, f"RESOLVED: tmp under REMOTE_ENV, id={env_tmp_id}")
            if not env_tmp_id:
                if not env_parent_id:
                    env_parent_id = get_folder_id(headers, "REMOTE_ENV")
                if env_parent_id:
                    env_tmp_id = get_folder_id(headers, "tmp", parent_id=env_parent_id)
            if root_parent_id and not root_tmp_id:
                root_tmp_id = get_folder_id(headers, "tmp", parent_id=root_parent_id)
                if root_tmp_id:
                    _write_debug_log(project_root, f"RESOLVED: tmp under REMOTE_ROOT, id={root_tmp_id}")
            if not env_tmp_id and not root_tmp_id:
                if not root_parent_id:
                    root_parent_id = get_folder_id(headers, "REMOTE_ROOT")
                if root_parent_id:
                    root_tmp_id = get_folder_id(headers, "tmp", parent_id=root_parent_id)
            tmp_folder_id = env_tmp_id or root_tmp_id
            if not tmp_folder_id:
                _write_debug_log(project_root, "WARN: 'tmp' folder not found, using name-based search")

        elapsed = time.time() - start_time
        use_name_search = (not tmp_folder_id) or (elapsed > timeout * 0.5)

        import uuid
        queries = []
        if tmp_folder_id:
            queries.append(f"'{tmp_folder_id}' in parents and trashed = false")
        if env_tmp_id and env_tmp_id != tmp_folder_id:
            queries.append(f"'{env_tmp_id}' in parents and trashed = false")
        if use_name_search:
            queries.append(f"name = '{filename}' and trashed = false")
        if not queries:
            queries.append(f"name = '{filename}' and trashed = false")

        found = False
        total_files_seen = 0
        try:
            for qi, q in enumerate(queries):
                params = {
                    "q": q,
                    "fields": "files(id, name, createdTime, size)",
                    "pageSize": 200,
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                    "quotaUser": f"refresh_{uuid.uuid4().hex[:8]}"
                }
                res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=20)
                if res.status_code == 200:
                    all_files = res.json().get("files", [])
                    total_files_seen += len(all_files)
                    target_files = [f for f in all_files if f.get("name") == filename]
                    if target_files:
                        file_id = target_files[0]['id']
                        _write_debug_log(project_root, f"FOUND: {filename} (id={file_id}, query #{qi+1}), downloading...")
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
                        found = True
                        break
                else:
                    last_error = f"API error ({res.status_code})"
                    _write_debug_log(project_root, f"ERROR: {last_error}: {res.text[:200]}")

            if not found:
                elapsed_s = int(time.time() - start_time)
                _write_debug_log(project_root, f"POLL ({elapsed_s}s): {total_files_seen} files across {len(queries)} queries, '{filename}' not found yet")
            
            now = time.time()
            if now - last_tm_update > 5:
                if stage:
                    elapsed = int(now - start_time)
                    base_name = getattr(stage, '_original_active_name', None)
                    if base_name is None:
                        base_name = stage.active_name or "the result file"
                        stage._original_active_name = base_name
                    stage.active_name = f"{base_name} ({elapsed}s)"
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

