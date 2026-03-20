"""Google Drive file operations via CDP + gapi.client.

Uses the user's existing Google auth in the Colab page to perform
Drive API calls (create, delete, list) without requiring a separate
service account or OAuth token.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
)
from tool.GOOGLE.logic.chrome.colab import find_colab_tab

DRIVE_MIME_TYPES = {
    "colab": "application/vnd.google.colaboratory",
    "doc": "application/vnd.google-apps.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "slide": "application/vnd.google-apps.presentation",
    "form": "application/vnd.google-apps.form",
    "drawing": "application/vnd.google-apps.drawing",
    "script": "application/vnd.google-apps.script",
    "site": "application/vnd.google-apps.site",
    "folder": "application/vnd.google-apps.folder",
}


def _get_cdp_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_colab_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Notebook creation
# ---------------------------------------------------------------------------

def create_notebook(name: str, folder_id: str, port: int = CDP_PORT,
                    cell_source: str = "") -> Dict[str, Any]:
    """Create a Colab notebook in a Google Drive folder via CDP + gapi.client."""
    if not is_chrome_cdp_available(port):
        return {"success": False, "error": "Chrome CDP not available"}

    tab = find_colab_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return {"success": False, "error": "No Colab tab found in Chrome"}

    try:
        import websocket as _ws  # noqa: F401
    except ImportError:
        return {"success": False, "error": "websocket-client not installed"}

    session = CDPSession(tab["webSocketDebuggerUrl"])
    try:
        gapi_ok = session.evaluate(
            "typeof gapi !== 'undefined' && gapi.client ? 'ok' : 'no'"
        )
        if gapi_ok != "ok":
            return {"success": False, "error": "gapi.client not available in Colab tab"}

        source_lines = (cell_source or "# GCS Remote Execution Environment").split("\n")
        source_json = json.dumps([line + "\n" for line in source_lines])

        notebook_content = json.dumps({
            "nbformat": 4, "nbformat_minor": 0,
            "metadata": {
                "colab": {"name": name, "provenance": []},
                "kernelspec": {"name": "python3", "display_name": "Python 3"},
            },
            "cells": [{
                "cell_type": "code", "execution_count": None,
                "metadata": {}, "outputs": [],
                "source": json.loads(source_json),
            }],
        })
        nb_content_json = json.dumps(notebook_content)
        name_json = json.dumps(name)
        folder_json = json.dumps(folder_id)

        result_str = session.evaluate(f"""
            (async function() {{
                try {{
                    var nbContent = {nb_content_json};
                    var metadata = {{
                        name: {name_json},
                        mimeType: "application/vnd.google.colaboratory",
                        parents: [{folder_json}]
                    }};
                    var boundary = "----CDPNotebook" + Date.now();
                    var body = "--" + boundary + "\\r\\n";
                    body += 'Content-Type: application/json; charset=UTF-8\\r\\n\\r\\n';
                    body += JSON.stringify(metadata) + "\\r\\n";
                    body += "--" + boundary + "\\r\\n";
                    body += 'Content-Type: application/json\\r\\n\\r\\n';
                    body += nbContent + "\\r\\n";
                    body += "--" + boundary + "--";
                    var resp = await gapi.client.request({{
                        path: '/upload/drive/v3/files',
                        method: 'POST',
                        params: {{uploadType: 'multipart', fields: 'id,name,webViewLink'}},
                        headers: {{'Content-Type': 'multipart/related; boundary=' + boundary}},
                        body: body
                    }});
                    return JSON.stringify({{
                        success: true,
                        id: resp.result.id,
                        name: resp.result.name,
                        link: resp.result.webViewLink
                    }});
                }} catch(e) {{
                    var detail = e.result ? JSON.stringify(e.result).substring(0, 300) : e.toString();
                    return JSON.stringify({{success: false, error: detail}});
                }}
            }})()
        """, timeout=30)

        if not result_str:
            return {"success": False, "error": "No response from gapi.client"}

        data = json.loads(result_str)
        if data.get("success"):
            file_id = data["id"]
            return {
                "success": True, "file_id": file_id,
                "name": data.get("name", name),
                "colab_url": f"https://colab.research.google.com/drive/{file_id}",
            }
        return {"success": False, "error": data.get("error", "Unknown error")}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Generic CRUD
# ---------------------------------------------------------------------------

def delete_drive_file(file_id: str, port: int = CDP_PORT) -> bool:
    """Delete a Google Drive file via CDP + gapi.client."""
    session = _get_cdp_session(port)
    if not session:
        return False
    try:
        result = session.evaluate(f"""
            (async function() {{
                try {{
                    await gapi.client.request({{
                        path: '/drive/v3/files/{file_id}',
                        method: 'DELETE'
                    }});
                    return 'ok';
                }} catch(e) {{ return 'fail'; }}
            }})()
        """)
        return result == "ok"
    except Exception:
        return False
    finally:
        session.close()


def list_drive_files(folder_id: str, query: str = "", port: int = CDP_PORT,
                     page_size: int = 20) -> Dict[str, Any]:
    """List files in a Google Drive folder via CDP + gapi.client."""
    session = _get_cdp_session(port)
    if not session:
        return {"success": False, "error": "CDP session unavailable"}
    try:
        q_parts = [f"'{folder_id}' in parents", "trashed = false"]
        if query:
            q_parts.append(query)
        q_str = " and ".join(q_parts)
        result_str = session.evaluate(f"""
            (async function() {{
                try {{
                    var resp = await gapi.client.request({{
                        path: '/drive/v3/files',
                        method: 'GET',
                        params: {{
                            q: {json.dumps(q_str)},
                            fields: 'files(id,name,mimeType,size,createdTime,modifiedTime)',
                            orderBy: 'modifiedTime desc',
                            pageSize: {page_size}
                        }}
                    }});
                    return JSON.stringify({{success: true, files: resp.result.files || []}});
                }} catch(e) {{
                    var detail = e.result ? JSON.stringify(e.result).substring(0, 500) : e.toString();
                    return JSON.stringify({{success: false, error: detail}});
                }}
            }})()
        """, timeout=15)
        return json.loads(result_str) if result_str else {"success": False, "error": "No response"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def create_drive_file(name: str, file_type: str, folder_id: str,
                      content: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Create any Google Drive file via CDP + gapi.client."""
    mime_type = DRIVE_MIME_TYPES.get(file_type, file_type)

    if file_type == "colab":
        return create_notebook(name, folder_id, port=port, cell_source=content)

    session = _get_cdp_session(port)
    if not session:
        return {"success": False, "error": "CDP session unavailable"}
    try:
        if content:
            name_json = json.dumps(name)
            folder_json = json.dumps(folder_id)
            content_json = json.dumps(content)
            mime_json = json.dumps(mime_type if "/" in mime_type else "text/plain")

            result_str = session.evaluate(f"""
                (async function() {{
                    try {{
                        var boundary = "----CDPCreate" + Date.now();
                        var body = "--" + boundary + "\\r\\n";
                        body += 'Content-Type: application/json; charset=UTF-8\\r\\n\\r\\n';
                        body += JSON.stringify({{
                            name: {name_json},
                            parents: [{folder_json}]
                        }}) + "\\r\\n";
                        body += "--" + boundary + "\\r\\n";
                        body += 'Content-Type: ' + {mime_json} + '\\r\\n\\r\\n';
                        body += {content_json} + "\\r\\n";
                        body += "--" + boundary + "--";
                        var resp = await gapi.client.request({{
                            path: '/upload/drive/v3/files',
                            method: 'POST',
                            params: {{uploadType: 'multipart', fields: 'id,name,mimeType,webViewLink'}},
                            headers: {{'Content-Type': 'multipart/related; boundary=' + boundary}},
                            body: body
                        }});
                        return JSON.stringify({{
                            success: true, id: resp.result.id,
                            name: resp.result.name, link: resp.result.webViewLink || ''
                        }});
                    }} catch(e) {{
                        var detail = e.result ? JSON.stringify(e.result).substring(0, 500) : e.toString();
                        return JSON.stringify({{success: false, error: detail}});
                    }}
                }})()
            """, timeout=20)
        else:
            name_json = json.dumps(name)
            folder_json = json.dumps(folder_id)
            mime_json = json.dumps(mime_type)

            result_str = session.evaluate(f"""
                (async function() {{
                    try {{
                        var resp = await gapi.client.request({{
                            path: '/drive/v3/files',
                            method: 'POST',
                            params: {{fields: 'id,name,mimeType,webViewLink'}},
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                name: {name_json},
                                mimeType: {mime_json},
                                parents: [{folder_json}]
                            }})
                        }});
                        return JSON.stringify({{
                            success: true, id: resp.result.id,
                            name: resp.result.name, link: resp.result.webViewLink || ''
                        }});
                    }} catch(e) {{
                        var detail = e.result ? JSON.stringify(e.result).substring(0, 500) : e.toString();
                        return JSON.stringify({{success: false, error: detail}});
                    }}
                }})()
            """, timeout=15)

        data = json.loads(result_str) if result_str else {"success": False, "error": "No response"}
        return data
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_drive_about(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Drive user and storage info via CDP + gapi.client."""
    session = _get_cdp_session(port)
    if not session:
        return {"success": False, "error": "CDP session unavailable"}
    try:
        result_str = session.evaluate("""
            (async function() {
                try {
                    var resp = await gapi.client.request({
                        path: '/drive/v3/about',
                        method: 'GET',
                        params: {fields: 'user,storageQuota'}
                    });
                    return JSON.stringify({success: true, data: resp.result});
                } catch(e) {
                    return JSON.stringify({success: false, error: e.toString()});
                }
            })()
        """, timeout=10)
        return json.loads(result_str) if result_str else {"success": False, "error": "No response"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()
