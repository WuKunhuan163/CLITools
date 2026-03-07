"""Chrome DevTools Protocol (CDP) integration for Colab cell injection and execution.

Connects to a Chrome instance with --remote-debugging-port enabled,
finds the Colab notebook tab, injects code into a cell, and executes it.

Requirements:
  - Chrome running with: --remote-debugging-port=9222 --remote-allow-origins=*
  - websocket-client package (pip install websocket-client)
  - Colab notebook open in Chrome
"""
import json
import time
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any

CDP_PORT = 9222
CDP_TIMEOUT = 15


def is_chrome_cdp_available(port: int = CDP_PORT) -> bool:
    """Check if Chrome DevTools Protocol is reachable."""
    try:
        url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return "Browser" in data
    except Exception:
        return False


def find_colab_tab(port: int = CDP_PORT) -> Optional[Dict]:
    """Find a Colab notebook tab in the debug Chrome."""
    try:
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=5) as resp:
            tabs = json.loads(resp.read().decode())
        for tab in tabs:
            if 'colab' in tab.get('url', '').lower() and tab.get('type') == 'page':
                return tab
        return None
    except Exception:
        return None


class CDPSession:
    """Lightweight Chrome DevTools Protocol session over WebSocket."""

    def __init__(self, ws_url: str, timeout: int = 30):
        import websocket
        self.ws = websocket.create_connection(ws_url, timeout=timeout)
        self._msg_id = 0

    def send_and_recv(self, method: str, params: dict = None, timeout: int = CDP_TIMEOUT):
        self._msg_id += 1
        msg = {"id": self._msg_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        self.ws.settimeout(timeout)
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data = json.loads(self.ws.recv())
                if data.get("id") == self._msg_id:
                    return data
            except Exception:
                break
        return None

    def evaluate(self, expression: str, timeout: int = CDP_TIMEOUT) -> Any:
        """Evaluate JavaScript in the page and return the result value."""
        result = self.send_and_recv("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        }, timeout=timeout)
        if result and 'result' in result:
            r = result['result'].get('result', {})
            if 'value' in r:
                return r['value']
            return r.get('description', str(r))
        return None

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def _reopen_colab_tab(port: int = CDP_PORT, log_fn=None) -> Optional[Dict]:
    """Attempt to reopen the configured Colab notebook tab.

    Reads the notebook URL from config and opens it via CDP Target.createTarget.
    If the notebook was deleted, recreates it first.
    Returns the tab dict if successful, None otherwise.
    """
    config_path = Path(__file__).resolve().parent.parent.parent / "data" / "config.json"
    if not config_path.exists():
        return None
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
    except Exception:
        return None

    notebook_id = cfg.get("root_notebook_id", "")
    env_folder_id = cfg.get("env_folder_id", "")
    notebook_url = cfg.get("root_notebook_url", "")
    if not notebook_url and notebook_id:
        notebook_url = f"https://colab.research.google.com/drive/{notebook_id}"

    if not notebook_url:
        return None

    def _open_url_in_chrome(url):
        try:
            version_url = f"http://localhost:{port}/json/version"
            with urllib.request.urlopen(version_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if not browser_ws:
                return False
            import websocket
            ws = websocket.create_connection(browser_ws, timeout=15)
            try:
                ws.send(json.dumps({"id": 1, "method": "Target.createTarget", "params": {"url": url}}))
                ws.settimeout(10)
                for _ in range(20):
                    r = json.loads(ws.recv())
                    if r.get("id") == 1:
                        return True
            finally:
                ws.close()
        except Exception as e:
            if log_fn:
                log_fn(f"Failed to open URL: {e}")
        return False

    _open_url_in_chrome(notebook_url)
    if log_fn:
        log_fn("Reopened Colab tab. Waiting for page to load...")

    for i in range(20):
        time.sleep(1)
        tab = find_colab_tab(port)
        if tab:
            if log_fn:
                log_fn(f"Colab tab detected after {i+1}s. Checking notebook...")
            time.sleep(5)
            session = CDPSession(tab["webSocketDebuggerUrl"])
            try:
                repaired = _repair_notebook_if_needed(
                    session, notebook_id, env_folder_id, cfg, config_path, port, log_fn
                )
                if repaired == "recreated":
                    new_url = cfg.get("root_notebook_url", "")
                    session.close()
                    _open_url_in_chrome(new_url)
                    for j in range(15):
                        time.sleep(1)
                        tab = find_colab_tab(port)
                        if tab:
                            time.sleep(5)
                            return tab
                    return None
            except Exception:
                pass
            finally:
                try:
                    session.close()
                except Exception:
                    pass
            return tab
    return None


def _repair_notebook_if_needed(session, notebook_id, env_folder_id, cfg, config_path, port, log_fn):
    """Check if the notebook is accessible and recreate if not.
    
    Any non-normal state (trashed, deleted, inaccessible, trash banner) triggers
    a full recreation rather than attempting recovery from trash.
    
    Returns:
        None: notebook is fine
        "recreated": was not accessible, recreated with new ID
    """
    if not notebook_id:
        return None

    notebook_name = cfg.get("root_notebook_name", ".root.ipynb")
    needs_recreate = False
    reason = ""

    drive_check = session.evaluate(f"""
    (async function() {{
        try {{
            var resp = await gapi.client.request({{
                path: '/drive/v3/files/{notebook_id}',
                method: 'GET',
                params: {{fields: 'id,name,trashed'}}
            }});
            return JSON.stringify(resp.result);
        }} catch(e) {{
            return JSON.stringify({{error: String(e)}});
        }}
    }})()
    """)

    if not drive_check:
        return None

    try:
        data = json.loads(drive_check)
    except Exception:
        return None

    if data.get("trashed"):
        needs_recreate = True
        reason = "trashed"
    elif data.get("error"):
        needs_recreate = True
        reason = "not accessible"
    else:
        trash_on_page = session.evaluate("""
        (function() {
            var body = document.body ? document.body.innerText : '';
            return body.includes('moved to the trash') || body.includes('Moved to the trash');
        })()
        """)
        if trash_on_page == True or trash_on_page == "true":
            needs_recreate = True
            reason = "trash banner on page"

    if not needs_recreate:
        return None

    if log_fn:
        log_fn(f"Notebook {reason}. Recreating {notebook_name}...")
    if not env_folder_id:
        if log_fn:
            log_fn("No env_folder_id. Cannot recreate.")
        return None

    result = create_notebook(notebook_name, env_folder_id, port)
    if result.get("success"):
        cfg["root_notebook_id"] = result["file_id"]
        cfg["root_notebook_url"] = result["colab_url"]
        try:
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass
        if log_fn:
            log_fn(f"Recreated {notebook_name} ({result['file_id']}).")
        return "recreated"
    elif log_fn:
        log_fn(f"Failed to recreate: {result.get('error')}")

    return None


def inject_and_execute(code: str, port: int = CDP_PORT, timeout: int = 300,
                       done_marker: str = "", log_fn=None) -> Dict[str, Any]:
    """Inject code into the first Colab cell and execute it.

    Args:
        code: Python code to inject and execute.
        port: Chrome CDP port.
        timeout: Max seconds to wait for execution to complete.
        done_marker: Unique marker string (e.g. "GCS_DONE_abc12345") to detect
                     completion in the cell output. If provided, the polling loop
                     looks for this marker instead of relying solely on CSS state.
        log_fn: Optional logging function (receives string messages).

    Returns:
        dict with keys: success, output, error, state, duration
    """
    def _log(msg):
        if log_fn:
            log_fn(msg)

    start_time = time.time()

    if not is_chrome_cdp_available(port):
        return {"success": False, "error": "Chrome CDP not available on port " + str(port)}

    tab = find_colab_tab(port)
    if not tab:
        _log("Colab tab not found. Attempting to reopen...")
        tab = _reopen_colab_tab(port, _log)
        if not tab:
            return {"success": False, "error": "No Colab tab found in Chrome (reboot failed)"}

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return {"success": False, "error": "No WebSocket URL for Colab tab"}

    try:
        import websocket as _ws_check  # noqa: F401
    except ImportError:
        return {"success": False, "error": "websocket-client not installed (pip install websocket-client)"}

    session = CDPSession(ws_url)

    try:
        cell_count = session.evaluate(
            "colab.global.notebook.cells ? colab.global.notebook.cells.length : 0"
        )
        if not cell_count or int(cell_count) == 0:
            _log("No cells found. Adding a code cell...")
            session.evaluate("colab.global.notebook.addCell('code', {cellIndex: 0})")
            time.sleep(1)

        code_json = json.dumps(code)
        session.evaluate(f"colab.global.notebook.cells[0].setText({code_json})")
        time.sleep(0.3)

        actual = session.evaluate("colab.global.notebook.cells[0].getText()")
        _log(f"Code injected ({len(actual or '')} chars)")

        session.evaluate("document.querySelector('colab-run-button').click()")
        _log("Execution started")

        for _ in range(10):
            time.sleep(0.5)
            pre_state = session.evaluate("""
                (function() {
                    var rb = document.querySelector('colab-run-button');
                    var sd = rb && rb.shadowRoot ? rb.shadowRoot.querySelector('.cell-execution') : null;
                    return sd ? sd.className : '';
                })()
            """)
            if pre_state and ('running' in pre_state or 'pending' in pre_state):
                break

        poll_js = _build_poll_js(done_marker)
        for i in range(timeout // 2):
            time.sleep(2)
            state = session.evaluate(poll_js)
            if not state:
                continue

            info = json.loads(state)

            if done_marker and info.get('marker_found'):
                duration = time.time() - start_time
                _log(f"Completion marker [{done_marker}] detected in {duration:.1f}s")
                return {
                    "success": not info['error'],
                    "output": info.get('output', ''),
                    "errors": info.get('errors', ''),
                    "error_flag": info['error'],
                    "duration": duration,
                    "state": "completed",
                    "detected_by": "marker"
                }

            if not info['running'] and not info['pending']:
                duration = time.time() - start_time
                _log(f"Execution completed (CSS state) in {duration:.1f}s")
                return {
                    "success": not info['error'],
                    "output": info.get('output', ''),
                    "errors": info.get('errors', ''),
                    "error_flag": info['error'],
                    "duration": duration,
                    "state": "completed",
                    "detected_by": "css_state"
                }

            if (i + 1) * 2 % 20 == 0:
                _log(f"Still running ({(i+1)*2}s)...")

        duration = time.time() - start_time
        return {
            "success": False,
            "error": f"Execution timed out after {timeout}s",
            "duration": duration,
            "state": "timeout"
        }

    except Exception as e:
        return {"success": False, "error": str(e), "state": "exception"}
    finally:
        session.close()


def _build_poll_js(done_marker: str = "") -> str:
    """Build the JavaScript polling expression for cell state and output."""
    marker_check = ""
    if done_marker:
        marker_json = json.dumps(done_marker)
        marker_check = f"var markerFound = fullText.includes({marker_json});"
    else:
        marker_check = "var markerFound = false;"

    return f"""
        (function() {{
            var runBtn = document.querySelector('colab-run-button');
            var sd = runBtn && runBtn.shadowRoot ?
                runBtn.shadowRoot.querySelector('.cell-execution') : null;
            var classes = sd ? sd.className : '';
            var cell = document.querySelector('.cell.code');
            var outEls = cell ? cell.querySelectorAll('.output_text, .output_stream') : [];
            var fullText = '';
            outEls.forEach(function(e) {{ fullText += e.textContent + '\\n'; }});
            var errEls = cell ? cell.querySelectorAll('.output_error, .ansi-red-fg') : [];
            var errText = '';
            errEls.forEach(function(e) {{ errText += e.textContent.trim() + '\\n'; }});
            {marker_check}
            return JSON.stringify({{
                running: classes.includes('running'),
                pending: classes.includes('pending'),
                error: classes.includes('error'),
                output: fullText.trim().substring(0, 4000),
                errors: errText.substring(0, 2000),
                marker_found: markerFound
            }});
        }})()
    """


def create_notebook(name: str, folder_id: str, port: int = CDP_PORT,
                    cell_source: str = "") -> Dict[str, Any]:
    """Create a Colab notebook in a Google Drive folder via CDP + gapi.client.

    Uses the user's existing Google auth in the Colab page to create the
    notebook with valid content. Requires an existing Colab tab open in
    the debug Chrome.

    Args:
        name: Notebook filename (e.g. ".root.ipynb").
        folder_id: Google Drive folder ID to place the notebook in.
        port: Chrome CDP port.
        cell_source: Optional Python code for the first cell.

    Returns:
        dict with keys: success, file_id, name, colab_url, error
    """
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
        gapi_ok = session.evaluate("""
            typeof gapi !== 'undefined' && gapi.client ? 'ok' : 'no'
        """)
        if gapi_ok != "ok":
            return {"success": False, "error": "gapi.client not available in Colab tab"}

        source_lines = (cell_source or "# GCS Remote Execution Environment").split("\n")
        source_json = json.dumps([line + "\n" for line in source_lines])

        notebook_content = json.dumps({
            "nbformat": 4,
            "nbformat_minor": 0,
            "metadata": {
                "colab": {"name": name, "provenance": []},
                "kernelspec": {"name": "python3", "display_name": "Python 3"}
            },
            "cells": [{
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": json.loads(source_json)
            }]
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
                "success": True,
                "file_id": file_id,
                "name": data.get("name", name),
                "colab_url": f"https://colab.research.google.com/drive/{file_id}"
            }
        return {"success": False, "error": data.get("error", "Unknown error")}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def delete_drive_file(file_id: str, port: int = CDP_PORT) -> bool:
    """Delete a Google Drive file via CDP + gapi.client."""
    tab = find_colab_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return False
    session = CDPSession(tab["webSocketDebuggerUrl"])
    try:
        result = session.evaluate(f"""
            (async function() {{
                try {{
                    await gapi.client.request({{
                        path: '/drive/v3/files/{file_id}',
                        method: 'DELETE'
                    }});
                    return 'ok';
                }} catch(e) {{
                    return 'fail';
                }}
            }})()
        """)
        return result == "ok"
    except Exception:
        return False
    finally:
        session.close()
