"""Generic Google Drive file creation via browser MCP.

Supports creating any native Google Workspace file type in a specified folder:
- Google Colaboratory (.ipynb)
- Google Docs
- Google Sheets
- Google Slides
- Google Drawings
- Google My Maps
- Google Sites
- Google AI Studio
- Google Apps Script
- Google Forms
- Google Vids

The workflow uses the Drive UI's "New" menu via the built-in browser.
"""
import json
from logic.mcp.browser import BrowserMCPConfig, BrowserSize


DRIVE_FILE_TYPES = {
    "colab": {
        "menu_path": ["More has submenu", "Google Colaboratory"],
        "display_name": "Google Colaboratory",
        "default_ext": ".ipynb",
    },
    "doc": {
        "menu_path": ["Google Docs has submenu"],
        "display_name": "Google Docs",
        "default_ext": "",
        "submenu": True,
    },
    "sheet": {
        "menu_path": ["Google Sheets has submenu"],
        "display_name": "Google Sheets",
        "default_ext": "",
        "submenu": True,
    },
    "slide": {
        "menu_path": ["Google Slides has submenu"],
        "display_name": "Google Slides",
        "default_ext": "",
        "submenu": True,
    },
    "form": {
        "menu_path": ["Google Forms has submenu"],
        "display_name": "Google Forms",
        "default_ext": "",
        "submenu": True,
    },
    "drawing": {
        "menu_path": ["More has submenu", "Google Drawings"],
        "display_name": "Google Drawings",
        "default_ext": "",
    },
    "mymap": {
        "menu_path": ["More has submenu", "Google My Maps"],
        "display_name": "Google My Maps",
        "default_ext": "",
    },
    "site": {
        "menu_path": ["More has submenu", "Google Sites"],
        "display_name": "Google Sites",
        "default_ext": "",
    },
    "ai_studio": {
        "menu_path": ["More has submenu", "Google AI Studio"],
        "display_name": "Google AI Studio",
        "default_ext": "",
    },
    "apps_script": {
        "menu_path": ["More has submenu", "Google Apps Script"],
        "display_name": "Google Apps Script",
        "default_ext": "",
    },
    "vid": {
        "menu_path": ["Google Vids"],
        "display_name": "Google Vids",
        "default_ext": "",
    },
}


def get_supported_types():
    """Return dict of supported file types with display names."""
    return {k: v["display_name"] for k, v in DRIVE_FILE_TYPES.items()}


