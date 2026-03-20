"""Google Colab cell injection and execution via Chrome DevTools Protocol.

Finds the Colab notebook tab, injects Python code into the first cell,
executes it, and polls for completion (by CSS state or done-marker).
"""
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from interface.chrome import (
    CDPSession, CDP_PORT, is_chrome_cdp_available, open_tab, list_tabs,
)


def _open_in_session_window(url: str, port: int = CDP_PORT):
    """Open a URL in the CDMCP session window if available, otherwise any window."""
    window_id = None
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
        from interface.cdmcp import load_cdmcp_sessions
        sm = load_cdmcp_sessions()
        for info in sm.list_sessions():
            wid = info.get("window_id")
            if wid:
                window_id = wid
                break
    except Exception:
        pass

    if window_id:
        try:
            import urllib.request
            ver_url = f"http://localhost:{port}/json/version"
            with urllib.request.urlopen(ver_url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            browser_ws = data.get("webSocketDebuggerUrl")
            if browser_ws:
                s = CDPSession(browser_ws, timeout=10)
                s.send_and_recv("Target.createTarget", {
                    "url": url,
                    "newWindow": False,
                    "windowId": window_id,
                })
                s.close()
                return True
        except Exception:
            pass

    return open_tab(url, port)


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
    """Open a Colab tab via CDP.

    Opens the Colab homepage if no specific URL is available.
    """
    _log = log_fn or (lambda m: None)

    colab_url = "https://colab.research.google.com/"

    _open_in_session_window(colab_url, port)
    _log("Opened Colab tab. Waiting for page to load...")

    for i in range(20):
        time.sleep(1)
        tab = find_colab_tab(port)
        if tab:
            _log(f"Colab tab detected after {i + 1}s.")
            time.sleep(3)
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
            "(function(){ var c = colab.global.notebook.cells;"
            " return (Array.isArray(c) && c.length > 0 && typeof c[0].setText === 'function') ? c.length : 0; })()"
        )
        if not cell_count or int(cell_count) == 0:
            _log("No cells found. Adding a code cell...")
            add_result = session.evaluate(
                "(function(){ try { colab.global.notebook.addCell('code', {cellIndex: 0});"
                " return 'ok'; } catch(e) { return 'error:' + e.message; } })()"
            )
            if add_result and str(add_result).startswith("error:"):
                _log(f"API addCell failed ({add_result}). Using toolbar...")
            time.sleep(2)
            verify = session.evaluate(
                "(function(){ return document.querySelectorAll('.cell.code').length; })()"
            )
            if not verify or int(verify) == 0:
                _log("Clicking toolbar button to add cell...")
                session.evaluate(
                    "(function(){ var b = document.querySelector('#toolbar-add-code');"
                    " if(b) { b.click(); return 'clicked'; }"
                    " var hover = document.querySelector('.add-cell');"
                    " if(hover) { hover.dispatchEvent(new MouseEvent('mouseenter', {bubbles:true}));"
                    "   setTimeout(function(){ var c = document.querySelector('.add-code');"
                    "     if(c) c.click(); }, 500); return 'hover-clicked'; }"
                    " return 'none'; })()"
                )
                time.sleep(3)

        code_json = json.dumps(code)
        set_result = session.evaluate(
            f"(function(){{ var cell = document.querySelector('.cell.code');"
            f" if(!cell) return 'no-cell';"
            f" var me = cell.querySelector('.monaco-editor');"
            f" if(me && typeof monaco !== 'undefined') {{"
            f"   var editors = monaco.editor.getEditors();"
            f"   for(var i=0;i<editors.length;i++) {{"
            f"     var dom = editors[i].getDomNode();"
            f"     if(cell.contains(dom)) {{"
            f"       editors[i].setValue({code_json});"
            f"       return 'monaco:' + editors[i].getValue().length;"
            f"     }}"
            f"   }}"
            f" }}"
            f" try {{ colab.global.notebook.cells[0].setText({code_json}); return 'api:ok'; }}"
            f" catch(e) {{ return 'error:' + e.message; }}"
            f" }})()"
        )
        time.sleep(0.5)

        actual_len = 0
        if set_result and "monaco:" in str(set_result):
            actual_len = int(str(set_result).split(":")[1])
        else:
            actual = session.evaluate("colab.global.notebook.cells[0].getText()")
            actual_len = len(actual or "")
        _log(f"Code injected ({actual_len} chars)")

        pre_run_output = session.evaluate(
            "(function(){ var cell = document.querySelector('.cell.code');"
            " var out = cell ? cell.querySelector('.output-content') : null;"
            " return out ? out.textContent.trim().substring(0,200) : ''; })()"
        )

        session.evaluate(
            "(function(){ var cell = document.querySelector('.cell.code');"
            " var rb = cell ? cell.querySelector('colab-run-button') : document.querySelector('colab-run-button');"
            " if(rb) rb.click(); })()"
        )
        _log("Execution started")

        saw_running = False
        for _ in range(20):
            time.sleep(0.5)
            pre_state = session.evaluate("""
                (function() {
                    var cell = document.querySelector('.cell.code');
                    var rb = cell ? cell.querySelector('colab-run-button') : document.querySelector('colab-run-button');
                    var sd = rb && rb.shadowRoot ? rb.shadowRoot.querySelector('.cell-execution') : null;
                    return sd ? sd.className : '';
                })()
            """)
            if pre_state and ("running" in pre_state or "pending" in pre_state):
                saw_running = True
                break

        if not saw_running:
            time.sleep(3)

        poll_js = _build_poll_js(done_marker)
        settled_count = 0
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
                current_output = info.get("output", "").strip()
                current_errors = info.get("errors", "").strip()
                is_new = saw_running or (current_output and current_output != (pre_run_output or "").strip())
                if is_new or settled_count >= 2:
                    if not current_output and not current_errors:
                        iframe_data = _read_output_iframe(port)
                        if iframe_data["output"]:
                            current_output = iframe_data["output"]
                        if iframe_data["errors"]:
                            current_errors = iframe_data["errors"]
                    duration = time.time() - start_time
                    _log(f"Execution completed (CSS state) in {duration:.1f}s")
                    error_msg = None
                    if info["error"]:
                        error_msg = current_errors or current_output or "Cell execution error"
                    return {
                        "success": not info["error"],
                        "output": current_output,
                        "error": error_msg,
                        "errors": current_errors,
                        "error_flag": info["error"],
                        "duration": duration,
                        "state": "completed",
                        "detected_by": "css_state",
                    }
                settled_count += 1
            else:
                settled_count = 0

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


