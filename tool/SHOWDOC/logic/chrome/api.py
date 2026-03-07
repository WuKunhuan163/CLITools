"""ShowDoc operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP sessions to manage the showdoc.com.cn browser tab.
All data operations go through ShowDoc's REST API (via in-page fetch)
to avoid fragile DOM scraping.  DOM interaction is only used for
visual overlay injection and navigation state checks.

API base: https://showdoc-server.cdn.dfyun.com.cn/server/index.php?s=/api/
Auth: POST FormData with user_token from localStorage['userinfo'].
Response shape: {error_code: 0, data: ...}
"""

import json
import time
import base64
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional, List

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

SHOWDOC_HOME = "https://www.showdoc.com.cn"
SHOWDOC_DASH = "https://www.showdoc.com.cn/item/index"
SHOWDOC_API  = "https://showdoc-server.cdn.dfyun.com.cn/server/index.php?s="
_session_name = "showdoc"

_CDMCP_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "GOOGLE.CDMCP"
_OVERLAY_PATH   = _CDMCP_TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_INTERACT_PATH  = _CDMCP_TOOL_DIR / "logic" / "cdp" / "interact.py"

_sd_session = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_overlay():
    return _load_module("cdmcp_overlay", _OVERLAY_PATH)


def _load_session_mgr():
    return _load_module("cdmcp_session_mgr", _SESSION_MGR_PATH)


def _load_interact():
    return _load_module("cdmcp_interact", _INTERACT_PATH)


def _get_or_create_session(port: int = CDP_PORT):
    global _sd_session
    if _sd_session is not None:
        cdp = _sd_session.get_cdp()
        if cdp:
            return _sd_session
        _sd_session = None

    sm = _load_session_mgr()
    existing = sm.get_session(_session_name)
    if existing:
        cdp = existing.get_cdp()
        if cdp:
            _sd_session = existing
            return existing
        sm.close_session(_session_name)
    return None


