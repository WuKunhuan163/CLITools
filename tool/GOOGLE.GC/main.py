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

        if interact:
            interact.mcp_click(
                cdp, "#toolbar-add-code",
                label="+ Code (create cell)", dwell=1.0,
                color="#e8710a", tool_name="GC",
            )
        else:
            cdp.evaluate(
                "(function(){ var b = document.getElementById('toolbar-add-code');"
                " if(b) b.click(); })()"
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
                ov.inject_highlight(cdp, ".cell.code:last-child",
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
    pm.add_stage(TuringStage(
        "add_cell", stage_add_cell,
        active_status="Creating", active_name="code cell...",
        success_status="Created", success_name="code cell.",
        fail_status="Failed to create", fail_name="code cell.",
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


def main():
    tool = ToolBase("GOOGLE.GC")

    parser = argparse.ArgumentParser(
        description="Google Colab automation via CDP", add_help=False
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # GOOGLE.GC status
    subparsers.add_parser("status", help="Check Colab tab and CDP availability")

    # GOOGLE.GC inject <code>
    inj_p = subparsers.add_parser("inject", help="Inject and execute code in Colab")
    inj_p.add_argument("code", help="Python code to inject")
    inj_p.add_argument("--timeout", type=int, default=120, help="Max wait seconds")
    inj_p.add_argument("--marker", default="", help="Completion marker string")

    # GOOGLE.GC cell add [--text CODE]
    cell_p = subparsers.add_parser("cell", help="Manage Colab cells via MCP")
    cell_sub = cell_p.add_subparsers(dest="cell_action", help="Cell action")
    cell_add = cell_sub.add_parser("add", help="Add a code cell with MCP visual effects")
    cell_add.add_argument("--text", default="", help="Initial cell content")

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

    if args.command == "status":
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
        else:
            _run_cell_action(tool, args)

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
