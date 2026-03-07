#!/usr/bin/env python3 -u
import os
import json
import time
import hashlib
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def generate_remount_script(project_root: Path):
    # 1. Load GCS config
    config_path = project_root / "data" / "config.json"
    if not config_path.exists():
        return None, "GCS config not found. Please run 'GCS setup-tutorial'."
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    root_folder_id = config.get("root_folder_id")
    env_folder_id = config.get("env_folder_id")
    
    if not root_folder_id or not env_folder_id:
        return None, "GCS folder IDs not found in config. Please run 'GCS setup-tutorial'."

    # 2. Load Service Account Key
    key_path = project_root / "data" / "google_cloud_console" / "console_key.json"
    if not key_path.exists():
        return None, "Service account key not found. Please run 'GCS setup-tutorial'."
    
    with open(key_path, 'r') as f:
        creds_dict = json.load(f)

    # 3. Generate session-specific markers
    ts = str(int(time.time()))
    session_hash = hashlib.md5(f"{ts}_{root_folder_id}".encode()).hexdigest()[:6]
    
    remote_root_name = "REMOTE_ROOT"
    remote_env_name = "REMOTE_ENV"

    script_template = r'''# GCS Remount Script
import os
import json
from datetime import datetime

try:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=True)
    mount_result = "Success"
except Exception as e:
    mount_result = str(e)
    if "Drive already mounted" not in str(e):
        raise

remote_root_path = "/content/drive/MyDrive/%(remote_root_name)s"
remote_env_path = "/content/drive/MyDrive/%(remote_env_name)s"

os.makedirs(remote_root_path, exist_ok=True)
os.makedirs(os.path.join(remote_root_path, "tmp"), exist_ok=True)
os.makedirs(remote_env_path, exist_ok=True)

remote_root_id = None
remote_env_id = None

try:
    try:
        import kora
    except:
        import subprocess
        subprocess.run(['pip', 'install', 'kora'], check=True, capture_output=True)
    from kora.xattr import get_id
    if os.path.exists(remote_root_path): remote_root_id = get_id(remote_root_path)
    if os.path.exists(remote_env_path): remote_env_id = get_id(remote_env_path)
except:
    pass

fingerprint_data = {
    "mount_point": "/content/drive",
    "timestamp": "%(ts)s",
    "hash": "%(session_hash)s",
    "remote_root_id": remote_root_id,
    "remote_env_id": remote_env_id,
    "signature": "%(ts)s_%(session_hash)s_" + str(remote_root_id or "unknown") + "_" + str(remote_env_id or "unknown"),
    "created": datetime.now().isoformat(),
    "type": "mount_fingerprint"
}

fingerprint_file = os.path.join(remote_root_path, "tmp", ".gds_mount_fingerprint_%(session_hash)s")
with open(fingerprint_file, 'w') as f:
    json.dump(fingerprint_data, f, indent=2)

result_file = os.path.join(remote_root_path, "tmp", "remount_result_%(ts)s_%(session_hash)s.json")
result_data = {
    "success": True,
    "mount_point": "/content/drive",
    "timestamp": "%(ts)s",
    "remote_root": remote_root_path,
    "remote_env": remote_env_path,
    "remote_root_id": remote_root_id,
    "remote_env_id": remote_env_id,
    "fingerprint_signature": fingerprint_data.get("signature"),
    "completed": datetime.now().isoformat(),
    "type": "remount"
}
with open(result_file, 'w') as f:
    json.dump(result_data, f, indent=2)

SERVICE_ACCOUNT_CREDENTIALS = %(creds_json)s

def verify_fingerprint_file_access(tmp_folder_id, fingerprint_filename, creds_dict):
    import time
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
    except:
        import subprocess
        subprocess.run(['pip', 'install', 'google-api-python-client', 'google-auth-httplib2', 'google-auth-oauthlib'], check=True, capture_output=True)
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    service = build('drive', 'v3', credentials=credentials)

    print("Verifying mount via API: ", end="", flush=True)
    for _ in range(20):
        try:
            query = "'%%s' in parents and name='%%s'" %% (tmp_folder_id, fingerprint_filename)
            res = service.files().list(q=query).execute()
            if res.get('files'):
                print("OK")
                return True
        except:
            pass
        time.sleep(1)
    print("Failed")
    return False

tmp_folder_id = None
if remote_root_id:
    try:
        from kora.xattr import get_id
        tmp_folder_id = get_id(os.path.join(remote_root_path, "tmp"))
    except:
        pass

fingerprint_filename = os.path.basename(fingerprint_file)
if tmp_folder_id and verify_fingerprint_file_access(tmp_folder_id, fingerprint_filename, SERVICE_ACCOUNT_CREDENTIALS):
    print("Remount successful!")
else:
    print("Remount failed. Please restart runtime.")
''' % {
        'remote_root_name': remote_root_name,
        'remote_env_name': remote_env_name,
        'ts': ts,
        'session_hash': session_hash,
        'creds_json': json.dumps(creds_dict)
    }

    return script_template, {
        "ts": ts,
        "session_hash": session_hash
    }

