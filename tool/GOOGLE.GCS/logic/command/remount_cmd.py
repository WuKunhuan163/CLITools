#!/usr/bin/env python3
"""GCS --remount command: generate and execute Colab remount script via GUI."""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from interface.config import get_color
from interface.turing import ProgressTuringMachine
from interface.turing import TuringStage

_DEBUG_LOG = Path("/Applications/AITerminalTools/tmp/remount_debug.log")


def _debug_log(msg):
    try:
        _DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_DEBUG_LOG, "a") as f:
            ts = time.strftime("%H:%M:%S")
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _t(tool, key, default):
    try:
        from interface.lang import get_translation
        logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
        return get_translation(logic_dir, key, default)
    except Exception:
        return default


def execute(tool, args, state_mgr, load_logic, no_feedback=False, **kwargs):
    remount_mod = load_logic("remount")
    script, metadata = remount_mod.generate_remount_script(tool.project_root)
    if not script:
        print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: {metadata}")
        return 1

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"

    if cdp_enabled:
        return _execute_cdp(tool, remount_mod, script, metadata, no_feedback)
    return _execute_manual(tool, remount_mod, load_logic, script, metadata)


# ---------------------------------------------------------------------------
# MCP / CDP path — fully automated with OAuth handling
# ---------------------------------------------------------------------------

def _is_cell_done(session, cell_idx=0, min_exec_count=0):
    """Return True if the injected code cell completed AFTER our run started."""
    try:
        state = session.evaluate(f"""
            (function() {{
                var cells = colab.global.notebook.cells;
                if (!cells || {cell_idx} >= cells.length) return 'no_cell';
                var cell = cells[{cell_idx}];
                if (typeof cell.isPending !== 'function') return 'not_code';
                if (cell.isRunning()) return 'running';
                if (cell.isPending()) return 'pending';
                var ec = typeof cell.getExecutionCount === 'function'
                         ? cell.getExecutionCount() : 0;
                return ec > {min_exec_count} ? 'done' : 'not_started';
            }})()
        """) or ""
        return state == "done"
    except Exception:
        return False


def _launch_mcp_gui(tool, script, metadata):
    """Launch the remount GUI in background for MCP mode fallback."""
    logic_script = Path(__file__).resolve().parent.parent / "remount.py"
    tmp_script = tool.project_root / "tmp" / f"gcs_remount_{metadata['ts']}.py"
    tmp_script.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_script, "w") as f:
        f.write(script)

    env = os.environ.copy()
    env["TK_SILENCE_DEPRECATION"] = "1"
    env["GDS_GUI_MANAGED"] = "1"

    cmd = [
        sys.executable, str(logic_script),
        "--script-path", str(tmp_script),
        "--ts", metadata["ts"],
        "--hash", metadata["session_hash"],
        "--project-root", str(tool.project_root),
        "--mcp",
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True, env=env,
    )
    _debug_log(f"_launch_mcp_gui: pid={proc.pid}")
    return proc, tmp_script


