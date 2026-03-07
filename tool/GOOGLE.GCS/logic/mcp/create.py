"""Generic MCP file operations for GCS.

Provides CDP-first (gapi.client) Google Drive operations with browser MCP fallback.
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

from interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
BLUE = get_color("BLUE")
YELLOW = get_color("YELLOW")
RESET = get_color("RESET")


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


def _resolve_folder_id(path_spec):
    """Resolve a path spec to a folder ID.

    Supports:
        ~ or root -> root_folder_id
        @ or env  -> env_folder_id
        <folder_id> -> used directly
    """
    cfg = _load_config()
    if path_spec in ("~", "root"):
        return cfg.get("root_folder_id", "")
    if path_spec in ("@", "env"):
        return cfg.get("env_folder_id", "")
    return path_spec


def _is_cdp_available():
    try:
        from logic.cdp.colab import is_chrome_cdp_available, find_colab_tab
        if not is_chrome_cdp_available():
            return False
        tab = find_colab_tab()
        return tab is not None
    except Exception:
        return False


def _get_supported_types():
    try:
        from logic.cdp.colab import DRIVE_MIME_TYPES
        return {k: v.split(".")[-1] if "google-apps" in v else k
                for k, v in DRIVE_MIME_TYPES.items()}
    except ImportError:
        return {}


def run_mcp_create(file_type, folder_spec="~", filename=None, as_json=False):
    """Create a new Drive file.

    Uses CDP + gapi.client when the debug Chrome is available.
    Falls back to browser MCP workflow instructions otherwise.
    """
    from logic.cdp.colab import DRIVE_MIME_TYPES

    if file_type not in DRIVE_MIME_TYPES:
        if as_json:
            print(json.dumps({"status": "error", "types": list(DRIVE_MIME_TYPES.keys())}))
        else:
            print(f"{BOLD}{RED}Unknown type{RESET} '{file_type}'.")
            print(f"  Supported: {', '.join(DRIVE_MIME_TYPES.keys())}")
        return 1

    folder_id = _resolve_folder_id(folder_spec)
    if not folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Cannot resolve folder '{folder_spec}'. Run GCS --setup-tutorial first."}))
        else:
            print(f"{BOLD}{RED}Failed to resolve{RESET} folder '{folder_spec}'.")
            print(f"  Run {BOLD}GCS --setup-tutorial{RESET} first.")
        return 1

    if _is_cdp_available():
        from logic.cdp.colab import create_drive_file
        name = filename or f"Untitled.{file_type}"
        result = create_drive_file(name, file_type, folder_id)
        if result.get("success"):
            file_id = result.get("id", result.get("file_id", ""))
            link = result.get("link", result.get("colab_url", ""))
            if as_json:
                print(json.dumps({"status": "created", "id": file_id, "name": result.get("name", name), "link": link}))
            else:
                print(f"{BOLD}{GREEN}Successfully created{RESET} {result.get('name', name)}.")
                print(f"  ID: {file_id}")
                if link:
                    print(f"  Link: {link}")

            return 0
        else:
            if as_json:
                print(json.dumps({"status": "error", "message": result.get("error", "Unknown error")}))
            else:
                print(f"{BOLD}{RED}Failed to create{RESET} {file_type}. {result.get('error', '')}")
            return 1

    from logic.mcp.drive_create import build_create_workflow, get_supported_types
    supported = get_supported_types()
    workflow = build_create_workflow(folder_id, file_type, filename)

    if as_json:
        print(json.dumps(workflow, indent=2))
    else:
        display = supported.get(file_type, file_type)
        print(f"{BOLD}{BLUE}Creating{RESET} {display}" + (f" as '{filename}'" if filename else "") + f" in folder {folder_spec}.")
        print(f"  Drive URL: {workflow['folder_url']}")
        print(f"  {YELLOW}CDP unavailable{RESET}. Follow browser MCP workflow.")
        print(f"\n  Use {BOLD}GCS --mcp-create {file_type} --json{RESET} for structured workflow instructions.")
    return 2


def run_mcp_delete(file_id, as_json=False):
    """Delete a Google Drive file by ID."""
    if not file_id:
        if as_json:
            print(json.dumps({"status": "error", "message": "No file ID provided."}))
        else:
            print(f"{BOLD}{RED}Missing file ID{RESET}.")
        return 1

    if _is_cdp_available():
        from logic.cdp.colab import delete_drive_file
        ok = delete_drive_file(file_id)
        if ok:
            if as_json:
                print(json.dumps({"status": "deleted", "id": file_id}))
            else:
                print(f"{BOLD}{GREEN}Successfully deleted{RESET} {file_id}.")
            return 0
        else:
            if as_json:
                print(json.dumps({"status": "error", "message": f"Failed to delete {file_id}"}))
            else:
                print(f"{BOLD}{RED}Failed to delete{RESET} {file_id}.")
            return 1

    if as_json:
        print(json.dumps({"status": "error", "message": "CDP unavailable. Cannot delete."}))
    else:
        print(f"{BOLD}{RED}CDP unavailable{RESET}. Cannot delete file.")
        print(f"  Start debug Chrome with {BOLD}GCS --mcp boot{RESET} first.")
    return 1


def run_mcp_list(folder_spec="~", as_json=False):
    """List files in a Google Drive folder."""
    folder_id = _resolve_folder_id(folder_spec)
    if not folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Cannot resolve folder '{folder_spec}'."}))
        else:
            print(f"{BOLD}{RED}Failed to resolve{RESET} folder '{folder_spec}'.")
        return 1

    if _is_cdp_available():
        from logic.cdp.colab import list_drive_files
        result = list_drive_files(folder_id)
        if result.get("success"):
            files = result.get("files", [])
            if as_json:
                print(json.dumps({"status": "ok", "folder_id": folder_id, "files": files}, indent=2))
            else:
                print(f"{BOLD}Files in {folder_spec}{RESET} ({folder_id}):")
                if not files:
                    print("  (empty)")
                for f in files:
                    size = f.get("size", "")
                    size_str = f" ({size} bytes)" if size else ""
                    mime = f.get("mimeType", "")
                    short_mime = mime.split(".")[-1] if "google-apps" in mime else mime.split("/")[-1]
                    print(f"  {f['name']:35s}  {short_mime:20s}  {f['id']}{size_str}")
            return 0
        else:
            if as_json:
                print(json.dumps({"status": "error", "message": result.get("error", "Unknown")}))
            else:
                print(f"{BOLD}{RED}Failed to list{RESET}. {result.get('error', '')}")
            return 1

    if as_json:
        print(json.dumps({"status": "error", "message": "CDP unavailable. Cannot list files."}))
    else:
        print(f"{BOLD}{RED}CDP unavailable{RESET}. Cannot list files.")
        print(f"  Start debug Chrome with {BOLD}GCS --mcp boot{RESET} first.")
    return 1


def run_mcp_upload(folder_spec="~", as_json=False):
    """Upload a file via browser MCP workflow."""
    folder_id = _resolve_folder_id(folder_spec)
    if not folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Cannot resolve folder '{folder_spec}'."}))
        else:
            print(f"{BOLD}{RED}Failed to resolve{RESET} folder '{folder_spec}'.")
        return 1

    from logic.mcp.drive_create import build_upload_workflow
    workflow = build_upload_workflow(folder_id)

    if as_json:
        print(json.dumps(workflow, indent=2))
    else:
        print(f"{BOLD}{BLUE}Upload workflow{RESET} for folder {folder_spec}.")
        print(f"  Drive URL: {workflow['folder_url']}")
        print(f"  Note: {workflow.get('limitation', '')}")
        print(f"\n  Use {BOLD}GCS --mcp-upload --json{RESET} for structured workflow instructions.")
    return 2
