"""MCP workflow for executing GDS commands via Colab browser automation.

Architecture:
    1. GDS command runs normally — opens a Tkinter GUI window (ButtonBarWindow)
       that auto-copies the remote script to the clipboard.
    2. Agent interacts with Colab in the built-in MCP browser:
       navigate → lock → create cell → paste (Cmd+V) → execute → wait for marker.
    3. After output appears, agent sends `GDS --gui-submit` to close the GUI.
    4. Normal GDS flow resumes (result download, etc.).

The GDS GUI Queue ensures multiple --mcp sessions are serialized.
If MCP browser interaction fails, the GUI window stays open so the user can
complete the task manually (the agent should fallback to USERINPUT).
"""
import json
import sys
import hashlib
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


def _command_hash(command: str) -> str:
    return hashlib.md5(command.encode()).hexdigest()[:8].upper()


def build_execute_workflow(command, as_python=False, marker=None):
    """Build a structured MCP workflow for running a command in Colab.

    Args:
        command: Shell command string to execute.
        as_python: If True, run as Python code instead of shell command.
        marker: Unique output marker for detecting completion. Auto-generated if None.

    Returns:
        dict with status, colab_url, and agent workflow steps.
    """
    colab_url = "https://colab.research.google.com/"
    cmd_hash = _command_hash(command)

    if not marker:
        import time
        marker = f"GDS_DONE_{hashlib.md5(f'{command}{time.time()}'.encode()).hexdigest()[:8]}"

    if as_python:
        cell_code = f"{command}\nprint('{marker}')"
    else:
        cell_code = f"!{command} && echo {marker} || echo {marker}"

    steps = [
        {
            "step": 1,
            "action": "run_gcs_command",
            "description": "Run the GDS command normally (opens GUI window, copies script to clipboard)",
            "shell_command": f"GDS {command}",
            "important": "Run this in a terminal. Wait for the GUI window to appear before proceeding.",
        },
        {
            "step": 2,
            "action": "open_notebook",
            "description": "Navigate to the Colab notebook",
            "mcp_tool": "browser_navigate",
            "args": {"url": colab_url},
        },
        {
            "step": 3,
            "action": "lock_browser",
            "description": "Lock browser for automation",
            "mcp_tool": "browser_lock",
            "args": {},
        },
        {
            "step": 4,
            "action": "snapshot",
            "description": "Get current page state to find cell refs",
            "mcp_tool": "browser_snapshot",
            "args": {},
        },
        {
            "step": 5,
            "action": "prepare_cell",
            "description": "Create a fresh empty cell and enter edit mode",
            "instructions": [
                "Press Escape to ensure command mode.",
                "Press Ctrl+M then B to insert a new cell below.",
                "If old cells exist, delete them: select each and press Ctrl+M then D -> D.",
                "Press Enter on the new cell to enter edit mode.",
                "Verify 'Editor content' textbox is 'active, focused' in the snapshot.",
            ],
        },
        {
            "step": 6,
            "action": "type_command",
            "description": f"Type the command into the cell",
            "mcp_tool": "browser_type",
            "args": {"ref": "find:textbox:Editor content", "text": cell_code, "slowly": True},
            "important": "CRITICAL: Use browser_type with slowly=true. "
                         "Meta+V paste does NOT work — MCP browser has isolated clipboard. "
                         "NEVER use browser_fill on Colab cells — it breaks CodeMirror.",
        },
        {
            "step": 7,
            "action": "dismiss_autocomplete",
            "description": "Press Escape to dismiss any autocomplete popup",
            "mcp_tool": "browser_press_key",
            "args": {"key": "Escape"},
        },
        {
            "step": 8,
            "action": "execute_cell",
            "description": "Execute the cell with Cmd+Enter",
            "mcp_tool": "browser_press_key",
            "args": {"key": "Meta+Enter"},
        },
        {
            "step": 9,
            "action": "wait_for_output",
            "description": f"Wait for the completion marker '{marker}' or 'Finished' text in the output",
            "mcp_tool": "browser_wait_for",
            "args": {"text": marker, "timeout": 120000},
            "note": "If the command is long-running, this may time out. "
                    "Use browser_search to check for partial output.",
        },
        {
            "step": 10,
            "action": "capture_output",
            "description": "Take a screenshot to capture the full output",
            "mcp_tool": "browser_take_screenshot",
            "args": {},
        },
        {
            "step": 11,
            "action": "unlock_browser",
            "description": "Unlock the browser",
            "mcp_tool": "browser_unlock",
            "args": {},
        },
        {
            "step": 12,
            "action": "submit_gui",
            "description": "Close the GDS GUI window via external control",
            "shell_command": "GDS --gui-submit",
            "note": "This triggers the normal GDS flow to continue (result download, etc.).",
        },
    ]

    return {
        "status": "workflow",
        "action": "execute",
        "command": command,
        "command_hash": cmd_hash,
        "cell_code": cell_code,
        "colab_url": colab_url,
        "completion_marker": marker,
        "steps": steps,
        "tips": {
            "typing": "Use browser_type with slowly=true. Meta+V paste does NOT work (isolated clipboard).",
            "cell_editing": "NEVER use browser_fill on Colab cells — it breaks CodeMirror.",
            "output_reading": "Cell output may not appear in the accessibility tree. Use browser_search or screenshot.",
            "new_cell": "Always create a fresh cell: Escape -> Ctrl+M -> B, then Enter for edit mode.",
            "stale_session": "If 'Could not load JavaScript files' error appears, use Runtime -> 'Restart session and run all'.",
            "fallback": "If MCP interaction fails, use USERINPUT to ask the user to complete the task. "
                        f"The GUI window [{cmd_hash}] stays open for manual completion.",
        },
    }