def _read_output_iframe(port: int = CDP_PORT) -> Dict[str, str]:
    """Read output from Colab output iframes (cross-origin sandboxed)."""
    output, errors = "", ""
    try:
        tabs = list_tabs(port)
        for tab in tabs:
            url = tab.get("url", "")
            if "outputframe" not in url or tab.get("type") != "iframe":
                continue
            ws = tab.get("webSocketDebuggerUrl")
            if not ws:
                continue
            try:
                s = CDPSession(ws, timeout=5)
                body = s.evaluate(
                    "(function(){ return document.body ? document.body.innerText.substring(0, 4000) : ''; })()"
                )
                s.close()
                if body and body.strip():
                    text = str(body).strip()
                    if "Error" in text or "Traceback" in text:
                        errors = text
                    else:
                        output = text
            except Exception:
                continue
    except Exception:
        pass
    return {"output": output, "errors": errors}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_poll_js(done_marker: str = "") -> str:
    marker_check = ""
    if done_marker:
        marker_json = json.dumps(done_marker)
        marker_check = f"var markerFound = fullText.includes({marker_json});"
    else:
        marker_check = "var markerFound = false;"

    return f"""
        (function() {{
            var cell = document.querySelector('.cell.code');
            var runBtn = cell ? cell.querySelector('colab-run-button') : document.querySelector('colab-run-button');
            var sd = runBtn && runBtn.shadowRoot ?
                runBtn.shadowRoot.querySelector('.cell-execution') : null;
            var classes = sd ? sd.className : '';
            var outEls = cell ? cell.querySelectorAll('.output_text, .output_stream') : [];
            if (outEls.length === 0) {{ outEls = cell ? cell.querySelectorAll('.output-content:not([hidden])') : []; }}
            var fullText = '';
            outEls.forEach(function(e) {{ fullText += e.textContent + '\\n'; }});
            var errEls = cell ? cell.querySelectorAll('.output_error, .ansi-red-fg, .error-in-cell') : [];
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


