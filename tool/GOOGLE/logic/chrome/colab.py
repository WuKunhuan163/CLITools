"""Google Colab cell injection and execution via Chrome DevTools Protocol.

Finds the Colab notebook tab, injects Python code into the first cell,
executes it, and polls for completion (by CSS state or done-marker).
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from tool.GOOGLE.logic.chrome.session import (
    CDPSession, CDP_PORT, CDP_TIMEOUT,
    is_chrome_cdp_available, open_tab,
)


# ---------------------------------------------------------------------------
# Tab discovery
# ---------------------------------------------------------------------------

def find_colab_tab(port: int = CDP_PORT) -> Optional[Dict]:
    """Find a Colab notebook tab in the debug Chrome."""
    try:
        import urllib.request
        url = f"http://localhost:{port}/json/list"
        with urllib.request.urlopen(url, timeout=5) as resp:
            tabs = json.loads(resp.read().decode())
        for tab in tabs:
            if "colab" in tab.get("url", "").lower() and tab.get("type") == "page":
                return tab
        return None
    except Exception:
        return None


def reopen_colab_tab(port: int = CDP_PORT, log_fn: Callable = None) -> Optional[Dict]:
    """Attempt to reopen the configured Colab notebook tab.

    Reads the notebook URL from GCS config and opens it via CDP.
    If the notebook was deleted, recreates it first.
    """
    _log = log_fn or (lambda m: None)

    config_path = _find_gcs_config()
    if not config_path or not config_path.exists():
        return None
    try:
        with open(config_path, "r") as f:
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

    open_tab(notebook_url, port)
    _log("Reopened Colab tab. Waiting for page to load...")

    for i in range(20):
        time.sleep(1)
        tab = find_colab_tab(port)
        if tab:
            _log(f"Colab tab detected after {i + 1}s. Checking notebook...")
            time.sleep(5)
            session = CDPSession(tab["webSocketDebuggerUrl"])
            try:
                repaired = _repair_notebook_if_needed(
                    session, notebook_id, env_folder_id, cfg, config_path, port, _log
                )
                if repaired == "recreated":
                    new_url = cfg.get("root_notebook_url", "")
                    session.close()
                    open_tab(new_url, port)
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


# ---------------------------------------------------------------------------
# Cell injection & execution
# ---------------------------------------------------------------------------

def inject_and_execute(code: str, port: int = CDP_PORT, timeout: int = 300,
                       done_marker: str = "", log_fn: Callable = None) -> Dict[str, Any]:
    """Inject code into the first Colab cell and execute it.

    Args:
        code:        Python code to inject.
        port:        Chrome CDP port.
        timeout:     Max seconds to wait for completion.
        done_marker: Unique marker to detect completion in cell output.
        log_fn:      Optional logger ``(str) -> None``.

    Returns:
        dict with keys: success, output, error, state, duration
    """
    _log = log_fn or (lambda m: None)
    start_time = time.time()

    if not is_chrome_cdp_available(port):
        return {"success": False, "error": f"Chrome CDP not available on port {port}"}

    tab = find_colab_tab(port)
    if not tab:
        _log("Colab tab not found. Attempting to reopen...")
        tab = reopen_colab_tab(port, _log)
        if not tab:
            return {"success": False, "error": "No Colab tab found in Chrome (reboot failed)"}

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return {"success": False, "error": "No WebSocket URL for Colab tab"}

    try:
        import websocket as _ws_check  # noqa: F401
    except ImportError:
        return {"success": False, "error": "websocket-client not installed"}

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
            if pre_state and ("running" in pre_state or "pending" in pre_state):
                break

        poll_js = _build_poll_js(done_marker)
        for i in range(timeout // 2):
            time.sleep(2)
            state = session.evaluate(poll_js)
            if not state:
                continue

            info = json.loads(state)

            if done_marker and info.get("marker_found"):
                duration = time.time() - start_time
                _log(f"Completion marker [{done_marker}] detected in {duration:.1f}s")
                return {
                    "success": not info["error"],
                    "output": info.get("output", ""),
                    "errors": info.get("errors", ""),
                    "error_flag": info["error"],
                    "duration": duration,
                    "state": "completed",
                    "detected_by": "marker",
                }

            if not info["running"] and not info["pending"]:
                duration = time.time() - start_time
                _log(f"Execution completed (CSS state) in {duration:.1f}s")
                return {
                    "success": not info["error"],
                    "output": info.get("output", ""),
                    "errors": info.get("errors", ""),
                    "error_flag": info["error"],
                    "duration": duration,
                    "state": "completed",
                    "detected_by": "css_state",
                }

            if (i + 1) * 2 % 20 == 0:
                _log(f"Still running ({(i + 1) * 2}s)...")

        duration = time.time() - start_time
        return {
            "success": False,
            "error": f"Execution timed out after {timeout}s",
            "duration": duration,
            "state": "timeout",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "state": "exception"}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_gcs_config() -> Optional[Path]:
    """Locate the GCS data/config.json relative to the GOOGLE tool."""
    p = Path(__file__).resolve().parent.parent.parent.parent  # → tool/
    config = p / "GOOGLE.GCS" / "data" / "config.json"
    if config.exists():
        return config
    p2 = p.parent  # project root
    config2 = p2 / "data" / "config.json"
    return config2 if config2.exists() else None


def _build_poll_js(done_marker: str = "") -> str:
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


def _repair_notebook_if_needed(session, notebook_id, env_folder_id,
                               cfg, config_path, port, log_fn):
    """Check if the notebook is accessible; recreate if trashed/deleted."""
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
        needs_recreate, reason = True, "trashed"
    elif data.get("error"):
        needs_recreate, reason = True, "not accessible"
    else:
        trash_on_page = session.evaluate("""
        (function() {
            var body = document.body ? document.body.innerText : '';
            return body.includes('moved to the trash') || body.includes('Moved to the trash');
        })()
        """)
        if trash_on_page is True or trash_on_page == "true":
            needs_recreate, reason = True, "trash banner on page"

    if not needs_recreate:
        return None

    log_fn(f"Notebook {reason}. Recreating {notebook_name}...")
    if not env_folder_id:
        log_fn("No env_folder_id. Cannot recreate.")
        return None

    from tool.GOOGLE.logic.chrome.drive import create_notebook
    result = create_notebook(notebook_name, env_folder_id, port)
    if result.get("success"):
        cfg["root_notebook_id"] = result["file_id"]
        cfg["root_notebook_url"] = result["colab_url"]
        try:
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass
        log_fn(f"Recreated {notebook_name} ({result['file_id']}).")
        return "recreated"
    elif log_fn:
        log_fn(f"Failed to recreate: {result.get('error')}")
    return None