def _is_cdp_available():
    try:
        from logic.chrome.session import is_chrome_cdp_available
        return is_chrome_cdp_available()
    except Exception:
        return False


def _run_cdp_execute(command, as_python=False):
    """Execute command via CDP directly. Returns (exit_code, output_text)."""
    import time
    marker = f"GDS_DONE_{hashlib.md5(f'{command}{time.time()}'.encode()).hexdigest()[:8]}"

    if as_python:
        cell_code = f"{command}\nprint('{marker}')"
    else:
        cell_code = f"!{command} && echo {marker} || echo {marker}"

    from tool.GOOGLE.interface.main import inject_and_execute
    result = inject_and_execute(
        code=cell_code, port=9222, timeout=120,
        done_marker=marker
    )

    if result.get("success"):
        return 0, result.get("output", "")
    else:
        return 1, result.get("error", "Unknown error")


def run_mcp_execute(command, as_python=False, as_json=False):
    """Execute a GDS command via MCP/CDP automation.

    When CDP is available, executes directly with Turing Machine progress.
    Otherwise, prints workflow instructions for the agent to follow manually.

    Returns exit code: 0 = success, 1 = error
    """
    workflow = build_execute_workflow(command, as_python=as_python)

    if workflow["status"] == "error":
        if as_json:
            print(json.dumps(workflow))
        else:
            print(f"{BOLD}{RED}Failed{RESET}. {workflow['message']}")
        return 1

    if as_json:
        print(json.dumps(workflow, indent=2))
        return 0

    if _is_cdp_available():
        return _run_cdp_with_turing(command, as_python)

    cmd_hash = workflow["command_hash"]
    print(f"{BOLD}{BLUE}MCP execute{RESET}: {command}")
    print(f"  Hash:   {cmd_hash}")
    print(f"  Colab:  {workflow['colab_url']}")
    print(f"  Cell:   {workflow['cell_code']}")
    print(f"  Marker: {workflow['completion_marker']}")
    print(f"  Flow:   GDS {command} -> type in Colab -> execute -> GDS --gui-submit")
    return 0


def _load_cdmcp():
    """Try to load CDMCP overlay and interact modules. Returns (overlay, interact) or (None, None)."""
    try:
        from logic.cdmcp_loader import load_cdmcp_overlay, load_cdmcp_interact
        return load_cdmcp_overlay(), load_cdmcp_interact()
    except Exception:
        return None, None


def _apply_cdmcp_overlays(cdp, overlay):
    """Apply CDMCP overlays to Colab tab: badge, focus, lock with timer."""
    try:
        overlay.inject_badge(cdp, text="GDS [colab]", color="#0d904f")
        overlay.inject_focus(cdp, color="#0d904f")
        overlay.inject_favicon(cdp, svg_color="#0d904f", letter="G")
        overlay.inject_lock(cdp, base_opacity=0.08, flash_opacity=0.25,
                            tool_name="GDS")
        overlay.increment_mcp_count(cdp, 1)
    except Exception:
        pass


def _cleanup_cdmcp_overlays(cdp, overlay):
    """Remove CDMCP overlays after execution."""
    try:
        overlay.remove_all_overlays(cdp)
    except Exception:
        pass


