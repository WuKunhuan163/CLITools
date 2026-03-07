#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.tool.blueprint.mcp import MCPToolBase
from logic.interface.config import get_color


def _get_colab_open_url() -> str:
    """Read the Colab notebook URL from GCS config for auto-open."""
    import json as _json
    for cfg_path in [
        Path(__file__).resolve().parents[2] / "data" / "config.json",
        Path(__file__).resolve().parents[1] / "GOOGLE.GCS" / "data" / "config.json",
    ]:
        if cfg_path.exists():
            try:
                with open(cfg_path) as f:
                    cfg = _json.load(f)
                url = cfg.get("root_notebook_url", "")
                if url:
                    return url
                nid = cfg.get("root_notebook_id", "")
                if nid:
                    return f"https://colab.research.google.com/drive/{nid}"
            except Exception:
                continue
    return ""


class GCTool(MCPToolBase):
    """GOOGLE.GC tool with Colab MCP state reporting."""

    def __init__(self):
        super().__init__("GOOGLE.GC", session_name="")

    def _collect_mcp_state(self, session=None, tab_label: str = ""):
        """Collect Google Colab notebook state via CDP."""
        from tool.GOOGLE.logic.chrome.session import CDPSession, is_chrome_cdp_available
        import json as _json

        state = {
            "cdp_available": False,
            "colab_tab": None,
            "cells": [],
            "cell_count": 0,
            "runtime": {"connected": False, "status": "unknown"},
            "notebook": {"title": "", "url": ""},
        }

        if not is_chrome_cdp_available():
            return state
        state["cdp_available"] = True

        tab_info = None
        sm = self.session_mgr
        if sm:
            tab_info = sm.require_tab(
                label="colab", url_pattern="colab.research.google.com",
                auto_open=False, wait_sec=0,
            )
        if not tab_info:
            from tool.GOOGLE.logic.chrome.colab import find_colab_tab
            raw = find_colab_tab()
            if raw:
                tab_info = {"id": raw["id"], "url": raw.get("url", ""),
                            "ws": raw.get("webSocketDebuggerUrl", "")}

        if not tab_info or not tab_info.get("ws"):
            return state

        state["colab_tab"] = {
            "id": tab_info.get("id", ""),
            "url": tab_info.get("url", ""),
        }

        try:
            cdp = CDPSession(tab_info["ws"], timeout=10)

            full_state = cdp.evaluate('''
                (function(){
                    var out = {cells:[], runtime:{}, notebook:{}};
                    // Notebook info
                    out.notebook.title = document.title || '';
                    out.notebook.url = window.location.href || '';

                    // Cells
                    var cells = [];
                    try {
                        cells = colab.global.notebook.cells;
                    } catch(e) {}
                    if (Array.isArray(cells)) {
                        for (var i = 0; i < cells.length; i++) {
                            var c = cells[i];
                            var text = '';
                            try { text = c.getText(); } catch(e){}
                            var type = 'unknown';
                            try { type = c.getType(); } catch(e){}
                            var focused = false;
                            try { focused = c.isFocused(); } catch(e){}
                            out.cells.push({
                                index: i,
                                type: type,
                                text: text.substring(0, 200),
                                text_length: text.length,
                                focused: focused
                            });
                        }
                    }

                    // Runtime status
                    var conn = document.querySelector('colab-connect-button');
                    if (conn) {
                        out.runtime.button_text = (conn.textContent || '').trim().substring(0, 30);
                        out.runtime.connected = out.runtime.button_text.toLowerCase().includes('connect') ?
                            !out.runtime.button_text.toLowerCase().startsWith('connect') : true;
                    }

                    // Check for running cells
                    var runningCells = document.querySelectorAll('.cell-execution.running');
                    out.runtime.running_cells = runningCells.length;
                    var pendingCells = document.querySelectorAll('.cell-execution.pending');
                    out.runtime.pending_cells = pendingCells.length;

                    return JSON.stringify(out);
                })()
            ''')

            if full_state:
                parsed = _json.loads(full_state)
                state["cells"] = parsed.get("cells", [])
                state["cell_count"] = len(state["cells"])
                state["runtime"] = parsed.get("runtime", state["runtime"])
                state["notebook"] = parsed.get("notebook", state["notebook"])

            cdp.close()
        except Exception as exc:
            state["error"] = str(exc)

        return state