def build_create_workflow(folder_id, file_type, filename=None):
    """Build a structured MCP workflow for creating a file in a Drive folder.

    Args:
        folder_id: Google Drive folder ID.
        file_type: One of DRIVE_FILE_TYPES keys (e.g., "colab", "doc", "sheet").
        filename: Optional name for the created file (renames after creation).

    Returns:
        dict with workflow steps for the AI agent to execute.
    """
    if file_type not in DRIVE_FILE_TYPES:
        return {"status": "error", "message": f"Unknown file type: {file_type}. Supported: {list(DRIVE_FILE_TYPES.keys())}"}

    type_info = DRIVE_FILE_TYPES[file_type]
    folder_url = BrowserMCPConfig.drive_folder_url(folder_id)

    steps = [
        {"action": "resize", "description": "Resize browser for Drive menu visibility",
         "mcp_tool": "browser_resize", "args": {"width": 1024, "height": 768}},
        {"action": "navigate", "description": "Open target folder in Drive",
         "mcp_tool": "browser_navigate", "args": {"url": folder_url}},
        {"action": "lock", "description": "Lock browser for automation",
         "mcp_tool": "browser_lock", "args": {}},
        {"action": "click_new", "description": "Click 'New' button",
         "mcp_tool": "browser_click", "args": {"ref": "find:button:New"}},
    ]

    for menu_item in type_info["menu_path"]:
        steps.append({
            "action": "click_menu",
            "description": f"Click '{menu_item}' in menu",
            "mcp_tool": "browser_click",
            "args": {"ref": f"find:menuitem:{menu_item}"},
        })

    if type_info.get("submenu"):
        steps.append({
            "action": "click_blank_submenu",
            "description": f"Click 'Blank {type_info['display_name'].split()[-1].lower()}' in submenu (if present)",
            "mcp_tool": "browser_click",
            "args": {"ref": "find:menuitem:Blank"},
            "note": "Some types show a submenu (Blank, From template). Click the blank option.",
            "optional": True,
        })

    steps.append({
        "action": "handle_shared_dialog",
        "description": "If 'Create in a shared folder?' dialog appears, press Enter",
        "mcp_tool": "browser_press_key",
        "args": {"key": "Enter"},
        "note": "The 'Create and share' button should be auto-focused. Only needed for shared folders.",
        "conditional": True,
    })

    steps.append({
        "action": "wait",
        "description": "Wait for new file tab to open",
        "mcp_tool": "browser_wait_for",
        "args": {"time": 5},
    })

    if filename:
        steps.extend([
            {"action": "rename", "description": f"Rename to {filename}",
             "mcp_tool": "browser_fill",
             "args": {"ref": "find:textbox:Notebook name", "value": filename},
             "note": "The textbox name varies: 'Notebook name' for Colab, may differ for Docs/Sheets."},
            {"action": "confirm_rename", "description": "Press Enter to confirm rename",
             "mcp_tool": "browser_press_key", "args": {"key": "Enter"}},
            {"action": "wait_save", "description": "Wait for rename to save",
             "mcp_tool": "browser_wait_for", "args": {"time": 3}},
        ])

    steps.append({
        "action": "unlock",
        "description": "Unlock browser",
        "mcp_tool": "browser_unlock",
        "args": {},
    })

    steps.append({
        "action": "extract_id",
        "description": "Extract file ID from the new tab's URL",
        "note": "Check the browser tab URL. For Colab: colab.research.google.com/drive/{id}. "
                "For Docs/Sheets/Slides: docs.google.com/{type}/d/{id}/edit",
    })

    return {
        "status": "workflow",
        "file_type": file_type,
        "display_name": type_info["display_name"],
        "target_folder_id": folder_id,
        "folder_url": folder_url,
        "filename": filename,
        "steps": steps,
    }


def build_upload_workflow(folder_id):
    """Build a structured MCP workflow for uploading a local file via Drive UI.

    Args:
        folder_id: Google Drive folder ID to upload into.

    Returns:
        dict with workflow steps.
    """
    folder_url = BrowserMCPConfig.drive_folder_url(folder_id)

    return {
        "status": "workflow",
        "action": "upload",
        "target_folder_id": folder_id,
        "folder_url": folder_url,
        "steps": [
            {"action": "resize", "description": "Resize browser",
             "mcp_tool": "browser_resize", "args": {"width": 1024, "height": 768}},
            {"action": "navigate", "description": "Open target folder in Drive",
             "mcp_tool": "browser_navigate", "args": {"url": folder_url}},
            {"action": "lock", "description": "Lock browser",
             "mcp_tool": "browser_lock", "args": {}},
            {"action": "click_new", "description": "Click 'New' button",
             "mcp_tool": "browser_click", "args": {"ref": "find:button:New"}},
            {"action": "click_upload", "description": "Click 'File upload'",
             "mcp_tool": "browser_click", "args": {"ref": "find:menuitem:File upload"}},
            {"action": "note", "description": "File picker dialog will appear",
             "note": "The browser's native file picker dialog opens. The MCP browser may not be able "
                     "to interact with OS-level dialogs. If the dialog cannot be automated, "
                     "the user must manually select the file. After selection, wait for upload."},
            {"action": "wait_upload", "description": "Wait for upload to complete",
             "mcp_tool": "browser_wait_for", "args": {"time": 10}},
            {"action": "unlock", "description": "Unlock browser",
             "mcp_tool": "browser_unlock", "args": {}},
        ],
        "limitation": "File picker dialogs are OS-level and may not be automatable via MCP browser. "
                      "The user may need to manually select the file.",
    }
