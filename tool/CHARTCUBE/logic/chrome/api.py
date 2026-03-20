"""ChartCube operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP sessions to manage the chartcube.alipay.com browser tab with
visual overlays and MCP interaction interfaces.

Pattern follows XMIND: boot_tool_session -> require_tab -> CDPSession(ws).
CDPSession is cached to avoid multiple WebSocket connections to the same target.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from interface.chrome import CDPSession, CDP_PORT
from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
)

CHARTCUBE_HOME = "https://chartcube.alipay.com"
CHARTCUBE_UPLOAD = "https://chartcube.alipay.com/upload"
CHARTCUBE_GUIDE = "https://chartcube.alipay.com/guide"
CHARTCUBE_MAKE = "https://chartcube.alipay.com/make"
CHARTCUBE_EXPORT = "https://chartcube.alipay.com/export"

_session_name = "chartcube"
_cc_session = None
_cc_cdp: Optional[CDPSession] = None
_cc_tab_ws: Optional[str] = None

TOOL_COLOR = "#6236ff"
TOOL_LETTER = "C"


def _load_session_mgr():
    return load_cdmcp_sessions()


def _load_overlay():
    return load_cdmcp_overlay()


def _get_or_create_session(port: int = CDP_PORT):
    global _cc_session
    _debug_log("_get_or_create_session: checking in-memory _cc_session...")
    if _cc_session is not None:
        cdp = _cc_session.get_cdp()
        if cdp:
            _debug_log("_get_or_create_session: in-memory session alive")
            return _cc_session
        _debug_log("_get_or_create_session: in-memory session dead, clearing")
        _cc_session = None

    sm = _load_session_mgr()
    _debug_log("_get_or_create_session: checking persistent session...")
    existing = sm.get_session(_session_name)
    if existing:
        _debug_log(f"_get_or_create_session: found persistent session: {existing.session_id[:8]}")
        cdp = existing.get_cdp()
        if cdp:
            _debug_log("_get_or_create_session: persistent session alive")
            _cc_session = existing
            return existing
        _debug_log("_get_or_create_session: persistent session dead, closing")
        sm.close_session(_session_name)
    else:
        _debug_log("_get_or_create_session: no persistent session found")
    return None


def _apply_overlays(cdp):
    overlay = _load_overlay()
    overlay.inject_favicon(cdp, svg_color=TOOL_COLOR, letter=TOOL_LETTER)
    overlay.inject_badge(cdp, text="ChartCube MCP", color=TOOL_COLOR)
    overlay.inject_focus(cdp, color=TOOL_COLOR)


def _get_chartcube_cdp(session, port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get a CDPSession pointing at the ChartCube tab, reusing cached connection."""
    global _cc_cdp, _cc_tab_ws

    tab_info = session.require_tab(
        "chartcube",
        url_pattern="chartcube.alipay.com",
        open_url=CHARTCUBE_HOME,
        auto_open=True,
        wait_sec=10,
    )
    if not tab_info or not tab_info.get("ws"):
        return None

    ws_url = tab_info["ws"]

    if _cc_cdp is not None and _cc_tab_ws == ws_url:
        try:
            _cc_cdp.evaluate("1")
            return _cc_cdp
        except Exception:
            try:
                _cc_cdp.close()
            except Exception:
                pass
            _cc_cdp = None
            _cc_tab_ws = None

    if _cc_cdp is not None:
        try:
            _cc_cdp.close()
        except Exception:
            pass
        _cc_cdp = None
        _cc_tab_ws = None

    try:
        _cc_cdp = CDPSession(ws_url)
        _cc_tab_ws = ws_url
        return _cc_cdp
    except Exception:
        return None


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get an active CDPSession for the ChartCube tab, booting if needed."""
    global _cc_session

    session = _get_or_create_session(port)
    if not session:
        r = boot_session(port)
        if not r.get("ok"):
            return None
        session = _get_or_create_session(port)

    if not session:
        return None

    cdp = _get_chartcube_cdp(session, port)
    if cdp:
        try:
            overlay = _load_overlay()
            has_badge = cdp.evaluate(f"!!document.getElementById('{overlay.CDMCP_BADGE_ID}')")
            if not has_badge:
                _apply_overlays(cdp)
        except Exception:
            pass
    return cdp


def _debug_log(msg: str):
    """Write debug messages to tmp/boot_debug.log for diagnostics."""
    log_path = Path(__file__).resolve().parent.parent.parent / "tmp" / "boot_debug.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    with open(log_path, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a ChartCube CDMCP session using the unified boot interface."""
    global _cc_session, _cc_cdp, _cc_tab_ws

    _debug_log(f"boot_session called, port={port}")

    if _cc_cdp is not None:
        try:
            _cc_cdp.close()
        except Exception:
            pass
        _cc_cdp = None
        _cc_tab_ws = None

    _debug_log("Checking for existing session...")
    existing = _get_or_create_session(port)
    if existing:
        _debug_log(f"Found existing session: {existing}")
        cdp = _get_chartcube_cdp(existing, port)
        if cdp:
            _apply_overlays(cdp)
            url = cdp.evaluate("window.location.href") or ""
            _debug_log(f"Reusing existing session, url={url}")
            return {"ok": True, "action": "already_booted", "url": url}

    _debug_log("No existing session, loading session manager...")
    try:
        sm = _load_session_mgr()
        _debug_log(f"Session manager loaded: {type(sm).__name__}")
    except Exception as e:
        _debug_log(f"Failed to load session manager: {e}")
        return {"ok": False, "error": f"Session manager load failed: {e}"}

    from interface.chrome import is_chrome_cdp_available
    cdp_ok = is_chrome_cdp_available(port)
    _debug_log(f"Pre-boot CDP check: available={cdp_ok}")

    max_attempts = 2
    boot_result = None
    for attempt in range(1, max_attempts + 1):
        _debug_log(f"boot_tool_session attempt {attempt}/{max_attempts} ('{_session_name}', port={port})")
        try:
            boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)
            _debug_log(f"boot_tool_session result (attempt {attempt}): ok={boot_result.get('ok')}, "
                        f"action={boot_result.get('action')}, error={boot_result.get('error')}")
        except Exception as e:
            _debug_log(f"boot_tool_session exception (attempt {attempt}): {e}")
            boot_result = {"ok": False, "error": f"Boot exception: {e}"}

        if boot_result.get("ok"):
            break

        if attempt < max_attempts:
            err = boot_result.get("error", "")
            _debug_log(f"Boot failed ({err}), rechecking CDP before retry...")
            cdp_ok_retry = is_chrome_cdp_available(port)
            _debug_log(f"CDP available after failure: {cdp_ok_retry}")
            if not cdp_ok_retry:
                _debug_log("CDP unavailable — attempting ensure_chrome via session manager...")
                try:
                    chrome_result = sm.ensure_chrome(port)
                    _debug_log(f"ensure_chrome result: {chrome_result}")
                except Exception as e:
                    _debug_log(f"ensure_chrome exception: {e}")
            time.sleep(2)

    if not boot_result or not boot_result.get("ok"):
        err = (boot_result or {}).get("error", "Boot failed")
        _debug_log(f"All boot attempts failed: {err}")
        cdp_final = is_chrome_cdp_available(port)
        _debug_log(f"Final CDP check: available={cdp_final}")
        hint = ""
        if not cdp_final:
            hint = " Ensure Chrome is running with --remote-debugging-port=9222, or run 'CDMCP boot' first."
        return {"ok": False, "error": f"{err}{hint}"}

    _cc_session = boot_result.get("session")

    tab_info = _cc_session.require_tab(
        "chartcube",
        url_pattern="chartcube.alipay.com",
        open_url=CHARTCUBE_HOME,
        auto_open=True,
        wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        _cc_tab_ws = tab_info["ws"]
        _cc_cdp = CDPSession(_cc_tab_ws)
        time.sleep(3)
        _apply_overlays(_cc_cdp)

        current_url = _cc_cdp.evaluate("window.location.href") or ""
        if "/upload" not in current_url and "/guide" not in current_url and "/make" not in current_url and "/export" not in current_url:
            _cc_cdp.evaluate("""
                (function() {
                    var buttons = document.querySelectorAll("button");
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.trim().includes("立即制作图表")) {
                            buttons[i].click();
                            return true;
                        }
                    }
                    return false;
                })()
            """)
            time.sleep(2)

    return {
        "ok": True,
        "action": boot_result.get("action", "booted"),
        "url": CHARTCUBE_UPLOAD,
    }


def get_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current ChartCube page status."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var url = window.location.href;
                var path = window.location.pathname;
                var step = 'unknown';
                if (path.includes('/upload')) step = 'upload';
                else if (path.includes('/guide')) step = 'guide';
                else if (path.includes('/make')) step = 'make';
                else if (path.includes('/export') || path.includes('/download')) step = 'export';
                else if (path === '/') step = 'home';
                return JSON.stringify({
                    ok: true, url: url,
                    title: document.title,
                    step: step,
                    path: path
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get detailed page information including interactive elements."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var url = window.location.href;
                var path = window.location.pathname;
                var buttons = [];
                document.querySelectorAll('button').forEach(function(b) {
                    var text = (b.textContent || '').trim();
                    if (text && !b.disabled) {
                        buttons.push(text.substring(0, 50));
                    }
                });
                var headings = [];
                document.querySelectorAll('h1, h2, h3').forEach(function(h) {
                    var text = (h.textContent || '').trim();
                    if (text) headings.push(text.substring(0, 60));
                });
                return JSON.stringify({
                    ok: true, url: url, path: path,
                    title: document.title,
                    buttons: buttons.slice(0, 20),
                    headings: headings.slice(0, 20)
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_step(step: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to a specific ChartCube wizard step."""
    step_urls = {
        "upload": CHARTCUBE_UPLOAD,
        "guide": CHARTCUBE_GUIDE,
        "make": CHARTCUBE_MAKE,
        "export": CHARTCUBE_EXPORT,
        "home": CHARTCUBE_HOME,
    }
    url = step_urls.get(step)
    if not url:
        return {"ok": False, "error": f"Unknown step: {step}. Valid: {list(step_urls.keys())}"}

    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    try:
        cdp.evaluate(f"window.location.href = {json.dumps(url)}")
        time.sleep(2)
        return {"ok": True, "step": step, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def use_sample_data(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    """Select a built-in sample dataset on the Upload page.

    index: 0-based index of the sample (0=first, 1=second, 2=third).
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var radios = document.querySelectorAll('input[type="radio"]');
                if (radios.length === 0) {{
                    var labels = document.querySelectorAll('.ant-radio-wrapper');
                    if (labels.length > {index}) {{
                        labels[{index}].click();
                        return JSON.stringify({{ok: true, selected: {index}, method: 'label'}});
                    }}
                    return JSON.stringify({{ok: false, error: 'No sample radio buttons found'}});
                }}
                if ({index} >= radios.length) {{
                    return JSON.stringify({{ok: false, error: 'Index out of range, max=' + (radios.length-1)}});
                }}
                radios[{index}].click();
                return JSON.stringify({{ok: true, selected: {index}, method: 'radio'}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def click_next(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click the 'Next Step' button on the current page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var text = (buttons[i].textContent || '').trim();
                    if (text.includes('下一步') || text.includes('Next')) {
                        buttons[i].click();
                        return JSON.stringify({ok: true, clicked: text});
                    }
                }
                return JSON.stringify({ok: false, error: 'Next button not found'});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def select_chart_type(chart_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Select a chart type on the Guide page by name (e.g. '柱状图', '折线图')."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var cards = document.querySelectorAll('.chart-view');
                for (var i = 0; i < cards.length; i++) {{
                    var text = (cards[i].textContent || '').trim();
                    if (text === {json.dumps(chart_name)}) {{
                        cards[i].click();
                        return JSON.stringify({{ok: true, selected: text}});
                    }}
                }}
                var all = document.querySelectorAll('[class*="chart"], [class*="Card"]');
                for (var i = 0; i < all.length; i++) {{
                    var text = (all[i].textContent || '').trim();
                    if (text.includes({json.dumps(chart_name)})) {{
                        all[i].click();
                        return JSON.stringify({{ok: true, selected: text.substring(0, 50), method: 'fallback'}});
                    }}
                }}
                return JSON.stringify({{ok: false, error: 'Chart type not found: ' + {json.dumps(chart_name)}}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_chart(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click the 'Generate Chart' / '完成配置，生成图表' button on the Make page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var text = (buttons[i].textContent || '').trim();
                    if (text.includes('生成图表') || text.includes('Generate')) {
                        buttons[i].click();
                        return JSON.stringify({ok: true, clicked: text});
                    }
                }
                return JSON.stringify({ok: false, error: 'Generate button not found'});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def select_columns(columns: str = "all", port: int = CDP_PORT) -> Dict[str, Any]:
    """Select data columns on the Upload page.

    columns: "all" to select all, or comma-separated column names.
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        if columns == "all":
            r = cdp.evaluate("""
                (function() {
                    var labels = document.querySelectorAll("label.ant-checkbox-wrapper");
                    for (var i = 0; i < labels.length; i++) {
                        if ((labels[i].textContent || "").trim() === "全部") {
                            var cb = labels[i].querySelector(".ant-checkbox");
                            var isChecked = cb && cb.classList.contains("ant-checkbox-checked");
                            if (!isChecked) labels[i].click();
                            return JSON.stringify({ok: true, action: "select_all"});
                        }
                    }
                    return JSON.stringify({ok: false, error: "全部 checkbox not found"});
                })()
            """)
        else:
            col_list = [c.strip() for c in columns.split(",")]
            r = cdp.evaluate(f"""
                (function() {{
                    var targets = {json.dumps(col_list)};
                    var clicked = [];
                    var labels = document.querySelectorAll("label.ant-checkbox-wrapper");
                    for (var i = 0; i < labels.length; i++) {{
                        var text = (labels[i].textContent || "").trim();
                        if (targets.indexOf(text) !== -1) {{
                            var cb = labels[i].querySelector(".ant-checkbox");
                            var isChecked = cb && cb.classList.contains("ant-checkbox-checked");
                            if (!isChecked) labels[i].click();
                            clicked.push(text);
                        }}
                    }}
                    return JSON.stringify({{ok: clicked.length > 0, clicked: clicked}});
                }})()
            """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def export_chart(format_type: str = "all", port: int = CDP_PORT) -> Dict[str, Any]:
    """Export the chart on the Export page.

    format_type: "all", "image", "data", "code", or "config".
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    try:
        if format_type == "all":
            r = cdp.evaluate("""
                (function() {
                    var buttons = document.querySelectorAll("button");
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.trim() === "全部导出") {
                            buttons[i].click();
                            return JSON.stringify({ok: true, clicked: "全部导出"});
                        }
                    }
                    return JSON.stringify({ok: false, error: "全部导出 button not found"});
                })()
            """)
        elif format_type == "code":
            r = cdp.evaluate("""
                (function() {
                    var buttons = document.querySelectorAll("button");
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.trim().includes("复制代码")) {
                            buttons[i].click();
                            return JSON.stringify({ok: true, clicked: "复制代码"});
                        }
                    }
                    return JSON.stringify({ok: false, error: "复制代码 button not found"});
                })()
            """)
        else:
            section_map = {"image": "图片", "data": "数据", "config": "配置文件"}
            section_name = section_map.get(format_type, format_type)
            r = cdp.evaluate(f"""
                (function() {{
                    var headings = document.querySelectorAll("h3");
                    for (var i = 0; i < headings.length; i++) {{
                        if (headings[i].textContent.trim() === {json.dumps(section_name)}) {{
                            var section = headings[i].parentElement || headings[i].closest("div");
                            if (section) {{
                                var btn = section.querySelector("button") || section.parentElement.querySelector("button");
                                if (btn) {{
                                    btn.click();
                                    return JSON.stringify({{ok: true, section: {json.dumps(section_name)}, clicked: btn.textContent.trim()}});
                                }}
                            }}
                        }}
                    }}
                    return JSON.stringify({{ok: false, error: "Section not found: " + {json.dumps(section_name)}}});
                }})()
            """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_code(port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract the generated G2Plot code from the Export page's <code> block."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var codeEl = document.querySelector("pre code");
                if (!codeEl) {
                    return JSON.stringify({ok: false, error: "No code block found. Navigate to the Export page first."});
                }
                return JSON.stringify({ok: true, code: codeEl.textContent.trim()});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_config(port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract the generated chart config JSON from the Export page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var pres = document.querySelectorAll("pre code");
                if (pres.length < 2) {
                    return JSON.stringify({ok: false, error: "Config block not found. Navigate to the Export page first."});
                }
                return JSON.stringify({ok: true, config: pres[1].textContent.trim()});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def toggle_option(option_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Toggle a checkbox option on the Make page (e.g. '平滑', '显示点', '显示标签')."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var labels = document.querySelectorAll("label");
                for (var i = 0; i < labels.length; i++) {{
                    if (labels[i].textContent.trim() === {json.dumps(option_name)}) {{
                        var cb = labels[i].querySelector("input[type='checkbox']");
                        if (cb) {{
                            var was = cb.checked;
                            cb.click();
                            return JSON.stringify({{ok: true, option: {json.dumps(option_name)},
                                                    was: was, now: !was}});
                        }}
                        labels[i].click();
                        return JSON.stringify({{ok: true, option: {json.dumps(option_name)},
                                                method: "label_click"}});
                    }}
                }}
                return JSON.stringify({{ok: false, error: "Option not found: " + {json.dumps(option_name)}}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_title(title: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set the chart title on the Make page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var inputs = document.querySelectorAll("input[type='text']");
                for (var i = 0; i < inputs.length; i++) {{
                    var rect = inputs[i].getBoundingClientRect();
                    if (rect.y > 230 && rect.y < 260) {{
                        var nativeSet = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        nativeSet.call(inputs[i], {json.dumps(title)});
                        inputs[i].dispatchEvent(new Event('input', {{bubbles: true}}));
                        inputs[i].dispatchEvent(new Event('change', {{bubbles: true}}));
                        return JSON.stringify({{ok: true, title: {json.dumps(title)}}});
                    }}
                }}
                return JSON.stringify({{ok: false, error: "Title input not found"}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_canvas_size(width: int, height: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set the canvas size on the Make page.
    Targets the first two ant-input-number-input elements (width, height)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var inputs = document.querySelectorAll("input.ant-input-number-input");
                if (inputs.length < 2)
                    return JSON.stringify({{ok: false,
                        error: "Expected >=2 number inputs, found " + inputs.length}});
                var set = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                set.call(inputs[0], String({width}));
                inputs[0].dispatchEvent(new Event('input', {{bubbles: true}}));
                inputs[0].dispatchEvent(new Event('change', {{bubbles: true}}));
                set.call(inputs[1], String({height}));
                inputs[1].dispatchEvent(new Event('input', {{bubbles: true}}));
                inputs[1].dispatchEvent(new Event('change', {{bubbles: true}}));
                return JSON.stringify({{ok: true, width: {width}, height: {height}}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_chart(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click '立即制作图表' button from the home page to enter the wizard."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var buttons = document.querySelectorAll("button");
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].textContent.trim().includes("立即制作图表")) {
                        buttons[i].click();
                        return JSON.stringify({ok: true});
                    }
                }
                return JSON.stringify({ok: false, error: "Button not found"});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def export_all(port: int = CDP_PORT) -> Dict[str, Any]:
    """Click the '全部导出' (Export All) button on the Export page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if ((buttons[i].textContent || '').includes('全部导出')) {
                        buttons[i].click();
                        return JSON.stringify({ok: true, clicked: '全部导出'});
                    }
                }
                return JSON.stringify({ok: false, error: '全部导出 button not found'});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_chart_types(port: int = CDP_PORT) -> Dict[str, Any]:
    """List all chart categories and types on the Guide page.
    Must be on /guide (Step 2) for this to work."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var h2s = document.querySelectorAll("h2");
                var h3s = document.querySelectorAll("h3");
                var categories = [];
                for (var i = 0; i < h2s.length; i++) {
                    var t = h2s[i].textContent.trim();
                    if (t.includes("类")) categories.push(t);
                }
                var charts = [];
                var seen = {};
                var skipNames = {"基础产品":1,"拓展产品":1,"周边生态":1,"别名":1,"定义":1,
                                 "图表血缘":1,"视觉通道":1,"分析目的":1,"数据准备":1};
                for (var i = 0; i < h3s.length; i++) {
                    var t = h3s[i].textContent.trim();
                    var rect = h3s[i].getBoundingClientRect();
                    if (rect.x > 30 && rect.x < 900 && t.length > 1 && t.length < 20
                        && !seen[t] && !skipNames[t]) {
                        seen[t] = true;
                        charts.push(t);
                    }
                }
                return JSON.stringify({ok: true, categories: categories, charts: charts,
                                       count: charts.length});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_description(desc: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set the chart description on the Make page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate(f"""
            (function() {{
                var inputs = document.querySelectorAll("input.ant-input.ant-input-sm");
                if (inputs.length >= 2) {{
                    var nativeSet = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeSet.call(inputs[1], {json.dumps(desc)});
                    inputs[1].dispatchEvent(new Event('input', {{bubbles: true}}));
                    inputs[1].dispatchEvent(new Event('change', {{bubbles: true}}));
                    return JSON.stringify({{ok: true, description: {json.dumps(desc)}}});
                }}
                return JSON.stringify({{ok: false, error: "Description input not found"}});
            }})()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def scan_elements(port: int = CDP_PORT) -> Dict[str, Any]:
    """Scan the current page for interactive elements (buttons, inputs, selects)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var result = {ok: true, elements: []};
                var selectors = 'button, input, select, [role="button"], [role="tab"], [role="radio"], [role="checkbox"], .ant-radio-wrapper, .ant-checkbox-wrapper, .ant-select, .ant-tabs-tab';
                var els = document.querySelectorAll(selectors);
                for (var i = 0; i < Math.min(els.length, 50); i++) {
                    var el = els[i];
                    var rect = el.getBoundingClientRect();
                    if (rect.width === 0 && rect.height === 0) continue;
                    result.elements.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || el.getAttribute('role') || '',
                        text: (el.textContent || el.value || '').trim().substring(0, 60),
                        className: (el.className || '').toString().substring(0, 80),
                        id: el.id || '',
                        rect: {x: Math.round(rect.x), y: Math.round(rect.y),
                               w: Math.round(rect.width), h: Math.round(rect.height)}
                    });
                }
                result.count = result.elements.length;
                return JSON.stringify(result);
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