def _ensure_cdp(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Return a live CDPSession for the ShowDoc tab, booting if needed."""
    global _sd_session

    session = _get_or_create_session(port)
    if not session:
        r = boot_session(port)
        if not r.get("ok"):
            return None
        session = _get_or_create_session(port)

    if not session:
        return None

    tab_info = session.require_tab(
        "showdoc", url_pattern="showdoc.com.cn",
        open_url=SHOWDOC_DASH, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        return CDPSession(tab_info["ws"])
    return None


def _api_call(cdp: CDPSession, endpoint: str, extra_params: Dict[str, str] = None) -> Any:
    """Call a ShowDoc REST API endpoint via in-page fetch.

    Automatically includes user_token from localStorage.
    Returns parsed JSON data field or raises on error.
    """
    parts = []
    if extra_params:
        for k, v in extra_params.items():
            safe_v = v.replace("'", "\\'").replace("\\", "\\\\")
            parts.append(f"fd.append('{k}', '{safe_v}');")
    extra_js = "\n".join(parts)

    js = f"""
    (async () => {{
        const ui = JSON.parse(localStorage.getItem('userinfo') || '{{}}');
        const token = ui.user_token || '';
        const fd = new FormData();
        fd.append('user_token', token);
        {extra_js}
        const r = await fetch('{SHOWDOC_API}{endpoint}', {{method:'POST', body:fd}});
        return JSON.stringify(await r.json());
    }})()
    """
    raw = cdp.evaluate(js)
    if not raw:
        return None
    parsed = json.loads(raw)
    if parsed.get("error_code", -1) != 0:
        return {"_error": parsed.get("error_message", "API error"), "_raw": parsed}
    return parsed.get("data")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a ShowDoc CDMCP session, opening the tab if needed."""
    global _sd_session

    existing = _get_or_create_session(port)
    if existing:
        return {"ok": True, "action": "already_booted"}

    sm = _load_session_mgr()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)

    if not boot_result.get("ok"):
        return {"ok": False, "error": boot_result.get("error", "Boot failed")}

    _sd_session = boot_result.get("session")

    tab_info = _sd_session.require_tab(
        "showdoc", url_pattern="showdoc.com.cn",
        open_url=SHOWDOC_DASH, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        try:
            overlay = _load_overlay()
            sd_cdp = CDPSession(tab_info["ws"])
            overlay.inject_favicon(sd_cdp, svg_color="#3370ff", letter="S")
            overlay.inject_badge(sd_cdp, text="ShowDoc MCP", color="#3370ff")
        except Exception:
            pass

    return {"ok": True, "action": "booted"}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current CDMCP session status (no boot)."""
    cdp_available = is_chrome_cdp_available(port)
    session = _get_or_create_session(port) if cdp_available else None

    return {
        "cdp_available": cdp_available,
        "cdp_port": port,
        "session_active": session is not None,
        "session_name": _session_name,
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check ShowDoc authentication state via localStorage + DOM."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"authenticated": False, "error": "No CDP session"}

    try:
        url = cdp.evaluate("window.location.href") or ""
        is_login_page = "/user/login" in url or "/user/register" in url

        has_token = cdp.evaluate(
            "!!(JSON.parse(localStorage.getItem('userinfo') || '{}').user_token)"
        )
        has_user_icon = cdp.evaluate(
            "!!document.querySelector('.header-right .icon-item .fa-user')"
        )

        authenticated = bool(has_token) and not is_login_page

        result: Dict[str, Any] = {
            "authenticated": authenticated,
            "url": url,
            "has_token": bool(has_token),
            "has_user_icon": bool(has_user_icon),
            "is_login_page": is_login_page,
        }

        if authenticated:
            user = _api_call(cdp, "/api/user/info")
            if user and not isinstance(user, dict) or (isinstance(user, dict) and "_error" not in user):
                result["user"] = user

        return result
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


def get_user_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get authenticated user profile via API."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/user/info")
    if data and isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "user": data}


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def get_page_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current browser page URL and title."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    try:
        url = cdp.evaluate("window.location.href") or ""
        title = cdp.evaluate("document.title") or ""
        return {"url": url, "title": title}
    except Exception as e:
        return {"error": str(e)}


def navigate_home(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to the ShowDoc project dashboard."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    try:
        cdp.evaluate(f"window.location.href = '{SHOWDOC_DASH}'")
        time.sleep(2)
        return {"ok": True, "url": cdp.evaluate("window.location.href")}
    except Exception as e:
        return {"error": str(e)}


def navigate_to_project(item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a specific project by item_id."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    try:
        url = f"{SHOWDOC_HOME}/{item_id}"
        cdp.evaluate(f"window.location.href = '{url}'")
        time.sleep(3)
        return {
            "ok": True,
            "url": cdp.evaluate("window.location.href"),
            "title": cdp.evaluate("document.title"),
        }
    except Exception as e:
        return {"error": str(e)}


def navigate_to_page(item_id: str, page_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a specific page within a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    try:
        url = f"{SHOWDOC_HOME}/{item_id}/{page_id}"
        cdp.evaluate(f"window.location.href = '{url}'")
        time.sleep(3)
        return {
            "ok": True,
            "url": cdp.evaluate("window.location.href"),
            "title": cdp.evaluate("document.title"),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Projects (items)
# ---------------------------------------------------------------------------

def get_projects(port: int = CDP_PORT) -> Dict[str, Any]:
    """List all user projects via API."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/myList")
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}

    items = data if isinstance(data, list) else []
    projects = []
    for it in items:
        type_map = {"1": "Regular", "4": "Table", "5": "Whiteboard"}
        projects.append({
            "item_id": it.get("item_id", ""),
            "name": it.get("item_name", ""),
            "description": it.get("item_description", ""),
            "type": type_map.get(it.get("item_type", ""), it.get("item_type", "")),
            "is_private": it.get("is_private") == 1 or it.get("is_private") == "1",
            "is_starred": it.get("is_star") == 1 or it.get("is_star") == "1",
        })
    return {"ok": True, "projects": projects}