def _close_mcp_gui(tool, proc):
    """Auto-close the MCP GUI via submit flag file."""
    if not proc or proc.poll() is not None:
        return
    stops_dir = tool.project_root / "data" / "run" / "stops"
    stops_dir.mkdir(parents=True, exist_ok=True)
    submit_file = stops_dir / f"{proc.pid}.submit"
    submit_file.touch()
    _debug_log(f"_close_mcp_gui: created {submit_file}")
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def _execute_cdp(tool, remount_mod, script, metadata, no_feedback=False):
    """Remount via CDP with 4 Turing Machine stages.

    Stage 1: Inject remount cell into Colab
    Stage 2: Handle OAuth authorization (auto-skip if not needed)
    Stage 3: Wait for mount cell to finish executing
    Stage 4: Verify the mount result via Drive API
    """
    from logic.chrome.session import CDPSession, is_chrome_cdp_available, CDP_PORT
    from tool.GOOGLE.logic.chrome.colab import find_colab_tab, _reopen_colab_tab as reopen_colab_tab
    from tool.GOOGLE.logic.chrome.oauth import handle_oauth_if_needed, close_oauth_tabs

    session_holder = [None]
    cell_done_early = [False]
    injected_cell_idx = [0]
    start_exec_count = [0]
    overlay_mod = [None]

    def _load_overlay():
        try:
            from logic.cdmcp_loader import load_cdmcp_overlay
            overlay_mod[0] = load_cdmcp_overlay()
        except Exception:
            pass

    def _apply_overlays(session):
        ov = overlay_mod[0]
        if not ov or not session:
            return
        try:
            ov.inject_badge(session, text="GCS [remount]", color="#0d904f")
            ov.inject_focus(session, color="#0d904f")
            ov.inject_favicon(session, svg_color="#0d904f", letter="G")
            ov.inject_lock(session, base_opacity=0.08, flash_opacity=0.25,
                           tool_name="GCS")
        except Exception:
            pass

    def _cleanup_overlays(session):
        ov = overlay_mod[0]
        if not ov or not session:
            return
        try:
            ov.remove_all_overlays(session)
        except Exception:
            pass

    _load_overlay()

    gui_proc, gui_tmp_script = None, None
    if not no_feedback:
        gui_proc, gui_tmp_script = _launch_mcp_gui(tool, script, metadata)

    # -- Stage 1: inject ------------------------------------------------
    def stage_inject(stage=None):
        _debug_log("stage_inject: start")
        if not is_chrome_cdp_available():
            if stage:
                stage.error_brief = "Chrome CDP not available"
            return False

        tab = find_colab_tab()
        if not tab:
            _debug_log("stage_inject: no tab, attempting reopen")
            tab = reopen_colab_tab(log_fn=lambda m: _debug_log(f"reopen: {m}"))
        if not tab:
            if stage:
                stage.error_brief = "No Colab tab found"
            return False

        session = CDPSession(tab["webSocketDebuggerUrl"], timeout=30)
        session_holder[0] = session
        _apply_overlays(session)

        session.evaluate("""
            (function(){
                var dlgs = document.querySelectorAll('mwc-dialog[open]');
                dlgs.forEach(function(d){ d.removeAttribute('open'); });
            })()
        """)
        time.sleep(0.5)

        cell_count = session.evaluate(
            "(function(){"
            " var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0;"
            "})()"
        )
        cell_count = int(cell_count or 0)
        _debug_log(f"stage_inject: existing cells = {cell_count}")

        if cell_count > 0:
            removed = session.evaluate("""
                (function(){
                    var nb = colab.global.notebook;
                    var cells = nb.cells;
                    if (!Array.isArray(cells) || cells.length === 0) return 0;
                    var toRemove = cells.slice();
                    try { nb.removeCells(toRemove); } catch(e) { return -1; }
                    return toRemove.length;
                })()
            """)
            _debug_log(f"stage_inject: removed {removed} cells")
            time.sleep(1)

        remaining = session.evaluate(
            "(function(){"
            " var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0;"
            "})()"
        )
        _debug_log(f"stage_inject: cells after clear = {remaining}")

        session.evaluate("""
            (function(){
                var btn = document.querySelector('#toolbar-add-code');
                if(btn){ btn.click(); return 'clicked'; }
                var adds = document.querySelectorAll('.add-cell .add-code');
                if(adds.length){ adds[0].click(); return 'clicked_alt'; }
                return 'not_found';
            })()
        """)
        time.sleep(1.5)

        new_count = session.evaluate(
            "(function(){"
            " var c = colab.global.notebook.cells;"
            " return Array.isArray(c) ? c.length : 0;"
            "})()"
        )
        _debug_log(f"stage_inject: cells after add = {new_count}")
        if int(new_count or 0) < 1:
            if stage:
                stage.error_brief = "Failed to add code cell"
            return False

        injected_cell_idx[0] = 0

        ci = injected_cell_idx[0]
        code_json = json.dumps(script)
        session.evaluate(f"colab.global.notebook.cells[{ci}].setText({code_json})")
        time.sleep(0.5)

        verify_text = session.evaluate(
            f"(function(){{ return colab.global.notebook.cells[{ci}]"
            f".getText().substring(0,50); }})()"
        )
        _debug_log(f"stage_inject: setText verify = {verify_text}")

        ec_initial = session.evaluate(
            f"(function(){{ var c=colab.global.notebook.cells[{ci}];"
            f" return typeof c.getExecutionCount==='function'?c.getExecutionCount():0; }})()"
        )
        start_exec_count[0] = int(ec_initial or 0)

        def _click_run(s, idx):
            return s.evaluate(f"""
                (function(){{
                    var cell = colab.global.notebook.cells[{idx}];
                    if(!cell) return 'no_cell';
                    var el = cell.element_;
                    if(!el) return 'no_element';
                    el.scrollIntoView({{behavior:'instant',block:'center'}});
                    try {{ if(cell.enterCell) cell.enterCell(); }} catch(e) {{}}
                    var btn = el.querySelector('colab-run-button');
                    if(!btn) return 'no_btn';
                    btn.click();
                    return 'clicked';
                }})()
            """)

        click_result = _click_run(session, ci)
        _debug_log(f"stage_inject: click_result = {click_result}")
        time.sleep(3)

        too_many = session.evaluate("""
            (function(){
                var btns = document.querySelectorAll('md-text-button');
                for (var i = 0; i < btns.length; i++) {
                    if ((btns[i].innerText||'').trim()==='Terminate other sessions') return 'found';
                }
                return '';
            })()
        """)
        if too_many == "found":
            _debug_log("stage_inject: too many sessions, using kernel API to terminate others")
            term_result = session.send_and_recv("Runtime.evaluate", {
                "expression": """
                    (async function(){
                        try {
                            var k = colab.global.notebook.kernel;
                            var ss = await k.listNotebookSessions();
                            if (!Array.isArray(ss)) return JSON.stringify({killed: 0});
                            var currentFile = k.getNotebookId();
                            var killed = 0;
                            for (var i = 0; i < ss.length; i++) {
                                var sid = ss[i].sessionId;
                                var fid = ss[i].fileId || (ss[i].notebookId||{}).fileId || '';
                                if (fid === currentFile) continue;
                                try { await k.terminateSession({sessionId: sid}); killed++; }
                                catch(e) {}
                            }
                            return JSON.stringify({killed: killed, total: ss.length});
                        } catch(e) { return JSON.stringify({error: e.message}); }
                    })()
                """,
                "awaitPromise": True,
                "returnByValue": True,
            })
            term_val = term_result.get("result", {}).get("value", "{}")
            _debug_log(f"stage_inject: terminate result = {term_val}")
            time.sleep(3)

            session.evaluate("""
                (function(){
                    var dlgs = document.querySelectorAll('mwc-dialog[open]');
                    dlgs.forEach(function(d){ d.removeAttribute('open'); });
                })()
            """)
            time.sleep(1)

            ec_now = session.evaluate(
                f"(function(){{ var c=colab.global.notebook.cells[{ci}];"
                f" return typeof c.getExecutionCount==='function'?c.getExecutionCount():0; }})()"
            )
            start_exec_count[0] = int(ec_now or 0)
            _debug_log(f"stage_inject: exec count before retry = {start_exec_count[0]}")
            _click_run(session, ci)
            _debug_log("stage_inject: retried after session cleanup")
        _debug_log("stage_inject: cell execution started")
        time.sleep(1)
        return True

    # -- Stage 2: OAuth --------------------------------------------------
    def stage_oauth(stage=None):
        session = session_holder[0]
        if not session:
            return False
        _debug_log("stage_oauth: start")

        session.evaluate("""
            (function(){
                var dlgs = document.querySelectorAll('mwc-dialog[open]');
                dlgs.forEach(function(d){
                    var txt = d.textContent || '';
                    if (txt.indexOf('Permit this notebook') >= 0) return;
                    if (d.close) d.close();
                    else d.removeAttribute('open');
                });
            })()
        """)
        time.sleep(0.5)

        ov = overlay_mod[0]
        if ov:
            try:
                ov.set_lock_passthrough(session, True)
                _debug_log("stage_oauth: lock passthrough enabled")
            except Exception:
                pass

        def _cell_done():
            done = _is_cell_done(session, injected_cell_idx[0], start_exec_count[0])
            if done:
                cell_done_early[0] = True
            return done

        result = handle_oauth_if_needed(
            session,
            port=CDP_PORT,
            dialog_timeout=60,
            popup_timeout=90,
            log_fn=lambda m: _debug_log(f"oauth: {m}"),
            cell_done_fn=_cell_done,
        )
        _debug_log(f"stage_oauth: result={result}")

        if ov:
            try:
                ov.set_lock_passthrough(session, False)
                _debug_log("stage_oauth: lock passthrough disabled")
            except Exception:
                pass

        if result == "not_needed":
            if stage:
                stage.success_status = _t(tool, "remount_oauth_skipped", "Skipped")
                stage.success_name = _t(tool, "remount_oauth_not_needed_label", "authorization (not needed)")
            return True
        if result == "success":
            return True
        if stage:
            stage.error_brief = _t(tool, "remount_oauth_failed", "OAuth authorization failed")
        return False

    # -- Stage 3: wait for cell completion --------------------------------
    def stage_wait(stage=None):
        session = session_holder[0]
        if not session:
            return False
        if cell_done_early[0]:
            _debug_log("stage_wait: already done (early)")
            return True
        _debug_log("stage_wait: polling cell state")
        ci = injected_cell_idx[0]
        for i in range(90):
            time.sleep(2)
            if _is_cell_done(session, ci, start_exec_count[0]):
                _debug_log(f"stage_wait: cell done at {(i+1)*2}s")
                return True
            if i < 5 or i % 10 == 0:
                try:
                    st = session.evaluate(f"""
                        (function(){{
                            var c = colab.global.notebook.cells[{ci}];
                            if(!c) return 'no_cell';
                            return JSON.stringify({{
                                r: typeof c.isRunning==='function'?c.isRunning():null,
                                p: typeof c.isPending==='function'?c.isPending():null,
                                e: typeof c.getExecutionCount==='function'?c.getExecutionCount():null,
                                o: typeof c.hasOutput==='function'?c.hasOutput():null
                            }});
                        }})()
                    """)
                    _debug_log(f"stage_wait: {(i+1)*2}s state={st}")
                except Exception:
                    _debug_log(f"stage_wait: {(i+1)*2}s evaluate failed")
        if stage:
            stage.error_brief = "Cell execution timed out (180 s)"
        _debug_log("stage_wait: timeout")
        return False

    # -- Stage 4: verify mount result ------------------------------------
    def stage_verify(stage=None):
        if session_holder[0]:
            _cleanup_overlays(session_holder[0])
            try:
                session_holder[0].close()
            except Exception:
                pass
            session_holder[0] = None
        close_oauth_tabs(CDP_PORT)

        time.sleep(1.0)
        ok, msg = remount_mod.verify_local_remount_result(
            tool.project_root, metadata["ts"], metadata["session_hash"], stage=stage
        )
        if not ok and stage:
            stage.fail_status = _t(tool, "turing_failed_to_verify", "Failed to verify")
            stage.fail_name = _t(tool, "remount_result_label", "remount result")
            stage.error_brief = msg
        _debug_log(f"stage_verify: ok={ok} msg={msg}")
        return ok

    # -- Build Turing Machine --------------------------------------------
    inject_label = _t(tool, "remount_injecting_cell", "Injecting remount cell into Colab")
    oauth_label = _t(tool, "remount_handling_oauth", "Handling OAuth authorization")
    wait_label = _t(tool, "remount_waiting_mount", "Waiting for mount to complete")
    verify_label = _t(tool, "remount_verifying_result", "Verifying the remount result")

    pm = ProgressTuringMachine(
        project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir()
    )
    pm.add_stage(TuringStage(
        "inject cell", stage_inject,
        active_status="", active_name=inject_label,
        fail_status=_t(tool, "turing_failed_to_complete", "Failed to complete"),
        success_status=_t(tool, "remount_injected", "Injected"),
        success_name=_t(tool, "remount_cell_label", "remount cell"),
        bold_part=inject_label,
    ))
    pm.add_stage(TuringStage(
        "oauth", stage_oauth,
        active_status="", active_name=oauth_label,
        fail_status=_t(tool, "turing_failed_to_complete", "Failed to complete"),
        success_status=_t(tool, "remount_oauth_handled", "Handled"),
        success_name=_t(tool, "remount_oauth_label", "OAuth authorization"),
        bold_part=oauth_label,
    ))
    pm.add_stage(TuringStage(
        "wait mount", stage_wait,
        active_status="", active_name=wait_label,
        fail_status=_t(tool, "turing_failed_to_complete", "Failed to complete"),
        success_status=_t(tool, "remount_mount_completed", "Completed"),
        success_name=_t(tool, "remount_mount_label", "mount operation"),
        bold_part=wait_label,
    ))
    pm.add_stage(TuringStage(
        "verify result", stage_verify,
        active_status="", active_name=verify_label,
        fail_status=_t(tool, "turing_failed_to_verify", "Failed to verify"),
        fail_name=_t(tool, "remount_result_label", "remount result"),
        success_status=_t(tool, "remount_verified", "Verified"),
        success_name=_t(tool, "remount_result_label", "remount result"),
        bold_part=verify_label,
    ))

    if pm.run(ephemeral=True):
        if gui_proc:
            _close_mcp_gui(tool, gui_proc)
        if gui_tmp_script and gui_tmp_script.exists():
            try:
                gui_tmp_script.unlink()
            except Exception:
                pass
        print(
            f"{get_color('BOLD')}{get_color('GREEN')}Successfully remounted"
            f"{get_color('RESET')} Google Drive from Google Colab."
        )
        config_path = tool.project_root / "data" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = json.load(f)
            cfg["mount_hash"] = metadata["session_hash"]
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
        return 0

    if session_holder[0]:
        _cleanup_overlays(session_holder[0])
        try:
            session_holder[0].close()
        except Exception:
            pass
    if gui_tmp_script and gui_tmp_script.exists():
        try:
            gui_tmp_script.unlink()
        except Exception:
            pass
    return 1


