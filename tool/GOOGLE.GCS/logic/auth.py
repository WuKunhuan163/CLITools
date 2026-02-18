import json
import jwt
import time
import requests
from pathlib import Path

def validate_service_account_json(file_path):
    """
    Validates a Google Service Account JSON key.
    Returns (is_valid, error_msg, info_dict)
    """
    try:
        with open(file_path, 'r') as f:
            info = json.load(f)
        
        required_fields = [
            "type", "project_id", "private_key_id", "private_key",
            "client_email", "client_id", "auth_uri", "token_uri"
        ]
        
        for field in required_fields:
            if field not in info:
                return False, f"Missing required field: {field}", None
        
        if info["type"] != "service_account":
            return False, "Not a service account key (type mismatch)", None
            
        # Basic check of private key format
        if "-----BEGIN PRIVATE KEY-----" not in info["private_key"]:
            return False, "Invalid private key format", None
            
        return True, "", info
        
    except json.JSONDecodeError:
        return False, "Not a valid JSON file", None
    except Exception as e:
        return False, str(e), None

def save_console_key(project_root, info):
    """Saves the validated key to data/google_cloud_console/console_key.json"""
    target_dir = Path(project_root) / "data" / "google_cloud_console"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "console_key.json"
    
    with open(target_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2)
    return target_path

def get_access_token(info, scope="https://www.googleapis.com/auth/drive.readonly"):
    """Generates an access token using JWT for the service account."""
    now = int(time.time())
    payload = {
        "iss": info["client_email"],
        "scope": scope,
        "aud": info["token_uri"],
        "exp": now + 3600,
        "iat": now
    }
    token = jwt.encode(payload, info["private_key"], algorithm="RS256")
    res = requests.post(info["token_uri"], data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": token
    }, timeout=10)
    if res.status_code != 200:
        raise Exception(f"Auth Error: {res.text}")
    return res.json()["access_token"]

def validate_folder_access(project_root, folder_id):
    """Checks if a folder ID is accessible using the saved console key."""
    key_path = Path(project_root) / "data" / "google_cloud_console" / "console_key.json"
    if not key_path.exists():
        return False, "Console key not found. Please complete Step 4."
    
    try:
        with open(key_path, 'r') as f:
            info = json.load(f)
        
        token = get_access_token(info)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test access by getting metadata
        url = f"https://www.googleapis.com/drive/v3/files/{folder_id}"
        params = {"fields": "id, name, mimeType"}
        res = requests.get(url, headers=headers, params=params, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("mimeType") != "application/vnd.google-apps.folder":
                return False, f"ID refers to a file, not a folder (type: {data.get('mimeType')})"
            return True, data.get("name")
        elif res.status_code == 404:
            return False, "Folder not found or not shared with this service account."
        else:
            return False, f"API Error ({res.status_code}): {res.text}"
            
    except Exception as e:
        return False, str(e)

def save_gcs_config(project_root, root_folder_id, env_folder_id):
    """Saves the folder IDs to data/config.json"""
    target_dir = Path(project_root) / "data"
    target_dir.mkdir(parents=True, exist_ok=True)
    config_path = target_dir / "config.json"
    
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except: pass
        
    config["root_folder_id"] = root_folder_id
    config["env_folder_id"] = env_folder_id
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    return config_path