def _run_cdp_with_turing(command, as_python=False):
    """Execute via CDP with Turing Machine progress display and CDMCP visual effects."""
    from interface.turing import ProgressTuringMachine, TuringStage

    _cdp_result = {}
    _cdp_session_holder = [None]
    overlay, interact = _load_cdmcp()
    mcp_count = [0]

    def _stage_connect(stage):
        if _is_cdp_available():
            return True
        stage.report_error("Chrome CDP not available.")
        return False

    def _stage_find_tab(stage):
        from logic.chrome.session import CDPSession
        from tool.GOOGLE.interface.main import find_colab_tab, _reopen_colab_tab as reopen_colab_tab
        tab = find_colab_tab()
        if not tab:
            stage.active_name = "Reopening Colab tab..."
            stage.refresh()
            tab = reopen_colab_tab()
        if not tab:
            stage.report_error("Colab tab not found and reopen failed.")
            return False

        ws = tab.get("webSocketDebuggerUrl")
        if ws:
            cdp = CDPSession(ws, timeout=15)
            _cdp_session_holder[0] = cdp
            if overlay:
                _apply_cdmcp_overlays(cdp, overlay)
                mcp_count[0] += 1
        return True

    def _stage_execute(stage):
        cdp = _cdp_session_holder[0]
        if overlay and cdp:
            cell_sel = ".cell.code"
            try:
                cell_ok = cdp.evaluate(
                    "(function(){ var c = colab.global.notebook.cells;"
                    " return (Array.isArray(c) && c.length > 0 "
                    " && typeof c[0].setText === 'function') ? 1 : 0; })()"
                )
                if not cell_ok or int(cell_ok) == 0:
                    stage.active_name = "Creating code cell..."
                    stage.refresh()
                    if interact:
                        interact.mcp_click(cdp, "#toolbar-add-code",
                                           label="+ Code (create cell)", dwell=0.8,
                                           color="#e8710a", unlock_for_click=True)
                    else:
                        cdp.evaluate("colab.global.notebook.addCell('code', {cellIndex: 0})")
                    import time as _t
                    _t.sleep(2)
                    mcp_count[0] += 1
                    stage.active_name = f"{command}..."
                    stage.refresh()

                overlay.inject_highlight(cdp, cell_sel,
                                         label=f"Injecting: {command[:30]}",
                                         color="#1a73e8")
                overlay.increment_mcp_count(cdp, 1)
                import time as _t
                _t.sleep(0.8)
                overlay.remove_highlight(cdp)
            except Exception:
                pass

        if cdp:
            try:
                cdp.close()
            except Exception:
                pass
            _cdp_session_holder[0] = None

        code, output = _run_cdp_execute(command, as_python)

        from tool.GOOGLE.interface.main import find_colab_tab as _find_tab
        _tab = _find_tab()
        if _tab and _tab.get("webSocketDebuggerUrl"):
            from logic.chrome.session import CDPSession as _CdpCls
            _cdp_session_holder[0] = _CdpCls(_tab["webSocketDebuggerUrl"], timeout=10)
            if overlay:
                try:
                    overlay.increment_mcp_count(_cdp_session_holder[0], 1)
                except Exception:
                    pass
        _cdp_result["code"] = code
        _cdp_result["output"] = output
        mcp_count[0] += 1
        if code == 0:
            return True
        out_lower = (output or "").lower()
        if "not mounted" in out_lower or "drive not mounted" in out_lower:
            stage.error_brief = "Google Drive not mounted. Run 'GDS --remount' first."
        elif "fingerprint" in out_lower and "failed" in out_lower:
            stage.error_brief = "Mount fingerprint mismatch. Run 'GDS --remount' to refresh."
        else:
            stage.error_brief = output[:200] if output else "Execution failed."
        return False

    def _stage_result(stage):
        output = _cdp_result.get("output", "")
        if output:
            stage.set_captured_output(output)
        return _cdp_result.get("code", 1) == 0

    pm = ProgressTuringMachine(project_root=str(_project_root), tool_name="GOOGLE.GDS")

    pm.add_stage(TuringStage(
        "CDP", _stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
        bold_part="Connecting to"
    ))

    pm.add_stage(TuringStage(
        "Colab tab", _stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Failed to find", fail_name="Colab notebook.",
        bold_part="Finding"
    ))

    pm.add_stage(TuringStage(
        "execute", _stage_execute,
        active_status="Executing", active_name=f"{command}...",
        success_status="Executed", success_name=f"{command}.",
        fail_status="Failed to execute", fail_name="command.",
        bold_part="Executing"
    ))

    pm.add_stage(TuringStage(
        "result", _stage_result,
        active_status="Capturing", active_name="execution result...",
        success_status="Captured", success_name="execution result.",
        fail_status="Failed to capture", fail_name="execution result.",
        bold_part="Capturing",
        is_sticky=True
    ))

    success = pm.run()

    cdp = _cdp_session_holder[0]
    if cdp and overlay:
        try:
            _cleanup_cdmcp_overlays(cdp, overlay)
        except Exception:
            pass
        try:
            cdp.close()
        except Exception:
            pass

    output = _cdp_result.get("output", "")
    if success and output:
        lines = output.strip().split('\n')
        for line in lines:
            if not line.startswith("GDS_DONE_"):
                print(f"  {line}")

    return 0 if success else 1