def _run_cell_action(tool, args):
    """Handle 'GOOGLE.GC cell add' with Turing machine + CDMCP overlays.

    Uses CDMCP session.require_tab() for tab lifecycle management:
    if the Colab tab is missing, CDMCP auto-opens it in the session window.
    """
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.interface.config import get_color

    action = getattr(args, "cell_action", None) or "add"
    cell_text = getattr(args, "text", "") or ""
    cell_type = getattr(args, "cell_type", "code") or "code"

    _cdp = [None]
    _overlay = [None]
    _interact = [None]
    _session_mgr = [None]

    def stage_connect(stage=None):
        from tool.GOOGLE.logic.chrome.session import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            if stage:
                stage.error_brief = "Chrome CDP not available."
            return False
        try:
            from logic.cdmcp_loader import (
                load_cdmcp_overlay, load_cdmcp_interact, load_cdmcp_sessions,
            )
            _overlay[0] = load_cdmcp_overlay()
            _interact[0] = load_cdmcp_interact()
            _session_mgr[0] = load_cdmcp_sessions()
        except Exception:
            pass
        return True

    def stage_find_tab(stage=None):
        from tool.GOOGLE.logic.chrome.session import CDPSession
        sm = _session_mgr[0]

        tab_info = None
        if sm:
            tab_info = sm.require_tab(
                label="colab",
                url_pattern="colab.research.google.com",
                open_url=_get_colab_open_url(),
                auto_open=True,
                wait_sec=12.0,
            )

        if not tab_info:
            from tool.GOOGLE.logic.chrome.colab import find_colab_tab
            raw = find_colab_tab()
            if raw:
                tab_info = {"id": raw["id"], "url": raw.get("url", ""),
                            "ws": raw.get("webSocketDebuggerUrl", ""),
                            "label": "colab", "recovered": False}

        if not tab_info or not tab_info.get("ws"):
            if stage:
                stage.error_brief = "No Colab tab found."
            return False

        _cdp[0] = CDPSession(tab_info["ws"], timeout=15)
        if _overlay[0]:
            _overlay[0].inject_badge(_cdp[0], text="GC [colab]", color="#e8710a")
            _overlay[0].inject_focus(_cdp[0], color="#e8710a")
            _overlay[0].inject_lock(_cdp[0], tool_name="GC")
        return True

    def stage_add_cell(stage=None):
        import time
        cdp = _cdp[0]
        ov = _overlay[0]
        interact = _interact[0]

        is_text = cell_type == "text"
        btn_id = "#toolbar-add-text" if is_text else "#toolbar-add-code"
        btn_label = "+ Text (create cell)" if is_text else "+ Code (create cell)"
        cell_selector = ".cell.text:last-child" if is_text else ".cell.code:last-child"

        if interact:
            interact.mcp_click(
                cdp, btn_id,
                label=btn_label, dwell=1.0,
                color="#e8710a", tool_name="GC",
            )
        else:
            cdp.evaluate(
                f"(function(){{ var b = document.querySelector('{btn_id}');"
                f" if(b) b.click(); }})()"
            )
        time.sleep(1.5)

        if ov:
            ov.increment_mcp_count(cdp, 1)

        if cell_text:
            import json as _json
            cdp.evaluate(
                f"(function(){{ var c = colab.global.notebook.cells;"
                f" if(Array.isArray(c) && c.length > 0)"
                f" c[c.length-1].setText({_json.dumps(cell_text)}); }})()"
            )
            if ov:
                ov.inject_highlight(cdp, cell_selector,
                                     label=f"Set: {cell_text[:30]}", color="#1a73e8")
                time.sleep(0.8)
                ov.remove_highlight(cdp)
                ov.increment_mcp_count(cdp, 1)
        return True

    def stage_cleanup(stage=None):
        if _overlay[0] and _cdp[0]:
            _overlay[0].remove_all_overlays(_cdp[0])
        if _cdp[0]:
            _cdp[0].close()
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    _ct_label = f"{cell_type} cell"
    pm.add_stage(TuringStage(
        "add_cell", stage_add_cell,
        active_status="Creating", active_name=f"{_ct_label}...",
        success_status="Created", success_name=f"{_ct_label}.",
        fail_status="Failed to create", fail_name=f"{_ct_label}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_cell_edit(tool, args):
    """Handle 'GOOGLE.GC cell edit' — clear, type, or insert in a cell.

    Operations:
      --clear              Clear entire cell content
      --type TEXT           Append text at end with typing effect
      --clear-line N       Clear line N (0-based)
      --line N --insert T  Insert text at end of line N
      --line N --col C --insert T  Insert text at line N, column C
    """
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    cell_idx = getattr(args, "index", 0)
    do_clear = getattr(args, "clear", False)
    type_text = getattr(args, "type_text", "") or ""
    clear_line = getattr(args, "clear_line", -1)
    target_line = getattr(args, "line", -1)
    target_col = getattr(args, "col", -1)
    insert_text_val = getattr(args, "insert", "") or ""
    from_line = getattr(args, "from_line", -1)
    to_line = getattr(args, "to_line", -1)
    replace_with = getattr(args, "replace_with", "") or ""

    _cdp = [None]
    _overlay = [None]
    _interact = [None]
    _session_mgr = [None]

    def stage_connect(stage=None):
        from tool.GOOGLE.logic.chrome.session import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            if stage:
                stage.error_brief = "Chrome CDP not available."
            return False
        try:
            from logic.cdmcp_loader import (
                load_cdmcp_overlay, load_cdmcp_interact, load_cdmcp_sessions,
            )
            _overlay[0] = load_cdmcp_overlay()
            _interact[0] = load_cdmcp_interact()
            _session_mgr[0] = load_cdmcp_sessions()
        except Exception:
            pass
        return True

    def stage_find_tab(stage=None):
        from tool.GOOGLE.logic.chrome.session import CDPSession
        sm = _session_mgr[0]
        tab_info = None
        if sm:
            tab_info = sm.require_tab(
                label="colab", url_pattern="colab.research.google.com",
                open_url=_get_colab_open_url(), auto_open=True, wait_sec=12.0,
            )
        if not tab_info:
            from tool.GOOGLE.logic.chrome.colab import find_colab_tab
            raw = find_colab_tab()
            if raw:
                tab_info = {"id": raw["id"], "url": raw.get("url", ""),
                            "ws": raw.get("webSocketDebuggerUrl", ""),
                            "label": "colab", "recovered": False}
        if not tab_info or not tab_info.get("ws"):
            if stage:
                stage.error_brief = "No Colab tab found."
            return False
        _cdp[0] = CDPSession(tab_info["ws"], timeout=15)
        if _overlay[0]:
            _overlay[0].inject_badge(_cdp[0], text="GC [colab]", color="#e8710a")
            _overlay[0].inject_focus(_cdp[0], color="#e8710a")
            _overlay[0].inject_lock(_cdp[0], tool_name="GC")
        return True

    def stage_select_cell(stage=None):
        import time, json as _json
        cdp = _cdp[0]
        interact = _interact[0]
        ov = _overlay[0]

        cell_count = cdp.evaluate(
            "(function(){ var c = colab.global.notebook.cells;"
            " return (Array.isArray(c) && c.length > 0 && typeof c[0].setText === 'function') ? c.length : 0; })()"
        )
        if not cell_count or int(cell_count) <= cell_idx:
            if stage:
                stage.error_brief = f"Cell {cell_idx} not found (have {cell_count or 0} cells)."
            return False

        sel = f".cell.code:nth-child({cell_idx + 1})"
        if interact:
            interact.mcp_click(cdp, sel, label=f"Cell [{cell_idx}]",
                               dwell=0.8, color="#e8710a", tool_name="GC")
        else:
            cdp.evaluate(
                f"(function(){{ var c = colab.global.notebook.cells[{cell_idx}];"
                f" if(c) {{ c.setFocused(true); c.setEditing(true); }} }})()"
            )
        time.sleep(0.3)

        cdp.evaluate(
            f"(function(){{ var c = colab.global.notebook.cells[{cell_idx}];"
            f" if(c) {{ c.setFocused(true); c.setEditing(true); }} }})()"
        )
        if ov:
            ov.increment_mcp_count(cdp, 1)
        return True

    def stage_edit_cell(stage=None):
        import time, json as _json
        cdp = _cdp[0]
        ov = _overlay[0]
        interact = _interact[0]
        idx = cell_idx

        if do_clear:
            if ov:
                ov.inject_highlight(cdp, f".cell.code:nth-child({idx + 1})",
                                     label="Clearing cell...", color="#ea4335")
                time.sleep(0.5)
            cdp.evaluate(f"colab.global.notebook.cells[{idx}].setText('')")
            if ov:
                time.sleep(0.3)
                ov.remove_highlight(cdp)
                ov.increment_mcp_count(cdp, 1)

        if type_text:
            cdp.evaluate(
                f"(function(){{ var e = colab.global.notebook.cells[{idx}].getEditor();"
                f" if(e) e.moveToEndOfLastLine(); }})()"
            )
            time.sleep(0.2)

            if ov:
                preview = type_text[:30] + ("..." if len(type_text) > 30 else "")
                ov.inject_highlight(cdp, f".cell.code:nth-child({idx + 1})",
                                     label=f"Typing: {preview}", color="#1a73e8")

            if ov:
                ov.set_lock_passthrough(cdp, True)

            from logic.chrome.session import insert_text as _insert_text, dispatch_key as _dispatch_key
            char_delay = max(0.01, min(0.04, 2.0 / max(len(type_text), 1)))
            for ch in type_text:
                if ch == "\n":
                    _dispatch_key(cdp, "Enter")
                else:
                    _insert_text(cdp, ch)
                time.sleep(char_delay)

            if ov:
                ov.set_lock_passthrough(cdp, False)
                time.sleep(0.3)
                ov.remove_highlight(cdp)
                ov.increment_mcp_count(cdp, 1)

        if clear_line >= 0:
            current = cdp.evaluate(f"colab.global.notebook.cells[{idx}].getText()")
            if current:
                lines = current.split("\n")
                if clear_line < len(lines):
                    line_sel = f".cell.code:nth-child({idx + 1}) .view-line:nth-child({clear_line + 1})"
                    if ov:
                        ov.inject_highlight(cdp, line_sel,
                                             label=f"Clearing line {clear_line}",
                                             color="#ea4335")
                        time.sleep(1.0)
                    lines[clear_line] = ""
                    new_text = "\n".join(lines)
                    cdp.evaluate(
                        f"colab.global.notebook.cells[{idx}].setText({_json.dumps(new_text)})"
                    )
                    if ov:
                        time.sleep(0.5)
                        ov.remove_highlight(cdp)
                        ov.increment_mcp_count(cdp, 1)

        if target_line >= 0 and insert_text_val:
            current = cdp.evaluate(f"colab.global.notebook.cells[{idx}].getText()")
            if current is not None:
                lines = current.split("\n")
                while len(lines) <= target_line:
                    lines.append("")

                line_content = lines[target_line]
                col = target_col if target_col >= 0 else len(line_content)
                col = min(col, len(line_content))
                lines[target_line] = line_content[:col] + insert_text_val + line_content[col:]

                line_sel = f".cell.code:nth-child({idx + 1}) .view-line:nth-child({target_line + 1})"
                if ov:
                    preview = insert_text_val[:25]
                    ov.inject_highlight(
                        cdp, line_sel,
                        label=f"Insert L{target_line}:{col} '{preview}'",
                        color="#1a73e8",
                    )
                    time.sleep(1.0)

                new_text = "\n".join(lines)
                cdp.evaluate(
                    f"colab.global.notebook.cells[{idx}].setText({_json.dumps(new_text)})"
                )
                if ov:
                    time.sleep(0.5)
                    ov.remove_highlight(cdp)
                    ov.increment_mcp_count(cdp, 1)

        if from_line >= 0 and to_line >= from_line and replace_with:
            current = cdp.evaluate(f"colab.global.notebook.cells[{idx}].getText()")
            if current is not None:
                lines = current.split("\n")
                end = min(to_line + 1, len(lines))
                processed = replace_with.replace("\\\\n", "\x00").replace("\\n", "\n").replace("\x00", "\\n")
                new_lines = processed.split("\n")

                total_chars = sum(len(l) for l in new_lines)
                # Adaptive: more content = faster typing effect
                char_delay = max(0.005, min(0.04, 2.0 / max(total_chars, 1)))

                if ov:
                    for li in range(from_line, end):
                        if li < len(lines):
                            sel = f".cell.code:nth-child({idx + 1}) .view-line:nth-child({li + 1})"
                            ov.inject_highlight(cdp, sel,
                                                 label=f"Replace L{li}",
                                                 color="#ea4335")
                            time.sleep(0.4)
                            ov.remove_highlight(cdp)

                lines[from_line:end] = new_lines
                cdp.evaluate(
                    f"colab.global.notebook.cells[{idx}].setText({_json.dumps(chr(10).join(lines))})"
                )

                if ov:
                    time.sleep(0.5)
                    for ni in range(len(new_lines)):
                        li = from_line + ni
                        sel = f".cell.code:nth-child({idx + 1}) .view-line:nth-child({li + 1})"
                        preview = new_lines[ni][:30]
                        ov.inject_highlight(cdp, sel,
                                             label=f"New L{li}: {preview}",
                                             color="#34a853")
                        time.sleep(0.6)
                        ov.remove_highlight(cdp)
                    ov.increment_mcp_count(cdp, 1)

        final_text = cdp.evaluate(f"colab.global.notebook.cells[{idx}].getText()")
        if final_text is not None and ov:
            line_count = len(final_text.split("\n"))
            ov.inject_highlight(cdp, f".cell.code:nth-child({idx + 1})",
                                 label=f"Done ({line_count} lines)",
                                 color="#34a853")
            time.sleep(0.6)
            ov.remove_highlight(cdp)
        return True

    def stage_cleanup(stage=None):
        if _overlay[0] and _cdp[0]:
            _overlay[0].remove_all_overlays(_cdp[0])
        if _cdp[0]:
            _cdp[0].close()
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "select_cell", stage_select_cell,
        active_status="Selecting", active_name=f"cell [{cell_idx}]...",
        success_status="Selected", success_name=f"cell [{cell_idx}].",
        fail_status="Failed to select", fail_name=f"cell [{cell_idx}].",
    ))
    pm.add_stage(TuringStage(
        "edit_cell", stage_edit_cell,
        active_status="Editing", active_name=f"cell [{cell_idx}]...",
        success_status="Edited", success_name=f"cell [{cell_idx}].",
        fail_status="Failed to edit", fail_name=f"cell [{cell_idx}].",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_cell_execute(tool, args):
    """Handle 'GOOGLE.GC cell run' — click the run button and wait for completion."""
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    cell_idx = getattr(args, "index", 0)
    max_wait = getattr(args, "wait", 120)

    _cdp = [None]
    _overlay = [None]
    _interact = [None]
    _session_mgr = [None]
    _output = [""]

    def stage_connect(stage=None):
        from tool.GOOGLE.logic.chrome.session import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            if stage:
                stage.error_brief = "Chrome CDP not available."
            return False
        try:
            from logic.cdmcp_loader import (
                load_cdmcp_overlay, load_cdmcp_interact, load_cdmcp_sessions,
            )
            _overlay[0] = load_cdmcp_overlay()
            _interact[0] = load_cdmcp_interact()
            _session_mgr[0] = load_cdmcp_sessions()
        except Exception:
            pass
        return True

    def stage_find_tab(stage=None):
        from tool.GOOGLE.logic.chrome.session import CDPSession
        sm = _session_mgr[0]
        tab_info = None
        if sm:
            tab_info = sm.require_tab(
                label="colab", url_pattern="colab.research.google.com",
                open_url=_get_colab_open_url(), auto_open=True, wait_sec=12.0,
            )
        if not tab_info:
            from tool.GOOGLE.logic.chrome.colab import find_colab_tab
            raw = find_colab_tab()
            if raw:
                tab_info = {"id": raw["id"], "url": raw.get("url", ""),
                            "ws": raw.get("webSocketDebuggerUrl", ""),
                            "label": "colab", "recovered": False}
        if not tab_info or not tab_info.get("ws"):
            if stage:
                stage.error_brief = "No Colab tab found."
            return False
        _cdp[0] = CDPSession(tab_info["ws"], timeout=15)
        if _overlay[0]:
            _overlay[0].inject_badge(_cdp[0], text="GC [colab]", color="#e8710a")
            _overlay[0].inject_focus(_cdp[0], color="#e8710a")
            _overlay[0].inject_lock(_cdp[0], tool_name="GC")
        return True

    def stage_run_cell(stage=None):
        import time
        cdp = _cdp[0]
        interact = _interact[0]
        ov = _overlay[0]

        cell_count = cdp.evaluate(
            "(function(){ var c = colab.global.notebook.cells;"
            " return (Array.isArray(c) && c.length > 0) ? c.length : 0; })()"
        )
        if not cell_count or int(cell_count) <= cell_idx:
            if stage:
                stage.error_brief = f"Cell {cell_idx} not found (have {cell_count or 0} cells)."
            return False

        run_sel = f".cell.code:nth-child({cell_idx + 1}) colab-run-button"
        if interact:
            interact.mcp_click(cdp, run_sel, label=f"Run cell [{cell_idx}]",
                               dwell=1.0, color="#34a853", tool_name="GC")
        else:
            cdp.evaluate(
                f"(function(){{ var c = document.querySelectorAll('.cell.code')[{cell_idx}];"
                f" if(c) {{ var b = c.querySelector('colab-run-button'); if(b) b.click(); }} }})()"
            )
        if ov:
            ov.increment_mcp_count(cdp, 1)
        return True

    def stage_wait_complete(stage=None):
        import time
        cdp = _cdp[0]
        ov = _overlay[0]

        poll_js = f"""(function(){{
            var cells = document.querySelectorAll('.cell.code');
            if (cells.length <= {cell_idx}) return 'no_cell';
            var cell = cells[{cell_idx}];
            var rb = cell.querySelector('colab-run-button');
            var sd = rb && rb.shadowRoot ? rb.shadowRoot.querySelector('.cell-execution') : null;
            var cls = sd ? sd.className : '';
            var outEls = cell.querySelectorAll('.output_text, .output_stream');
            var text = '';
            outEls.forEach(function(e){{ text += e.textContent; }});
            var errEls = cell.querySelectorAll('.output_error, .ansi-red-fg');
            var errText = '';
            errEls.forEach(function(e){{ errText += e.textContent; }});
            return JSON.stringify({{
                running: cls.includes('running'),
                pending: cls.includes('pending'),
                error: cls.includes('error'),
                output: text.substring(0, 2000),
                errors: errText.substring(0, 1000)
            }});
        }})()"""

        import time as _time
        for i in range(max_wait // 2):
            _time.sleep(2)
            result = cdp.evaluate(poll_js)
            if not result or result == "no_cell":
                continue
            try:
                import json as _json
                info = _json.loads(result)
            except Exception:
                continue

            if not info.get("running") and not info.get("pending"):
                _output[0] = info.get("output", "")
                if info.get("error"):
                    if stage:
                        err = info.get("errors", "")[:80]
                        stage.error_brief = f"Cell error: {err}"
                    return False
                return True

        if stage:
            stage.error_brief = f"Timed out after {max_wait}s."
        return False

    def stage_cleanup(stage=None):
        if _overlay[0] and _cdp[0]:
            _overlay[0].remove_all_overlays(_cdp[0])
        if _cdp[0]:
            _cdp[0].close()
        if _output[0]:
            print(_output[0].strip())
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "run_cell", stage_run_cell,
        active_status="Running", active_name=f"cell [{cell_idx}]...",
        success_status="Started", success_name=f"cell [{cell_idx}].",
        fail_status="Failed to run", fail_name=f"cell [{cell_idx}].",
    ))
    pm.add_stage(TuringStage(
        "wait_complete", stage_wait_complete,
        active_status="Waiting for", active_name=f"cell [{cell_idx}] completion...",
        success_status="Completed", success_name=f"cell [{cell_idx}].",
        fail_status="Failed:", fail_name=f"cell [{cell_idx}] execution.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _colab_connect_stages():
    """Return shared (state_dict, connect_fn, find_tab_fn) for Colab Turing machines."""
    ctx = {"cdp": None, "overlay": None, "interact": None, "session_mgr": None}

    def stage_connect(stage=None):
        from tool.GOOGLE.logic.chrome.session import is_chrome_cdp_available
        if not is_chrome_cdp_available():
            if stage:
                stage.error_brief = "Chrome CDP not available."
            return False
        try:
            from logic.cdmcp_loader import (
                load_cdmcp_overlay, load_cdmcp_interact, load_cdmcp_sessions,
            )
            ctx["overlay"] = load_cdmcp_overlay()
            ctx["interact"] = load_cdmcp_interact()
            ctx["session_mgr"] = load_cdmcp_sessions()
        except Exception:
            pass
        return True

    def stage_find_tab(stage=None):
        from tool.GOOGLE.logic.chrome.session import CDPSession
        sm = ctx["session_mgr"]
        tab_info = None
        if sm:
            tab_info = sm.require_tab(
                label="colab", url_pattern="colab.research.google.com",
                open_url=_get_colab_open_url(), auto_open=True, wait_sec=12.0,
            )
        if not tab_info:
            from tool.GOOGLE.logic.chrome.colab import find_colab_tab
            raw = find_colab_tab()
            if raw:
                tab_info = {"id": raw["id"], "url": raw.get("url", ""),
                            "ws": raw.get("webSocketDebuggerUrl", ""),
                            "label": "colab", "recovered": False}
        if not tab_info or not tab_info.get("ws"):
            if stage:
                stage.error_brief = "No Colab tab found."
            return False
        ctx["cdp"] = CDPSession(tab_info["ws"], timeout=15)
        if ctx["overlay"]:
            ctx["overlay"].inject_badge(ctx["cdp"], text="GC [colab]", color="#e8710a")
            ctx["overlay"].inject_focus(ctx["cdp"], color="#e8710a")
            ctx["overlay"].inject_lock(ctx["cdp"], tool_name="GC")
        return True

    def stage_cleanup(stage=None):
        if ctx["overlay"] and ctx["cdp"]:
            ctx["overlay"].remove_all_overlays(ctx["cdp"])
        if ctx["cdp"]:
            ctx["cdp"].close()
        return True

    return ctx, stage_connect, stage_find_tab, stage_cleanup


def _run_cell_delete(tool, args):
    """Handle 'GOOGLE.GC cell delete --index N'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    cell_idx = getattr(args, "index", -1)
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_delete(stage=None):
        cdp = ctx["cdp"]
        ov = ctx["overlay"]
        interact = ctx["interact"]

        cell_count = cdp.evaluate(
            "(function(){ var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0; })()"
        )
        total = int(cell_count or 0)
        idx = cell_idx if cell_idx >= 0 else max(total - 1, 0)
        if total == 0 or idx >= total:
            if stage:
                stage.error_brief = f"Cell {idx} not found ({total} cells)."
            return False

        sel = f".cell:nth-child({idx + 1})"
        if ov:
            ov.inject_highlight(cdp, sel, label=f"Delete cell [{idx}]", color="#ea4335")
            time.sleep(0.8)

        cdp.evaluate(
            f"(function(){{ var nb = colab.global.notebook; var c = nb.cells;"
            f" if(Array.isArray(c) && c.length > {idx}) nb.removeCells([c[{idx}]]); }})()"
        )
        if ov:
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)
        time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    _del_label = f"cell [{cell_idx}]" if cell_idx >= 0 else "last cell"
    pm.add_stage(TuringStage(
        "delete_cell", stage_delete,
        active_status="Deleting", active_name=f"{_del_label}...",
        success_status="Deleted", success_name=f"{_del_label}.",
        fail_status="Failed to delete", fail_name=f"{_del_label}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_cell_move(tool, args):
    """Handle 'GOOGLE.GC cell move --index N --direction up/down'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    cell_idx = getattr(args, "index", 0)
    direction = getattr(args, "direction", "up")
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_move(stage=None):
        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        cell_count = cdp.evaluate(
            "(function(){ var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0; })()"
        )
        total = int(cell_count or 0)
        if total == 0 or cell_idx >= total:
            if stage:
                stage.error_brief = f"Cell {cell_idx} not found ({total} cells)."
            return False

        new_idx = cell_idx - 1 if direction == "up" else cell_idx + 1
        if new_idx < 0 or new_idx >= total:
            if stage:
                stage.error_brief = f"Cannot move cell {cell_idx} {direction} (bounds)."
            return False

        sel = f".cell:nth-child({cell_idx + 1})"
        if ov:
            arrow = "^" if direction == "up" else "v"
            ov.inject_highlight(cdp, sel,
                                label=f"Move [{cell_idx}] {arrow}", color="#fbbc04")
            time.sleep(0.8)

        delta = -1 if direction == "up" else 1
        cdp.evaluate(
            f"(function(){{ var nb = colab.global.notebook;"
            f" var c = nb.cells;"
            f" if(Array.isArray(c) && c.length > {cell_idx})"
            f" nb.moveCell([c[{cell_idx}]], {delta}, 0); }})()"
        )
        if ov:
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)
        time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "move_cell", stage_move,
        active_status="Moving", active_name=f"cell [{cell_idx}] {direction}...",
        success_status="Moved", success_name=f"cell [{cell_idx}] {direction}.",
        fail_status="Failed to move", fail_name=f"cell [{cell_idx}] {direction}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_runtime_action(tool, args):
    """Handle 'GOOGLE.GC runtime <action>' — run-all, interrupt, restart."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    action = getattr(args, "rt_action", None) or "run-all"
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    _action_map = {
        "run-all": {"text": "Run all", "label": "Run all cells", "color": "#34a853"},
        "interrupt": {"text": "Interrupt execution", "label": "Interrupt execution", "color": "#ea4335"},
        "restart": {"text": "Restart session", "label": "Restart session", "color": "#fbbc04"},
    }
    info = _action_map.get(action, _action_map["run-all"])

    def stage_execute(stage=None):
        cdp = ctx["cdp"]
        interact = ctx["interact"]
        ov = ctx["overlay"]

        if interact:
            interact.mcp_click(
                cdp, "#runtime-menu-button",
                label="Runtime menu", dwell=0.5,
                color=info["color"], tool_name="GC",
            )
        else:
            cdp.evaluate(
                "(function(){ var rm = document.getElementById('runtime-menu-button');"
                " if(rm) rm.click(); })()"
            )
        time.sleep(0.8)

        menu_text = info["text"]
        click_js = (
            f"(function(){{ var items = document.querySelectorAll('[role=menuitem]');"
            f" for(var i=0; i<items.length; i++){{"
            f"   if(items[i].textContent.trim().startsWith('{menu_text}'))"
            f"     {{ items[i].click(); return 'clicked'; }}"
            f" }} return 'not_found'; }})()"
        )
        result = cdp.evaluate(click_js)
        if result != "clicked":
            cdp.evaluate("document.body.click()")
            if stage:
                stage.error_brief = f"Menu item '{menu_text}' not found."
            return False

        if ov:
            ov.increment_mcp_count(cdp, 1)
        time.sleep(1.5)

        if action == "restart":
            cdp.evaluate(
                "(function(){ var ok = document.querySelector('[data-id=ok]');"
                " if(ok) ok.click(); })()"
            )
            time.sleep(1)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "execute", stage_execute,
        active_status="Executing", active_name=f"{info['label']}...",
        success_status="Executed", success_name=f"{info['label']}.",
        fail_status="Failed:", fail_name=f"{info['label']}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_notebook_action(tool, args):
    """Handle 'GOOGLE.GC notebook <action>' — save, clear-outputs."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    action = getattr(args, "nb_action", None) or "save"
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    _action_map = {
        "save": {"label": "Save notebook", "color": "#1a73e8"},
        "clear-outputs": {"label": "Clear all outputs", "color": "#e8710a",
                          "menu": "edit-menu-button", "text": "Clear all outputs"},
    }
    info = _action_map.get(action, _action_map["save"])

    def stage_execute(stage=None):
        cdp = ctx["cdp"]
        interact = ctx["interact"]
        ov = ctx["overlay"]

        if action == "save":
            cdp.evaluate(
                "(function(){"
                " document.dispatchEvent(new KeyboardEvent('keydown',"
                " {key:'s',code:'KeyS',ctrlKey:true,metaKey:true,bubbles:true}));"
                "})()"
            )
        else:
            menu_btn = info.get("menu", "edit-menu-button")
            menu_text = info.get("text", "")
            if interact:
                interact.mcp_click(
                    cdp, f"#{menu_btn}",
                    label="Edit menu", dwell=0.5,
                    color=info["color"], tool_name="GC",
                )
            else:
                cdp.evaluate(
                    f"(function(){{ var m = document.getElementById('{menu_btn}');"
                    f" if(m) m.click(); }})()"
                )
            time.sleep(0.8)
            cdp.evaluate(
                f"(function(){{ var items = document.querySelectorAll('[role=menuitem]');"
                f" for(var i=0;i<items.length;i++){{"
                f"   if(items[i].textContent.trim().startsWith('{menu_text}'))"
                f"     {{ items[i].click(); return; }}"
                f" }} }})()"
            )
            time.sleep(0.8)

        if ov:
            ov.inject_highlight(cdp, "body", label=info["label"], color=info["color"])
            time.sleep(0.6)
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "execute", stage_execute,
        active_status="Executing", active_name=f"{info['label']}...",
        success_status="Completed", success_name=f"{info['label']}.",
        fail_status="Failed:", fail_name=f"{info['label']}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


_CELL_TOOLBAR_BUTTONS = {
    "move-up": {
        "id": "button-move-cell-up", "label": "Move cell up", "icon": "arrow_upward",
        "api_fn": "(function(){{ var nb = colab.global.notebook; var c = nb.cells;"
                  " if(Array.isArray(c) && c.length > {idx}) nb.moveCell([c[{idx}]], -1, 0);"
                  " return 'ok'; }})()",
    },
    "move-down": {
        "id": "button-move-cell-down", "label": "Move cell down", "icon": "arrow_downward",
        "api_fn": "(function(){{ var nb = colab.global.notebook; var c = nb.cells;"
                  " if(Array.isArray(c) && c.length > {idx}) nb.moveCell([c[{idx}]], 1, 0);"
                  " return 'ok'; }})()",
    },
    "delete": {
        "id": "button-delete-cell-or-selection", "label": "Delete cell", "icon": "delete",
        "api_fn": "(function(){{ var nb = colab.global.notebook; var c = nb.cells;"
                  " if(Array.isArray(c) && c.length > {idx}) nb.removeCells([c[{idx}]]);"
                  " return 'ok'; }})()",
    },
    "edit": {"id": "button-toggle-edit-markdown", "label": "Edit cell", "icon": "edit"},
    "more": {"id": "button-more-actions", "label": "More actions", "icon": "more_vert"},
}

_CELL_MORE_MENU_ITEMS = {
    "select": {"text": "Select cell", "label": "Select cell"},
    "copy-link": {"text": "Copy link to cell", "label": "Copy link to cell"},
    "cut": {"text": "Cut cell", "label": "Cut cell"},
    "copy": {"text": "Copy cell", "label": "Copy cell"},
    "comment": {"text": "Add a comment", "label": "Add comment"},
    "editor-settings": {"text": "Open editor settings", "label": "Editor settings"},
    "mirror": {"text": "Mirror cell in tab", "label": "Mirror in tab"},
    "scratch": {"text": "Copy to scratch cell", "label": "Copy to scratch"},
    "form": {"text": "Add a form", "label": "Add form"},
}

_TOP_MENU_BUTTONS = {
    "file": {"id": "file-menu-button", "label": "File menu"},
    "edit": {"id": "edit-menu-button", "label": "Edit menu"},
    "view": {"id": "view-menu-button", "label": "View menu"},
    "insert": {"id": "insert-menu-button", "label": "Insert menu"},
    "runtime": {"id": "runtime-menu-button", "label": "Runtime menu"},
    "tools": {"id": "tools-menu-button", "label": "Tools menu"},
    "help": {"id": "help-menu-button", "label": "Help menu"},
}

_TOOLBAR_BUTTONS = {
    "commands": {"selector": "#toolbar-show-command-palette", "label": "Command palette"},
    "add-code": {"selector": "#toolbar-add-code", "label": "Add Code cell"},
    "add-text": {"selector": "#toolbar-add-text", "label": "Add Text cell"},
    "run-all": {
        "selector": "colab-notebook-toolbar-run-button",
        "shadow_id": "toolbar-run-button",
        "label": "Run all cells",
    },
    "run-dropdown": {
        "selector": "colab-notebook-toolbar-run-button",
        "shadow_id": "toolbar-run-button-more-actions",
        "label": "Run options dropdown",
    },
    "connect": {
        "selector": "colab-connect-button",
        "shadow_id": "connect-icon",
        "label": "Connect/Reconnect",
    },
    "settings": {"selector": "#settings-cog", "label": "Settings"},
    "comments": {"selector": "#comments", "label": "Comments"},
    "toggle-header": {"selector": "#toggle-header-button", "label": "Toggle header"},
}

_BOTTOM_BAR_BUTTONS = {
    "variables": {"text": "Variables", "label": "Variables panel"},
    "terminal": {"text": "Terminal", "label": "Terminal panel"},
}

_SIDEBAR_BUTTONS = {
    "toc": {"aria": "Table of contents", "label": "Table of contents"},
    "find": {"aria": "Find and replace", "label": "Find and replace"},
    "snippets": {"aria": "Code snippets", "label": "Code snippets"},
    "inspector": {"aria": "Data inspector", "label": "Data inspector"},
    "secrets": {"aria": "Secrets", "label": "Secrets"},
    "files": {"aria": "Files", "label": "Files"},
    "data-explorer": {"aria": "Data explorer", "label": "Data explorer"},
}


def _focus_and_hover_cell(cdp, cell_idx: int):
    """Focus a Colab cell and hover to trigger its toolbar.

    Colab lazily creates the toolbar (colab-cell-toolbar inside shadow DOM)
    only for the currently focused cell.  This function:
      1. Defocuses all cells via API
      2. Focuses the target cell via API + real click on the left margin
         (left-margin click puts the cell in *command* mode, not edit mode)
      3. Hovers to make the toolbar visible

    Returns True if the toolbar appeared on the target cell.
    """
    import time, json as _json
    from logic.chrome.session import real_click

    cdp.evaluate(
        f"(function(){{ var c = colab.global.notebook.cells;"
        f" for(var i=0;i<c.length;i++) c[i].setFocused(false);"
        f" if(c.length > {cell_idx}) c[{cell_idx}].setFocused(true); }})()"
    )
    time.sleep(0.3)

    box_js = (
        f"(function(){{ var el = document.querySelectorAll('.cell')[{cell_idx}];"
        f" if(!el) return null;"
        f" el.scrollIntoView({{block:'center'}});"
        f" var r = el.getBoundingClientRect();"
        f" return JSON.stringify({{x: r.x + 20, y: r.y + r.height/2}}); }})()"
    )
    box = cdp.evaluate(box_js)
    if not box:
        return False
    coords = _json.loads(box)
    real_click(cdp, int(coords["x"]), int(coords["y"]))
    time.sleep(0.5)

    hover_js = (
        f"(function(){{ var el = document.querySelectorAll('.cell')[{cell_idx}];"
        f" if(!el) return null;"
        f" var r = el.getBoundingClientRect();"
        f" return JSON.stringify({{x: r.x + r.width/2, y: r.y + 10}}); }})()"
    )
    hover_box = cdp.evaluate(hover_js)
    if hover_box:
        hcoords = _json.loads(hover_box)
        cdp.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": int(hcoords["x"]),
            "y": int(hcoords["y"]),
        }, timeout=5)
    time.sleep(1.0)

    has_toolbar = cdp.evaluate(
        f"(function(){{ var el = document.querySelectorAll('.cell')[{cell_idx}];"
        f" if(!el) return false;"
        f" var ct = el.querySelector('.cell-toolbar colab-cell-toolbar');"
        f" return !!(ct && ct.shadowRoot); }})()"
    )
    return str(has_toolbar).lower() == "true"


