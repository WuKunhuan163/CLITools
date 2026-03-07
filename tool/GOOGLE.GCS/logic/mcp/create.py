"""Generic MCP file creation command for GCS.

Creates any Google Drive native file type in a GCS-accessible folder.
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
from logic.mcp.drive_create import build_create_workflow, build_upload_workflow, get_supported_types

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
BLUE = get_color("BLUE")
RESET = get_color("RESET")


def _load_config():
    config_path = _project_root / "data" / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, 'r') as f:
        return json.load(f)


def _resolve_folder_id(path_spec):
    """Resolve a path spec to a folder ID.

    Supports:
        ~ or root → root_folder_id
        @ or env  → env_folder_id
        <folder_id> → used directly
    """
    cfg = _load_config()
    if path_spec in ("~", "root"):
        return cfg.get("root_folder_id", "")
    if path_spec in ("@", "env"):
        return cfg.get("env_folder_id", "")
    return path_spec


def run_mcp_create(file_type, folder_spec="~", filename=None, as_json=False):
    """Create a new Drive file via browser MCP workflow.

    Args:
        file_type: Type of file (colab, doc, sheet, slide, etc.)
        folder_spec: Folder path spec (~, @, or folder ID)
        filename: Optional filename for the created file
        as_json: Output as JSON
    """
    supported = get_supported_types()
    if file_type not in supported:
        if as_json:
            print(json.dumps({"status": "error", "types": supported}))
        else:
            print(f"{BOLD}{RED}Unknown type{RESET} '{file_type}'.")
            print(f"  Supported: {', '.join(supported.keys())}")
        return 1

    folder_id = _resolve_folder_id(folder_spec)
    if not folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Cannot resolve folder '{folder_spec}'. Run GCS --setup-tutorial first."}))
        else:
            print(f"{BOLD}{RED}Failed to resolve{RESET} folder '{folder_spec}'.")
            print(f"  Run {BOLD}GCS --setup-tutorial{RESET} first.")
        return 1

    workflow = build_create_workflow(folder_id, file_type, filename)

    if as_json:
        print(json.dumps(workflow, indent=2))
    else:
        display = supported[file_type]
        print(f"{BOLD}{BLUE}Creating{RESET} {display}" + (f" as '{filename}'" if filename else "") + f" in folder {folder_spec}.")
        print(f"  Drive URL: {workflow['folder_url']}")
        print(f"\n  Use {BOLD}GCS --mcp-create {file_type} --json{RESET} for structured workflow instructions.")
        print(f"  The agent should follow the workflow steps using browser MCP tools.")
    return 2


def run_mcp_upload(folder_spec="~", as_json=False):
    """Upload a file via browser MCP workflow.

    Args:
        folder_spec: Folder path spec (~, @, or folder ID)
        as_json: Output as JSON
    """
    folder_id = _resolve_folder_id(folder_spec)
    if not folder_id:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Cannot resolve folder '{folder_spec}'."}))
        else:
            print(f"{BOLD}{RED}Failed to resolve{RESET} folder '{folder_spec}'.")
        return 1

    workflow = build_upload_workflow(folder_id)

    if as_json:
        print(json.dumps(workflow, indent=2))
    else:
        print(f"{BOLD}{BLUE}Upload workflow{RESET} for folder {folder_spec}.")
        print(f"  Drive URL: {workflow['folder_url']}")
        print(f"  Note: {workflow.get('limitation', '')}")
        print(f"\n  Use {BOLD}GCS --mcp-upload --json{RESET} for structured workflow instructions.")
    return 2