def get_project_info(item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get full project metadata and document tree via API."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/info", {"item_id": item_id})
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "project": data}


def get_project_groups(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the user's project groups."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/itemGroup/getList")
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "groups": data}


# ---------------------------------------------------------------------------
# Catalog (document tree)
# ---------------------------------------------------------------------------

def get_catalog(item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the catalog (folder tree) for a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/catalog/catList", {"item_id": item_id})
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "catalogs": data}


# ---------------------------------------------------------------------------
# Pages (documents)
# ---------------------------------------------------------------------------

def get_page_content(page_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get a single page's content via API."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/page/info", {"page_id": page_id})
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}

    return {
        "ok": True,
        "page": {
            "page_id": data.get("page_id", ""),
            "title": data.get("page_title", ""),
            "content": data.get("page_content", ""),
            "item_id": data.get("item_id", ""),
            "cat_id": data.get("cat_id", ""),
            "author_uid": data.get("author_uid", ""),
            "author": data.get("author_username", ""),
            "is_draft": data.get("is_draft", "0") == "1",
            "addtime": data.get("addtime", ""),
        },
    }


def get_unread_messages(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get unread message count."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/message/getUnread")
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "messages": data}


# ---------------------------------------------------------------------------
# Visual operations
# ---------------------------------------------------------------------------

def take_screenshot(port: int = CDP_PORT, output: str = "/tmp/showdoc_screenshot.png") -> Dict[str, Any]:
    """Take a screenshot of the ShowDoc page via CDP."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    try:
        result = cdp.send_and_recv("Page.captureScreenshot", {"format": "png"})
        if result and "result" in result:
            img_data = result["result"].get("data", "")
        elif result and "data" in result:
            img_data = result["data"]
        else:
            return {"error": "Screenshot capture returned no data"}

        with open(output, "wb") as f:
            f.write(base64.b64decode(img_data))
        return {"ok": True, "path": output}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Write: Projects
# ---------------------------------------------------------------------------

def create_project(name: str, item_type: str = "1", description: str = "",
                   password: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new project.

    item_type: "1"=Regular, "4"=Table, "5"=Whiteboard
    password: non-empty makes the project private with access password.
    """
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    params = {"item_name": name, "item_type": item_type,
              "item_description": description or name, "password": password}
    data = _api_call(cdp, "/api/item/add", params)
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "item_id": data.get("item_id") if isinstance(data, dict) else data}


def update_project(item_id: str, name: str = None, description: str = None,
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Update an existing project's name or description."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    params: Dict[str, str] = {"item_id": item_id}
    if name is not None:
        params["item_name"] = name
    if description is not None:
        params["item_description"] = description

    data = _api_call(cdp, "/api/item/update", params)
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "data": data}