def _click_cell_toolbar_button(cdp, button_id: str, cell_idx: int = -1):
    """Click a button in the focused cell's toolbar shadow DOM.

    Colab only creates colab-cell-toolbar for the currently focused cell.
    _focus_and_hover_cell() must be called first.

    When cell_idx >= 0, verifies the focused cell matches before clicking.
    Returns 'clicked', 'no_cell', 'no_toolbar', or 'no_button'.
    """
    idx_check = f"cells.length <= {cell_idx}" if cell_idx >= 0 else "false"
    target = (
        f"cells[{cell_idx}]" if cell_idx >= 0
        else "document.querySelector('.cell.focused') || cells[0]"
    )
    sel = (
        f"(function(){{ var cells = document.querySelectorAll('.cell');"
        f" if({idx_check}) return 'no_cell';"
        f" var cell = {target};"
        f" var tb = cell.querySelector('.cell-toolbar colab-cell-toolbar');"
        f" if(!tb || !tb.shadowRoot) return 'no_toolbar';"
        f" var btn = tb.shadowRoot.querySelector('#{button_id}');"
        f" if(!btn) return 'no_button';"
        f" btn.click(); return 'clicked'; }})()"
    )
    return cdp.evaluate(sel)


def _click_cell_more_menu_item(cdp, menu_text: str, cell_idx: int = -1):
    """Open the 'More actions' menu on the focused cell and click a menu item by text.

    Uses real_click (CDP mouse events) because Colab's Closure Library
    menu items don't respond to element.click().
    Returns 'clicked', 'no_toolbar', 'no_menu', or 'no_item'.
    """
    import time as _time, json as _json
    from logic.chrome.session import real_click

    result = _click_cell_toolbar_button(cdp, "button-more-actions", cell_idx)
    if result != "clicked":
        return result
    _time.sleep(1.0)

    coords_js = (
        f"(function(){{ var items = document.querySelectorAll('[role=menuitem]');"
        f" for(var i=0; i<items.length; i++){{"
        f"   var r = items[i].getBoundingClientRect();"
        f"   if(r.width > 0 && items[i].textContent.trim() === '{menu_text}')"
        f"     return JSON.stringify({{x: r.x + r.width/2, y: r.y + r.height/2}});"
        f" }} return ''; }})()"
    )
    coords_raw = cdp.evaluate(coords_js)
    if not coords_raw:
        cdp.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "Escape", "code": "Escape"
        }, timeout=5)
        cdp.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "Escape", "code": "Escape"
        }, timeout=5)
        return "no_item"

    coords = _json.loads(coords_raw)
    real_click(cdp, int(coords["x"]), int(coords["y"]))
    _time.sleep(0.5)
    return "clicked"