def log_remount(msg):
    try:
        with open("/tmp/gcs_remount_debug.log", "a") as f:
            f.write(f"[{time.time()}] {msg}\n")
            f.flush()
    except: pass

def _get_gcs_translation(project_root, key, default, **kwargs):
    try:
        from interface.lang import get_translation
        logic_dir = str(project_root / "tool" / "GOOGLE.GCS" / "logic")
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        return default.format(**kwargs) if kwargs else default

def show_remount_gui(project_root: Path, script: str, metadata: dict):
    log_remount("Entering show_remount_gui")
    from interface.gui import ButtonBarWindow

    _ = lambda key, default, **kw: _get_gcs_translation(project_root, key, default, **kw)

    btn_copy_text = _("gui_btn_copy", "Copy Script")
    btn_copied_text = _("gui_btn_copied", "Copied!")
    btn_feedback_text = _("gui_btn_feedback", "Feedback")
    btn_finished_text = _("gui_btn_finished", "Finished")
    btn_sending_text = _("gui_btn_sending", "Sending...")
    
    def copy_to_clipboard():
        log_remount("Copy Script clicked")
        if sys.platform == "darwin":
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(script.encode('utf-8'))
    
    def on_copy_click(btn):
        btn.config(text=btn_copied_text, state="disabled")
        btn.after(1500, lambda: btn.config(text=btn_copy_text, state="normal"))

    def on_feedback_click(btn):
        btn.config(text=btn_sending_text, state="disabled")

    buttons = [
        {
            "text": btn_copy_text, 
            "cmd": copy_to_clipboard, 
            "on_click": on_copy_click,
            "close_on_click": False
        },
        {
            "text": btn_finished_text,
            "return_value": "Finished",
            "cmd": None,
            "close_on_click": True,
            "disable_seconds": 15
        },
        {
            "text": btn_feedback_text,
            "return_value": "Feedback",
            "cmd": None,
            "on_click": on_feedback_click,
            "close_on_click": True,
            "disable_seconds": 15
        }
    ]
    
    # Auto-copy on startup
    copy_to_clipboard()
    
    instruction = _("gui_instruction_remount",
        "Please copy the script and run it in a **Python code cell** on Google Colab. Click 'Finished' once execution completes.")
    
    gui_title = _("gui_title_remount", "GCS Remount")

    win = ButtonBarWindow(
        title=gui_title, 
        timeout=300, 
        internal_dir=str(project_root / "tool" / "GOOGLE.GCS" / "logic"), 
        buttons=buttons,
        instruction=instruction,
        window_size="450x120"
    )
    log_remount("Calling win.run()")
    win.run()
    log_remount(f"win.run() returned with result status: {win.result.get('status')}")
    return win.result

if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--script-path", required=True)
    parser.add_argument("--ts", required=True)
    parser.add_argument("--hash", required=True)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args()
    
    proj_root = Path(args.project_root)
    
    # CRITICAL: Ensure project root is at the VERY BEGINNING of sys.path
    # This prevents any local path shadowing and allows 'import logic...' to work.
    root_str = str(proj_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    
    # Also remove current script directory from path if it shadows project 'logic'
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
    
    with open(args.script_path, 'r') as f:
        script_content = f.read()
        
    metadata = {"ts": args.ts, "session_hash": args.hash}
    res = show_remount_gui(proj_root, script_content, metadata)

def verify_local_remount_result(project_root: Path, ts: str, session_hash: str, stage=None):
    """
    Verify the remount result by checking Google Drive via API.
    This ensures Colab has successfully mounted and written the result.
    """
    import importlib.util
    def load_logic(name):
        logic_path = Path(__file__).resolve().parent / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"gcs_logic_{name}", str(logic_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    common_mod = load_logic("utils")
    filename = f"remount_result_{ts}_{session_hash}.json"
    ok, msg, data = common_mod.wait_for_gdrive_file(project_root, filename, timeout=60, stage=stage)
    if ok:
        return True, "Handshake successful"
    return False, msg