# ---------------------------------------------------------------------------
# Manual path — existing GUI-based flow (non-MCP)
# ---------------------------------------------------------------------------

def _execute_manual(tool, remount_mod, load_logic, script, metadata):
    """Remount via manual GUI interaction (non-MCP mode)."""

    logic_script = Path(__file__).resolve().parent.parent / "remount.py"
    gui_args = [
        "--script-path", "",
        "--ts", metadata["ts"],
        "--hash", metadata["session_hash"],
        "--project-root", str(tool.project_root),
    ]

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)

        tmp_script = tool.project_root / "tmp" / f"gcs_remount_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, "w") as f:
            f.write(script)
        gui_args[1] = str(tmp_script)
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, str(logic_script), 300,
                args=gui_args, request_id=f"remount_{metadata['ts']}",
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()
        if res.get("status") == "success":
            return True
        if stage:
            _set_failure_reason(stage, res)
        return False

    def verify_action(stage=None):
        time.sleep(1.0)
        ok, msg = remount_mod.verify_local_remount_result(
            tool.project_root, metadata["ts"], metadata["session_hash"], stage=stage
        )
        if not ok and stage:
            stage.fail_status = "Failed to verify"
            stage.fail_name = "remount result"
            stage.error_brief = msg
        return ok

    waiting_label = _t(tool, "turing_waiting_user_action", "Waiting for user action")
    verifying_label = _t(tool, "turing_verifying_result", "Verifying the remount result file")

    pm = ProgressTuringMachine(
        project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir()
    )
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="", active_name=waiting_label,
        fail_status="Failed to complete", success_status="Completed",
        success_name="user action", bold_part=waiting_label,
    ))
    pm.add_stage(TuringStage(
        "result file", verify_action,
        active_status="", active_name=verifying_label,
        fail_status="Failed to verify", fail_name="remount result",
        success_status="Verified", success_name="remount result",
        bold_part=verifying_label,
    ))

    if pm.run(ephemeral=True):
        print(
            f"{get_color('BOLD')}{get_color('GREEN')}Successfully remounted"
            f"{get_color('RESET')} Google Drive from Google Colab."
        )
        config_path = tool.project_root / "data" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = json.load(f)
            cfg["mount_hash"] = metadata["session_hash"]
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
        return 0
    return 1


def _set_failure_reason(stage, res, tool=None):
    status = res.get("status", "error")
    reason = res.get("reason", "")
    if status == "cancelled" or reason in ("interrupted", "signal", "stop"):
        stage.fail_status = _t(tool, "turing_cancelled", "Cancelled") if tool else "Cancelled"
        stage.fail_name = ""
        stage.fail_color = "YELLOW"
        stage.error_brief = _t(tool, "turing_cancelled_by_user", "Cancelled by user.") if tool else "Cancelled by user."
    elif status == "timeout":
        stage.error_brief = _t(tool, "turing_gui_timed_out", "GUI timed out.") if tool else "GUI timed out."
    else:
        stage.error_brief = res.get("message",
                                    _t(tool, "turing_gui_closed_unexpectedly", "GUI closed unexpectedly.") if tool else "GUI closed unexpectedly.")
