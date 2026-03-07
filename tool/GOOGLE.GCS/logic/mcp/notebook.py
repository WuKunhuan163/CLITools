"""MCP workflow for creating .root.ipynb in the Env folder.

This module provides:
1. Pre-flight checks (notebook exists? valid? config ready?)
2. Structured workflow instructions for the AI agent to execute via browser MCP.
"""
import json
import sys
from pathlib import Path

def _find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent.parent.parent.parent

_project_root = _find_project_root()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.interface.config import get_color
from logic.mcp.drive_create import build_create_workflow, get_supported_types

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
BLUE = get_color("BLUE")
RESET = get_color("RESET")

_DEFAULT_NOTEBOOK_NAME = ".root.ipynb"


def _get_notebook_name():
    cfg = _load_config()
    return cfg.get("root_notebook_name", _DEFAULT_NOTEBOOK_NAME)


def _load_config():
    config_path = _project_root / "data" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, 'r') as f:
        return json.load(f)


def _save_config(cfg):
    config_path = _project_root / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def _get_drive_token():
    import importlib.util
    key_path = _project_root / "data" / "google_cloud_console" / "console_key.json"
    if not key_path.exists():
        return None
    with open(key_path, 'r') as f:
        info = json.load(f)
    auth_path = _project_root / "tool" / "GOOGLE.GCS" / "logic" / "auth.py"
    spec = importlib.util.spec_from_file_location("gcs_auth_mcp", str(auth_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.get_access_token(info, scope="https://www.googleapis.com/auth/drive")


def _check_notebook_exists(token, folder_id):
    """Check if .root.ipynb exists in folder and return (file_id, size) or (None, None)."""
    import requests
    nb_name = _get_notebook_name()
    q = f"'{folder_id}' in parents and name = '{nb_name}' and trashed = false"
    res = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": q, "fields": "files(id,name,size,mimeType)", "pageSize": 5},
        timeout=20
    )
    if res.status_code == 200:
        files = res.json().get("files", [])
        if files:
            f = files[0]
            return f["id"], int(f.get("size", "0"))
    return None, None


def _save_notebook_to_config(file_id):
    cfg = _load_config()
    cfg["root_notebook_id"] = file_id
    cfg["root_notebook_url"] = f"https://colab.research.google.com/drive/{file_id}"
    _save_config(cfg)


def run_mcp_create_notebook(as_json=False):
    """Check notebook status and provide instructions for browser-based creation.

    Returns exit code:
        0 = notebook already exists and valid
        2 = notebook needs creation, instructions provided
        1 = error
    """
    cfg = _load_config()
    nb_name = cfg.get("root_notebook_name", _DEFAULT_NOTEBOOK_NAME)
    env_folder_id = cfg.get("env_folder_id", "")
    root_folder_id = cfg.get("root_folder_id", "")
    target_folder_id = env_folder_id or root_folder_id
    existing_nb_id = cfg.get("root_notebook_id", "")

    if not target_folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": "No folder ID configured. Run GCS --setup-tutorial first."}))
        else:
            print(f"{BOLD}{RED}Failed to check{RESET} notebook. No folder ID configured.")
            print(f"  Run {BOLD}GCS --setup-tutorial{RESET} first.")
        return 1

    try:
        token = _get_drive_token()
    except Exception as e:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Auth failed: {e}"}))
        else:
            print(f"{BOLD}{RED}Failed to authenticate{RESET}. {e}")
        return 1

    if not token:
        if as_json:
            print(json.dumps({"status": "error", "message": "No auth token. Run GCS --setup-tutorial first."}))
        else:
            print(f"{BOLD}{RED}Failed to authenticate{RESET}. Run {BOLD}GCS --setup-tutorial{RESET} first.")
        return 1

    if existing_nb_id:
        file_id, size = _check_notebook_exists(token, target_folder_id)
        if file_id and size > 0:
            colab_url = f"https://colab.research.google.com/drive/{file_id}"
            if as_json:
                print(json.dumps({"status": "exists", "file_id": file_id, "size": size, "colab_url": colab_url}))
            else:
                print(f"{BOLD}{GREEN}Already configured{RESET}. {nb_name} exists ({size} bytes).")
                print(f"  Colab: {colab_url}")
            return 0
        elif file_id and size == 0:
            if as_json:
                print(json.dumps({"status": "corrupted", "file_id": file_id, "message": "Empty notebook (0 bytes). Needs recreation."}))
            else:
                print(f"{BOLD}{YELLOW}Corrupted notebook{RESET}. {nb_name} is 0 bytes.")
                print(f"  Deleting and recreating...")
            import requests
            requests.delete(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {token}"}, timeout=10
            )
            cfg.pop("root_notebook_id", None)
            cfg.pop("root_notebook_url", None)
            _save_config(cfg)
        else:
            cfg.pop("root_notebook_id", None)
            cfg.pop("root_notebook_url", None)
            _save_config(cfg)
    else:
        file_id, size = _check_notebook_exists(token, target_folder_id)
        if file_id and size > 0:
            _save_notebook_to_config(file_id)
            colab_url = f"https://colab.research.google.com/drive/{file_id}"
            if as_json:
                print(json.dumps({"status": "found", "file_id": file_id, "size": size, "colab_url": colab_url}))
            else:
                print(f"{BOLD}{GREEN}Found existing{RESET} {nb_name} ({size} bytes).")
                print(f"  Colab: {colab_url}")
            return 0

    folder_type = "env" if env_folder_id else "root"
    workflow = build_create_workflow(target_folder_id, "colab", nb_name)
    workflow["notebook_name"] = nb_name
    workflow["folder_type"] = folder_type
    workflow["steps"].append({
        "action": "save_config",
        "description": "Save notebook ID to GCS config",
        "note": f"Extract file ID from Colab URL, then run: GCS --mcp-save-notebook <file_id>",
    })

    if as_json:
        print(json.dumps(workflow, indent=2))
    else:
        print(f"{BOLD}{BLUE}Notebook creation required{RESET}. Browser MCP workflow available.")
        print(f"  Target: {folder_type} folder ({target_folder_id})")
        print(f"  Drive URL: {workflow['folder_url']}")
        print(f"  Notebook: {nb_name}")
        print(f"\n  Use {BOLD}GCS --mcp-create-notebook --json{RESET} for structured workflow instructions.")
        print(f"  Or follow the skill: {BOLD}GCS-mcp-create-notebook{RESET}")
    return 2


def save_notebook_id(file_id):
    """Save a notebook file ID to config after browser-based creation."""
    if not file_id:
        print(f"{BOLD}{RED}Failed to save{RESET}. No file ID provided.")
        return 1
    _save_notebook_to_config(file_id)
    colab_url = f"https://colab.research.google.com/drive/{file_id}"
    print(f"{BOLD}{GREEN}Successfully saved{RESET} notebook ID.")
    print(f"  Colab: {colab_url}")
    return 0