def delete_project(item_id: str, password: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/delete", {"item_id": item_id, "password": password})
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


def star_project(item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Star a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/star", {"item_id": item_id})
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


def unstar_project(item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Unstar a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/unstar", {"item_id": item_id})
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


def search_project(item_id: str, keyword: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Full-text search within a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/item/search", {"item_id": item_id, "keyword": keyword})
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}

    pages = data.get("pages", []) if isinstance(data, dict) else []
    results = []
    for pg in pages:
        results.append({
            "page_id": pg.get("page_id", ""),
            "title": pg.get("page_title", ""),
            "cat_id": pg.get("cat_id", ""),
            "snippet": pg.get("search_content", "")[:200],
        })
    return {"ok": True, "results": results, "item_name": data.get("item_name", "")}


# ---------------------------------------------------------------------------
# Write: Catalogs (folders)
# ---------------------------------------------------------------------------

def create_catalog(item_id: str, cat_name: str, parent_cat_id: str = "0",
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new catalog (folder) in a project."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    params = {"item_id": item_id, "cat_name": cat_name,
              "parent_cat_id": parent_cat_id, "s_number": "99"}
    data = _api_call(cdp, "/api/catalog/save", params)
    if data is None:
        return {"error": "API returned no data"}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}

    cat_id = str(data) if not isinstance(data, dict) else data.get("cat_id", data)
    return {"ok": True, "cat_id": cat_id}


def rename_catalog(cat_id: str, cat_name: str, item_id: str,
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Rename an existing catalog."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/catalog/save",
                     {"cat_id": cat_id, "cat_name": cat_name, "item_id": item_id})
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


def delete_catalog(cat_id: str, item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete a catalog and its contents."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/catalog/delete", {"cat_id": cat_id, "item_id": item_id})
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


# ---------------------------------------------------------------------------
# Write: Pages
# ---------------------------------------------------------------------------

def _api_call_raw(cdp: CDPSession, endpoint: str, params: Dict[str, str]) -> Any:
    """Like _api_call but builds JS using concatenation to handle newlines in values."""
    param_lines = []
    for k, v in params.items():
        escaped = v.replace("\\", "\\\\").replace("'", "\\'")
        param_lines.append(
            f"fd.append('{k}', '{escaped}');"
        )
    extra = " ".join(param_lines)

    js = (
        "(async () => {"
        "const ui = JSON.parse(localStorage.getItem('userinfo') || '{}');"
        "const fd = new FormData();"
        "fd.append('user_token', ui.user_token);"
        f"{extra}"
        f"const r = await fetch('{SHOWDOC_API}{endpoint}', {{method:'POST', body:fd}});"
        "return JSON.stringify(await r.json());"
        "})()"
    )
    raw = cdp.evaluate(js)
    if not raw:
        return None
    parsed = json.loads(raw)
    if parsed.get("error_code", -1) != 0:
        return {"_error": parsed.get("error_message", "API error"), "_raw": parsed}
    return parsed.get("data")


def save_page(item_id: str, page_title: str, page_content: str,
              cat_id: str = "0", page_id: str = None,
              port: int = CDP_PORT) -> Dict[str, Any]:
    """Create or update a page.

    If page_id is provided, updates that page. Otherwise creates a new one.
    Content uses ShowDoc's markdown format.
    """
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    safe_title = page_title.replace("\\", "\\\\").replace("'", "\\'")
    safe_content = page_content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")

    parts = [
        f"fd.append('item_id', '{item_id}');",
        f"fd.append('cat_id', '{cat_id}');",
        f"fd.append('page_title', '{safe_title}');",
        f"fd.append('page_content', '{safe_content}');",
        "fd.append('s_number', '99');",
    ]
    if page_id:
        parts.append(f"fd.append('page_id', '{page_id}');")

    extra = " ".join(parts)
    js = (
        "(async () => {"
        "const ui = JSON.parse(localStorage.getItem('userinfo') || '{}');"
        "const fd = new FormData();"
        "fd.append('user_token', ui.user_token);"
        f"{extra}"
        f"const r = await fetch('{SHOWDOC_API}/api/page/save', {{method:'POST', body:fd}});"
        "return JSON.stringify(await r.json());"
        "})()"
    )

    raw = cdp.evaluate(js)
    if not raw:
        return {"error": "API returned no data"}
    parsed = json.loads(raw)
    if parsed.get("error_code", -1) != 0:
        return {"error": parsed.get("error_message", "Save failed")}

    data = parsed.get("data", {})
    return {
        "ok": True,
        "page_id": data.get("page_id", "") if isinstance(data, dict) else str(data),
        "action": "updated" if page_id else "created",
    }


def delete_page(page_id: str, item_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete a page."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/page/delete", {"page_id": page_id, "item_id": item_id})
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True}


def get_page_history(page_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get revision history for a page."""
    cdp = _ensure_cdp(port)
    if not cdp:
        return {"error": "No CDP session"}

    data = _api_call(cdp, "/api/page/history", {"page_id": page_id})
    if data is None:
        return {"ok": True, "history": []}
    if isinstance(data, dict) and "_error" in data:
        return {"error": data["_error"]}
    return {"ok": True, "history": data if isinstance(data, list) else []}
