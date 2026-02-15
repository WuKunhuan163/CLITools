import json
import jwt
import time
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

