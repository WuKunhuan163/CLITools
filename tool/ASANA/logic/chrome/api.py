"""Asana API operations via Chrome DevTools Protocol.

Uses the authenticated ``app.asana.com`` session to make API calls
through the same-origin Asana REST API at ``/api/1.0/``.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    find_tab,
)

ASANA_URL_PATTERN = "app.asana.com"


def find_asana_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Asana app tab in Chrome."""
    return find_tab(ASANA_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_asana_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def _asana_api(endpoint: str, method: str = "GET", body: dict = None,
               port: int = CDP_PORT, timeout: int = 15) -> Dict[str, Any]:
    """Call an Asana API endpoint via CDP fetch on the app tab.

    For mutating requests (POST/PUT/DELETE), the XSRF token is
    automatically extracted from cookies and sent as a header.
    """
    session = _get_session(port)
    if not session:
        return {"errors": [{"message": "Asana tab not found in Chrome"}]}
    try:
        body_json = json.dumps(body) if body else "null"
        js = f"""
            (async function() {{
                try {{
                    var method = "{method}";
                    var headers = {{"Accept": "application/json", "Content-Type": "application/json"}};
                    if (method !== "GET") {{
                        var xsrf = document.cookie.split(";").map(c => c.trim())
                            .find(c => c.startsWith("xsrf_token="));
                        if (xsrf) headers["X-CSRF-Token"] = xsrf.split("=").slice(1).join("=");
                    }}
                    var opts = {{method: method, credentials: "include", headers: headers}};
                    var bodyData = {body_json};
                    if (bodyData && method !== "GET") opts.body = JSON.stringify(bodyData);
                    var resp = await fetch("/api/1.0{endpoint}", opts);
                    var data = await resp.json();
                    return JSON.stringify({{status: resp.status, response: data}});
                }} catch(e) {{
                    return JSON.stringify({{status: 0, response: {{errors: [{{message: e.toString()}}]}}}});
                }}
            }})()
        """
        raw = session.evaluate(js, timeout=timeout)
        if raw:
            parsed = json.loads(raw)
            result = parsed.get("response", {})
            result["_status"] = parsed.get("status", 0)
            return result
        return {"errors": [{"message": "No response from Asana API"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}
    finally:
        session.close()


def get_me(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the authenticated Asana user info."""
    return _asana_api("/users/me?opt_fields=name,email,workspaces.name,photo", port=port)


def list_workspaces(port: int = CDP_PORT) -> Dict[str, Any]:
    """List all workspaces the user belongs to."""
    return _asana_api("/workspaces?opt_fields=name,is_organization", port=port)


def list_projects(workspace_gid: str, limit: int = 20,
                  port: int = CDP_PORT) -> Dict[str, Any]:
    """List projects in a workspace."""
    return _asana_api(
        f"/workspaces/{workspace_gid}/projects?opt_fields=name,owner.name,created_at,modified_at&limit={limit}",
        port=port,
    )


def list_tasks(workspace_gid: str, assignee: str = "me", limit: int = 20,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """List tasks assigned to a user in a workspace."""
    return _asana_api(
        f"/workspaces/{workspace_gid}/tasks?assignee={assignee}"
        f"&opt_fields=name,completed,due_on,assignee.name&limit={limit}",
        port=port,
    )


def get_task(task_gid: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get details for a specific task."""
    return _asana_api(
        f"/tasks/{task_gid}?opt_fields=name,notes,completed,due_on,assignee.name,projects.name,tags.name",
        port=port,
    )


def create_task(workspace_gid: str, name: str, notes: str = "",
                assignee: str = "me", due_on: str = None,
                project_gid: str = None,
                port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new task."""
    task_data: Dict[str, Any] = {
        "workspace": workspace_gid,
        "name": name,
        "assignee": assignee,
    }
    if notes:
        task_data["notes"] = notes
    if due_on:
        task_data["due_on"] = due_on
    if project_gid:
        task_data["projects"] = [project_gid]
    return _asana_api("/tasks", method="POST", body={"data": task_data}, port=port)


def create_project(workspace_gid: str, name: str, notes: str = "",
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new project in a workspace."""
    return _asana_api(
        "/projects", method="POST",
        body={"data": {"workspace": workspace_gid, "name": name, "notes": notes}},
        port=port,
    )


def complete_task(task_gid: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Mark a task as completed."""
    return _asana_api(
        f"/tasks/{task_gid}", method="PUT",
        body={"data": {"completed": True}}, port=port,
    )


def search_tasks(workspace_gid: str, query: str, limit: int = 10,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Search tasks in a workspace by text."""
    return _asana_api(
        f"/workspaces/{workspace_gid}/tasks/search"
        f"?text={query}&opt_fields=name,completed,assignee.name&limit={limit}",
        port=port,
    )