def _run_cell_focus(tool, args):
    """Handle 'GOOGLE.GC cell focus --index N [--toolbar-click BUTTON] [--menu-click ITEM]'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    cell_idx = getattr(args, "index", 0)
    tb_click = getattr(args, "toolbar_click", "")
    menu_click = getattr(args, "menu_click", "")
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_focus(stage=None):
        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        cell_count = cdp.evaluate(
            "(function(){ var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0; })()"
        )
        total = int(cell_count or 0)
        if total == 0 or cell_idx >= total:
            if stage:
                stage.error_brief = f"Cell {cell_idx} not found ({total} cells)."
            return False

        sel = f".cell:nth-child({cell_idx + 1})"
        if ov:
            ov.inject_highlight(cdp, sel, label=f"Focus cell [{cell_idx}]", color="#1a73e8")
            time.sleep(0.8)

        ok = _focus_and_hover_cell(cdp, cell_idx)
        if ov:
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)

        if not ok:
            if stage:
                stage.error_brief = f"Failed to focus cell {cell_idx} (toolbar not found)."
            return False
        return True

    def stage_toolbar_click(stage=None):
        if not tb_click:
            return True

        import time as _time
        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        btn_info = _CELL_TOOLBAR_BUTTONS.get(tb_click)
        if not btn_info:
            if stage:
                avail = ", ".join(_CELL_TOOLBAR_BUTTONS.keys())
                stage.error_brief = f"Unknown button '{tb_click}'. Available: {avail}"
            return False

        api_fn = btn_info.get("api_fn")
        if api_fn:
            result = cdp.evaluate(api_fn.format(idx=cell_idx))
            if ov:
                ov.increment_mcp_count(cdp, 1)
            _time.sleep(0.5)
            return True

        result = _click_cell_toolbar_button(cdp, btn_info["id"], cell_idx=cell_idx)
        if result != "clicked":
            if stage:
                stage.error_brief = f"Button '{tb_click}' not found ({result})."
            return False

        if ov:
            ov.increment_mcp_count(cdp, 1)
        _time.sleep(0.5)
        return True

    def stage_menu_click(stage=None):
        if not menu_click:
            return True

        import time as _time
        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        item_info = _CELL_MORE_MENU_ITEMS.get(menu_click)
        if not item_info:
            if stage:
                avail = ", ".join(_CELL_MORE_MENU_ITEMS.keys())
                stage.error_brief = f"Unknown menu item '{menu_click}'. Available: {avail}"
            return False

        result = _click_cell_more_menu_item(cdp, item_info["text"], cell_idx=cell_idx)
        if result != "clicked":
            if stage:
                stage.error_brief = f"Menu item '{menu_click}' failed ({result})."
            return False

        if ov:
            ov.increment_mcp_count(cdp, 1)
        _time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "focus", stage_focus,
        active_status="Focusing on", active_name=f"cell [{cell_idx}]...",
        success_status="Focused on", success_name=f"cell [{cell_idx}].",
        fail_status="Failed to focus on", fail_name=f"cell [{cell_idx}].",
    ))
    if tb_click:
        btn_label = _CELL_TOOLBAR_BUTTONS.get(tb_click, {}).get("label", tb_click)
        pm.add_stage(TuringStage(
            "toolbar_click", stage_toolbar_click,
            active_status="Clicking", active_name=f"{btn_label}...",
            success_status="Clicked", success_name=f"{btn_label}.",
            fail_status="Failed to click", fail_name=f"{btn_label}.",
        ))
    if menu_click:
        menu_label = _CELL_MORE_MENU_ITEMS.get(menu_click, {}).get("label", menu_click)
        pm.add_stage(TuringStage(
            "menu_click", stage_menu_click,
            active_status="Clicking menu:", active_name=f"{menu_label}...",
            success_status="Clicked menu:", success_name=f"{menu_label}.",
            fail_status="Failed to click menu:", fail_name=f"{menu_label}.",
        ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_toolbar_action(tool, args):
    """Handle 'GOOGLE.GC toolbar <button>'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    button_name = getattr(args, "button", "")
    btn_info = _TOOLBAR_BUTTONS.get(button_name, {})
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_click_toolbar(stage=None):
        cdp = ctx["cdp"]
        interact = ctx["interact"]
        ov = ctx["overlay"]

        shadow_id = btn_info.get("shadow_id")
        sel = btn_info.get("selector", "")

        if shadow_id:
            coords_js = (
                f"(function(){{ var host = document.querySelector('{sel}');"
                f" if(!host || !host.shadowRoot) return '';"
                f" var btn = host.shadowRoot.querySelector('#{shadow_id}');"
                f" if(!btn) return '';"
                f" var r = btn.getBoundingClientRect();"
                f" return JSON.stringify({{x: r.x + r.width/2, y: r.y + r.height/2}}); }})()"
            )
            coords_raw = cdp.evaluate(coords_js)
            if not coords_raw:
                if stage:
                    stage.error_brief = f"Button '{button_name}' not found in shadow DOM."
                return False
            import json as _json
            from logic.chrome.session import real_click
            coords = _json.loads(coords_raw)
            if ov:
                ov.inject_highlight(cdp, sel, label=btn_info["label"], color="#1a73e8")
                time.sleep(0.8)
            real_click(cdp, int(coords["x"]), int(coords["y"]))
        else:
            if interact:
                interact.mcp_click(
                    cdp, sel, label=btn_info["label"],
                    dwell=1.0, color="#1a73e8", tool_name="GC",
                )
            else:
                cdp.evaluate(f"document.querySelector('{sel}').click()")

        if ov:
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)
        time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage("connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage("find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage("click", stage_click_toolbar,
        active_status="Clicking", active_name=f"{btn_info.get('label', button_name)}...",
        success_status="Clicked", success_name=f"{btn_info.get('label', button_name)}.",
        fail_status="Failed to click", fail_name=f"{btn_info.get('label', button_name)}.",
    ))
    pm.add_stage(TuringStage("cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_menu_action(tool, args):
    """Handle 'GOOGLE.GC menu <menu_name> [--item TEXT]'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    menu_name = getattr(args, "menu_name", "")
    item_text = getattr(args, "item", "")
    menu_info = _TOP_MENU_BUTTONS.get(menu_name, {})
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_open_menu(stage=None):
        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        menu_id = menu_info["id"]
        if ov:
            ov.inject_highlight(cdp, f"#{menu_id}", label=menu_info["label"], color="#1a73e8")
            time.sleep(0.5)
        open_js = (
            f"(function(){{ var el = document.getElementById('{menu_id}');"
            f" if(!el) return 'not_found';"
            f" var r = el.getBoundingClientRect();"
            f" el.dispatchEvent(new MouseEvent('mousedown', "
            f"   {{bubbles:true, cancelable:true, clientX: r.x+r.width/2, clientY: r.y+r.height/2}}));"
            f" el.dispatchEvent(new MouseEvent('mouseup', "
            f"   {{bubbles:true, cancelable:true, clientX: r.x+r.width/2, clientY: r.y+r.height/2}}));"
            f" return 'opened'; }})()"
        )
        result = cdp.evaluate(open_js)
        if ov:
            ov.remove_highlight(cdp)
            ov.increment_mcp_count(cdp, 1)
        if result == "not_found":
            if stage:
                stage.error_brief = f"Menu button '{menu_name}' not found."
            return False
        time.sleep(1.0)
        return True

    def stage_click_item(stage=None):
        if not item_text:
            return True

        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        click_js = (
            f"(function(){{ var items = document.querySelectorAll('[role=menuitem]');"
            f" for(var i=0; i<items.length; i++){{"
            f"   var r = items[i].getBoundingClientRect();"
            f"   var t = items[i].textContent.trim();"
            f"   if(r.width > 0 && (t === '{item_text}' || t.startsWith('{item_text}'))){{"
            f"     items[i].dispatchEvent(new MouseEvent('mousedown', "
            f"       {{bubbles:true, cancelable:true, clientX: r.x+r.width/2, clientY: r.y+r.height/2}}));"
            f"     items[i].dispatchEvent(new MouseEvent('mouseup', "
            f"       {{bubbles:true, cancelable:true, clientX: r.x+r.width/2, clientY: r.y+r.height/2}}));"
            f"     items[i].dispatchEvent(new MouseEvent('click', "
            f"       {{bubbles:true, cancelable:true, clientX: r.x+r.width/2, clientY: r.y+r.height/2}}));"
            f"     return 'clicked';"
            f"   }}"
            f" }} return 'not_found'; }})()"
        )
        result = cdp.evaluate(click_js)
        if result == "not_found":
            cdp.send_and_recv("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": "Escape", "code": "Escape"
            }, timeout=5)
            if stage:
                stage.error_brief = f"Menu item '{item_text}' not found."
            return False

        if ov:
            ov.increment_mcp_count(cdp, 1)
        time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage("connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage("find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage("open_menu", stage_open_menu,
        active_status="Opening", active_name=f"{menu_info.get('label', menu_name)}...",
        success_status="Opened", success_name=f"{menu_info.get('label', menu_name)}.",
        fail_status="Failed to open", fail_name=f"{menu_info.get('label', menu_name)}.",
    ))
    if item_text:
        pm.add_stage(TuringStage("click_item", stage_click_item,
            active_status="Clicking", active_name=f"\"{item_text}\"...",
            success_status="Clicked", success_name=f"\"{item_text}\".",
            fail_status="Failed to click", fail_name=f"\"{item_text}\".",
        ))
    pm.add_stage(TuringStage("cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_bottom_action(tool, args):
    """Handle 'GOOGLE.GC bottom <panel>'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    panel = getattr(args, "panel", "")
    panel_info = _BOTTOM_BAR_BUTTONS.get(panel, {})
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    def stage_click_panel(stage=None):
        import json as _json
        from logic.chrome.session import real_click

        cdp = ctx["cdp"]
        ov = ctx["overlay"]

        ptext = panel_info["text"]
        coords_js = (
            f"(function(){{ var btns = document.querySelectorAll('[slot=bottom-pane-buttons]');"
            f" for(var i=0; i<btns.length; i++){{"
            f"   if(btns[i].textContent.indexOf('{ptext}') >= 0){{"
            f"     var r = btns[i].getBoundingClientRect();"
            f"     return JSON.stringify({{x: r.x + r.width/2, y: r.y + r.height/2}});"
            f"   }}"
            f" }} return ''; }})()"
        )
        coords_raw = cdp.evaluate(coords_js)
        if not coords_raw:
            if stage:
                stage.error_brief = f"Bottom bar '{panel}' not found."
            return False
        coords = _json.loads(coords_raw)
        real_click(cdp, int(coords["x"]), int(coords["y"]))
        if ov:
            ov.increment_mcp_count(cdp, 1)
        time.sleep(0.5)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage("connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage("find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage("click", stage_click_panel,
        active_status="Toggling", active_name=f"{panel_info.get('label', panel)}...",
        success_status="Toggled", success_name=f"{panel_info.get('label', panel)}.",
        fail_status="Failed to toggle", fail_name=f"{panel_info.get('label', panel)}.",
    ))
    pm.add_stage(TuringStage("cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def _run_sidebar_action(tool, args):
    """Handle 'GOOGLE.GC sidebar <panel>'."""
    import time
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage

    panel = getattr(args, "panel", "toc")
    ctx, stage_connect, stage_find_tab, stage_cleanup = _colab_connect_stages()

    panel_info = _SIDEBAR_BUTTONS.get(panel, {})
    aria_label = panel_info.get("aria", panel)

    def stage_click_panel(stage=None):
        cdp = ctx["cdp"]
        interact = ctx["interact"]
        ov = ctx["overlay"]

        sel = f'md-icon-button[aria-label="{aria_label}"]'
        if interact:
            interact.mcp_click(
                cdp, sel,
                label=panel_info.get("label", panel), dwell=1.0,
                color="#1a73e8", tool_name="GC",
            )
        else:
            cdp.evaluate(
                f"(function(){{ var el = document.querySelector('{sel}');"
                f" if(el) el.click(); }})()"
            )
        if ov:
            ov.increment_mcp_count(cdp, 1)
        time.sleep(1.0)
        return True

    pm = tool.create_progress_machine()
    pm.add_stage(TuringStage(
        "connect", stage_connect,
        active_status="Connecting to", active_name="Chrome CDP...",
        success_status="Connected to", success_name="Chrome CDP.",
        fail_status="Failed to connect to", fail_name="Chrome CDP.",
    ))
    pm.add_stage(TuringStage(
        "find_tab", stage_find_tab,
        active_status="Finding", active_name="Colab notebook...",
        success_status="Found", success_name="Colab notebook.",
        fail_status="Not found:", fail_name="Colab notebook.",
    ))
    pm.add_stage(TuringStage(
        "click_panel", stage_click_panel,
        active_status="Opening", active_name=f"{panel_info.get('label', panel)}...",
        success_status="Opened", success_name=f"{panel_info.get('label', panel)}.",
        fail_status="Failed to open", fail_name=f"{panel_info.get('label', panel)}.",
    ))
    pm.add_stage(TuringStage(
        "cleanup", stage_cleanup,
        active_status="Cleaning up", active_name="overlays...",
        success_status="Cleaned up", success_name="overlays.",
    ))
    pm.run(ephemeral=True)


def main():
    tool = GCTool()

    parser = argparse.ArgumentParser(
        description="Google Colab automation via CDP", add_help=False
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # GOOGLE.GC status
    subparsers.add_parser("status", help="Check Colab tab and CDP availability")

    # GOOGLE.GC state [--session SESSION_ID] [--tab TAB_LABEL]
    state_p = subparsers.add_parser("state", help="Report MCP state of Colab notebook")
    state_p.add_argument("--session", default="", help="Session ID to query")
    state_p.add_argument("--tab", default="", help="Tab label to focus on")
    state_p.add_argument("--json", action="store_true", help="Output as JSON")

    # GOOGLE.GC inject <code>
    inj_p = subparsers.add_parser("inject", help="Inject and execute code in Colab")
    inj_p.add_argument("code", help="Python code to inject")
    inj_p.add_argument("--timeout", type=int, default=120, help="Max wait seconds")
    inj_p.add_argument("--marker", default="", help="Completion marker string")

    # GOOGLE.GC cell add [--text CODE]
    cell_p = subparsers.add_parser("cell", help="Manage Colab cells via MCP")
    cell_sub = cell_p.add_subparsers(dest="cell_action", help="Cell action")
    cell_add = cell_sub.add_parser("add", help="Add a cell with MCP visual effects")
    cell_add.add_argument("--text", default="", help="Initial cell content")
    cell_add.add_argument("--cell-type", choices=["code", "text"], default="code",
                          help="Cell type: 'code' or 'text' (default: code)")

    cell_edit = cell_sub.add_parser("edit", help="Edit cell content with MCP visual effects")
    cell_edit.add_argument("--index", type=int, default=0, help="Cell index (0-based)")
    cell_edit.add_argument("--clear", action="store_true", help="Clear entire cell")
    cell_edit.add_argument("--type", dest="type_text", default="",
                           help="Type text at end (character-by-character)")
    cell_edit.add_argument("--clear-line", type=int, default=-1,
                           help="Clear a specific line (0-based)")
    cell_edit.add_argument("--line", type=int, default=-1,
                           help="Target line for --insert (0-based)")
    cell_edit.add_argument("--col", type=int, default=-1,
                           help="Column position for --insert (default: end of line)")
    cell_edit.add_argument("--insert", default="", help="Text to insert at --line/--col")
    cell_edit.add_argument("--from-line", type=int, default=-1,
                           help="Start line for batch replace (0-based)")
    cell_edit.add_argument("--to-line", type=int, default=-1,
                           help="End line for batch replace (inclusive, 0-based)")
    cell_edit.add_argument("--replace-with", default="",
                           help="Replacement text (\\n=newline, \\\\n=literal backslash-n)")

    cell_run = cell_sub.add_parser("run", help="Execute a cell with MCP visual effects")
    cell_run.add_argument("--index", type=int, default=0, help="Cell index (0-based)")
    cell_run.add_argument("--wait", type=int, default=120, help="Max wait seconds")

    cell_del = cell_sub.add_parser("delete", help="Delete a cell with MCP visual effects")
    cell_del.add_argument("--index", type=int, default=-1,
                          help="Cell index to delete (0-based, default: last)")

    cell_move = cell_sub.add_parser("move", help="Move a cell up or down")
    cell_move.add_argument("--index", type=int, default=0, help="Cell index (0-based)")
    cell_move.add_argument("--direction", choices=["up", "down"], required=True,
                           help="Direction to move the cell")

    cell_focus = cell_sub.add_parser("focus", help="Focus a cell and optionally click toolbar button")
    cell_focus.add_argument("--index", type=int, default=0, help="Cell index (0-based)")
    cell_focus.add_argument("--toolbar-click", default="",
                            choices=["", "move-up", "move-down", "delete", "edit", "more"],
                            help="Click a cell toolbar button after focusing")
    cell_focus.add_argument("--menu-click", default="",
                            choices=[""] + list(_CELL_MORE_MENU_ITEMS.keys()),
                            help="Click a 'More actions' menu item (opens ellipsis menu)")

    # GOOGLE.GC sidebar <panel>
    sb_p = subparsers.add_parser("sidebar", help="Toggle Colab sidebar panels")
    sb_p.add_argument("panel", choices=list(_SIDEBAR_BUTTONS.keys()),
                      help="Sidebar panel to toggle")

    # GOOGLE.GC toolbar <button>
    tb_p = subparsers.add_parser("toolbar", help="Click a Colab toolbar button via MCP")
    tb_p.add_argument("button", choices=list(_TOOLBAR_BUTTONS.keys()),
                      help="Toolbar button to click")

    # GOOGLE.GC menu <menu> [--item TEXT]
    menu_p = subparsers.add_parser("menu", help="Open a top-bar menu and optionally click an item")
    menu_p.add_argument("menu_name", choices=list(_TOP_MENU_BUTTONS.keys()),
                        help="Menu to open")
    menu_p.add_argument("--item", default="",
                        help="Menu item text to click (if empty, just opens menu)")

    # GOOGLE.GC bottom <panel>
    bot_p = subparsers.add_parser("bottom", help="Toggle bottom bar panels")
    bot_p.add_argument("panel", choices=list(_BOTTOM_BAR_BUTTONS.keys()),
                       help="Bottom bar panel to toggle")

    # GOOGLE.GC runtime <action>
    rt_p = subparsers.add_parser("runtime", help="Control Colab runtime via MCP")
    rt_sub = rt_p.add_subparsers(dest="rt_action", help="Runtime action")
    rt_run_all = rt_sub.add_parser("run-all", help="Run all cells")
    rt_interrupt = rt_sub.add_parser("interrupt", help="Interrupt execution")
    rt_restart = rt_sub.add_parser("restart", help="Restart runtime session")

    # GOOGLE.GC notebook <action>
    nb_p = subparsers.add_parser("notebook", help="Notebook-level operations via MCP")
    nb_sub = nb_p.add_subparsers(dest="nb_action", help="Notebook action")
    nb_save = nb_sub.add_parser("save", help="Save notebook")
    nb_clear = nb_sub.add_parser("clear-outputs", help="Clear all cell outputs")

    # GOOGLE.GC reopen
    subparsers.add_parser("reopen", help="Reopen the configured Colab notebook tab")

    # GOOGLE.GC oauth
    subparsers.add_parser("oauth", help="Handle OAuth dialog if present")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.GOOGLE.logic.chrome.session import is_chrome_cdp_available, CDPSession, CDP_PORT
    from tool.GOOGLE.logic.chrome.colab import find_colab_tab, reopen_colab_tab, inject_and_execute
    from tool.GOOGLE.logic.chrome.oauth import handle_oauth_if_needed, close_oauth_tabs

    if args.command == "state":
        if getattr(args, "json", False):
            import json as _json
            state = tool.get_mcp_state(
                session_id=getattr(args, "session", ""),
                tab_label=getattr(args, "tab", ""),
            )
            print(_json.dumps(state, indent=2, ensure_ascii=False, default=str))
        else:
            tool.print_mcp_state(
                session_id=getattr(args, "session", ""),
                tab_label=getattr(args, "tab", ""),
            )
        return

    elif args.command == "status":
        cdp_ok = is_chrome_cdp_available()
        tab = find_colab_tab() if cdp_ok else None
        if cdp_ok and tab:
            print(f"{BOLD}{GREEN}CDP{RESET}: Available")
            print(f"{BOLD}{GREEN}Colab{RESET}: {tab.get('title', tab.get('url', '?'))}")
        elif cdp_ok:
            print(f"{BOLD}{GREEN}CDP{RESET}: Available")
            print(f"{BOLD}{RED}Colab{RESET}: No tab found")
        else:
            print(f"{BOLD}{RED}CDP{RESET}: Not available (is Chrome running with --remote-debugging-port?)")

    elif args.command == "inject":
        result = inject_and_execute(
            args.code, timeout=args.timeout, done_marker=args.marker,
            log_fn=lambda m: print(f"  {BOLD}{BLUE}[GC]{RESET} {m}")
        )
        if result.get("success"):
            print(f"{BOLD}{GREEN}Success{RESET} ({result.get('duration', 0):.1f}s)")
            output = result.get("output", "")
            if output:
                print(output)
        else:
            print(f"{BOLD}{RED}Failed{RESET}: {result.get('error')}")
            errors = result.get("errors", "")
            if errors:
                print(errors)

    elif args.command == "cell":
        action = getattr(args, "cell_action", None)
        if action == "edit":
            _run_cell_edit(tool, args)
        elif action == "run":
            _run_cell_execute(tool, args)
        elif action == "delete":
            _run_cell_delete(tool, args)
        elif action == "move":
            _run_cell_move(tool, args)
        elif action == "focus":
            _run_cell_focus(tool, args)
        else:
            _run_cell_action(tool, args)

    elif args.command == "sidebar":
        _run_sidebar_action(tool, args)

    elif args.command == "toolbar":
        _run_toolbar_action(tool, args)

    elif args.command == "menu":
        _run_menu_action(tool, args)

    elif args.command == "bottom":
        _run_bottom_action(tool, args)

    elif args.command == "runtime":
        _run_runtime_action(tool, args)

    elif args.command == "notebook":
        _run_notebook_action(tool, args)

    elif args.command == "reopen":
        tab = reopen_colab_tab(
            log_fn=lambda m: print(f"  {BOLD}{BLUE}[GC]{RESET} {m}")
        )
        if tab:
            print(f"{BOLD}{GREEN}Reopened{RESET}: {tab.get('title', tab.get('url', '?'))}")
        else:
            print(f"{BOLD}{RED}Failed{RESET} to reopen Colab tab")

    elif args.command == "oauth":
        tab = find_colab_tab()
        if not tab:
            print(f"{BOLD}{RED}Error{RESET}: No Colab tab found")
            return
        session = CDPSession(tab["webSocketDebuggerUrl"])
        try:
            result = handle_oauth_if_needed(
                session,
                log_fn=lambda m: print(f"  {BOLD}{BLUE}[OAuth]{RESET} {m}")
            )
            print(f"{BOLD}OAuth result{RESET}: {result}")
        finally:
            session.close()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
