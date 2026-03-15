"""Google Scholar operations via CDMCP (Chrome DevTools MCP).

Uses standard CDMCP interfaces (via cdmcp_loader) for:
  - Session management (boot_tool_session / require_tab)
  - Visual overlays (badge, lock, focus, favicon)
  - MCP interaction effects (mcp_click, mcp_type, mcp_navigate)

Operations:
  - Session: boot / status / state
  - Search: search papers, get results
  - Navigation: next/prev page, open paper, open profile
  - Filters: time range, sort order, type
  - Actions: save, cite, cited-by, related, PDF
  - Profile: view author profile, get publications
  - Library: view saved papers
"""

import json
import time
import urllib.parse
import importlib.util as _ilu
from pathlib import Path
from typing import Dict, Any, Optional, List

from interface.chrome import CDPSession, CDP_PORT, capture_screenshot
from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_interact,
)

_SM_PATH = Path(__file__).resolve().parent / "state_machine.py"
_sm_spec = _ilu.spec_from_file_location("gs_state_machine", str(_SM_PATH))
_sm_mod = _ilu.module_from_spec(_sm_spec)
_sm_spec.loader.exec_module(_sm_mod)
GSState = _sm_mod.GSState
get_machine = _sm_mod.get_machine

GS_URL_PATTERN = "scholar.google"
GS_HOME = "https://scholar.google.com/"
TOOL_NAME = "GOOGLE.GS"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _TOOL_DIR / "data"


def _overlay():
    return load_cdmcp_overlay()


def _sessions():
    return load_cdmcp_sessions()


def _interact():
    return load_cdmcp_interact()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_session = None
_session_name = "scholar"


def _get_or_create_session(port: int = CDP_PORT):
    global _session
    if _session is not None:
        try:
            cdp = _session.get_cdp()
            if cdp:
                return _session
        except Exception:
            pass
        _session = None
    sm = _sessions()
    existing = sm.get_session(_session_name)
    if existing:
        try:
            cdp = existing.get_cdp()
            if cdp:
                _session = existing
                return _session
        except Exception:
            pass
    return None


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Ensure CDMCP session and Scholar tab exist. Returns CDPSession or None."""
    session = _get_or_create_session(port)
    if not session:
        result = boot_session(port=port)
        if not result.get("ok"):
            return None
        session = _get_or_create_session(port)
        if not session:
            return None

    tab = session.require_tab("scholar", url_pattern=GS_URL_PATTERN,
                              open_url=GS_HOME, auto_open=True, wait_sec=10)
    if not tab or not tab.get("ws"):
        return None

    cdp = CDPSession(tab["ws"], timeout=15)
    ov = _overlay()
    try:
        if not ov.is_locked(cdp):
            ov.inject_badge(cdp, text=f"GS [{session.session_id[:8]}]", color="#4285f4")
            ov.inject_lock(cdp, tool_name=TOOL_NAME)
    except Exception:
        pass
    return cdp


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    global _session
    sm = _sessions()
    machine = get_machine(_session_name)
    machine.transition(GSState.BOOTING)

    result = sm.boot_tool_session(_session_name, timeout_sec=86400,
                                  idle_timeout_sec=3600, port=port)
    if not result.get("ok"):
        machine.transition(GSState.ERROR, {"error": result.get("error", "Boot failed")})
        return result

    _session = result.get("session")
    machine.transition(GSState.IDLE)
    return result


def get_mcp_state(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    state = machine.to_dict()

    cdp = _ensure_session(port)
    if cdp:
        try:
            url = cdp.evaluate("window.location.href") or ""
            title = cdp.evaluate("document.title") or ""
            result_count = cdp.evaluate(
                "document.querySelector('#gs_ab_md .gs_ab_mdw')?.textContent?.trim() || ''"
            ) or ""
            state["page"] = {"url": url, "title": title, "result_info": result_count}
        except Exception:
            pass
        finally:
            cdp.close()
    return state


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(query: str, year_from: int = 0, year_to: int = 0,
           port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    machine.transition(GSState.SEARCHING, {"query": query})

    url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(query)}&hl=en"
    if year_from:
        url += f"&as_ylo={year_from}"
    if year_to:
        url += f"&as_yhi={year_to}"

    cdp = _ensure_session(port)
    if not cdp:
        machine.transition(GSState.ERROR, {"error": "No session"})
        return {"ok": False, "error": "No session"}

    interact = _interact()
    interact.mcp_navigate(cdp, url, wait_selector=".gs_r", timeout=10, tool_name=TOOL_NAME)
    time.sleep(1)

    machine.set_url(url)
    results = _extract_results(cdp)

    machine.transition(GSState.IDLE)
    cdp.close()
    return {"ok": True, "query": query, "results": results, "count": len(results)}


def get_results(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    results = _extract_results(cdp)
    cdp.close()
    return {"ok": True, "results": results, "count": len(results)}


def _extract_results(cdp: CDPSession) -> List[Dict[str, Any]]:
    r = cdp.evaluate('''
    (function(){
        var results = document.querySelectorAll('.gs_r.gs_or.gs_scl');
        var out = [];
        for(var i=0; i<results.length; i++){
            var el = results[i];
            var titleEl = el.querySelector('.gs_rt');
            var titleLink = titleEl ? titleEl.querySelector('a') : null;
            var authors = el.querySelector('.gs_a');
            var snippet = el.querySelector('.gs_rs');
            var links = el.querySelectorAll('.gs_fl a');
            var cited = '', citedHref = '', relatedHref = '', versionsText = '';
            for(var j=0;j<links.length;j++){
                var t = links[j].textContent;
                if(t.match(/Cited by/)){
                    cited = t; citedHref = links[j].href;
                } else if(t.match(/Related/)){
                    relatedHref = links[j].href;
                } else if(t.match(/All \\d+ version/)){
                    versionsText = t;
                }
            }
            var pdfEl = el.querySelector('.gs_or_ggsm a, .gs_ggs a');
            out.push({
                index: i,
                title: titleEl ? titleEl.textContent.trim() : '',
                link: titleLink ? titleLink.href : '',
                authors: authors ? authors.textContent.trim() : '',
                snippet: snippet ? snippet.textContent.trim().substring(0,200) : '',
                cited: cited,
                cited_href: citedHref,
                related_href: relatedHref,
                versions: versionsText,
                pdf_url: pdfEl ? pdfEl.href : '',
                pdf_label: pdfEl ? pdfEl.textContent.trim() : '',
            });
        }
        return JSON.stringify(out);
    })()
    ''')
    try:
        return json.loads(r)
    except (json.JSONDecodeError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def next_page(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    interact.mcp_click(cdp, '#gs_n td:last-child a, .gs_ico_nav_next',
                       label="Next page", tool_name=TOOL_NAME)
    time.sleep(2)
    results = _extract_results(cdp)
    url = cdp.evaluate("window.location.href") or ""
    get_machine(_session_name).set_url(url)
    cdp.close()
    return {"ok": True, "results": results, "count": len(results)}


def prev_page(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    interact.mcp_click(cdp, '#gs_n td:first-child a, .gs_ico_nav_previous',
                       label="Previous page", tool_name=TOOL_NAME)
    time.sleep(2)
    results = _extract_results(cdp)
    url = cdp.evaluate("window.location.href") or ""
    get_machine(_session_name).set_url(url)
    cdp.close()
    return {"ok": True, "results": results, "count": len(results)}


def open_paper(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    selector = f'.gs_r.gs_or.gs_scl:nth-child({index + 1}) .gs_rt a'
    result = interact.mcp_click(cdp, selector, label=f"Paper #{index}",
                                dwell=1.0, tool_name=TOOL_NAME)
    time.sleep(2)
    url = cdp.evaluate("window.location.href") or ""
    title = cdp.evaluate("document.title") or ""
    machine.set_url(url)
    machine.transition(GSState.VIEWING_PAPER, {"title": title})
    cdp.close()
    return {"ok": result.get("ok", False), "url": url, "title": title}


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def filter_time(year: str = "any", port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()

    if year == "any":
        r = cdp.evaluate('''
            (function(){
                var links = document.querySelectorAll('#gs_bdy_sb a');
                for(var i=0;i<links.length;i++){
                    if(links[i].textContent.trim()==='Any time')
                        return links[i].href;
                }
                return '';
            })()
        ''')
    else:
        r = cdp.evaluate(f'''
            (function(){{
                var links = document.querySelectorAll('#gs_bdy_sb a');
                for(var i=0;i<links.length;i++){{
                    if(links[i].textContent.trim().indexOf('Since {year}')>=0
                       || links[i].textContent.trim().indexOf('{year}')>=0)
                        return links[i].href;
                }}
                var url = window.location.href;
                var base = url.replace(/[&?]as_ylo=[^&]*/g,'').replace(/[&?]as_yhi=[^&]*/g,'');
                return base + (base.indexOf('?')>=0?'&':'?') + 'as_ylo={year}';
            }})()
        ''')

    if r:
        interact.mcp_navigate(cdp, r, tool_name=TOOL_NAME)
    time.sleep(2)
    results = _extract_results(cdp)
    cdp.close()
    return {"ok": True, "filter": f"year={year}", "results": results}


def filter_sort(order: str = "relevance", port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    target = "Sort by relevance" if order == "relevance" else "Sort by date"
    r = cdp.evaluate(f'''
        (function(){{
            var links = document.querySelectorAll('#gs_bdy_sb a');
            for(var i=0;i<links.length;i++){{
                if(links[i].textContent.trim()==='{target}')
                    return links[i].href;
            }}
            return '';
        }})()
    ''')
    if r:
        interact.mcp_navigate(cdp, r, tool_name=TOOL_NAME)
        time.sleep(2)
    results = _extract_results(cdp)
    cdp.close()
    return {"ok": True, "sort": order, "results": results}


# ---------------------------------------------------------------------------
# Per-result actions
# ---------------------------------------------------------------------------

def save_paper(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    selector = f'.gs_r.gs_or.gs_scl:nth-child({index + 1}) a.gs_or_sav'
    result = interact.mcp_click(cdp, selector, label=f"Save #{index}",
                                dwell=0.8, tool_name=TOOL_NAME)
    time.sleep(1)
    cdp.close()
    return {"ok": result.get("ok", False), "action": "save", "index": index}


def cite_paper(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    cdp.evaluate(f'''
    (function(){{
        var results = document.querySelectorAll('.gs_r.gs_or.gs_scl');
        if({index} >= results.length) return false;
        var links = results[{index}].querySelectorAll('.gs_fl a');
        for(var i=0;i<links.length;i++){{
            if(links[i].textContent.trim()==='Cite'){{
                links[i].click(); return true;
            }}
        }}
        return false;
    }})()
    ''')
    time.sleep(2)

    citations = cdp.evaluate('''
    (function(){
        var modal = document.querySelector('#gs_cit');
        if(!modal) return '{}';
        var rows = modal.querySelectorAll('.gs_citr');
        var out = {};
        for(var i=0; i<rows.length; i++){
            out['format_' + i] = rows[i].textContent.trim();
        }
        var links = modal.querySelectorAll('#gs_citi a');
        var formats = [];
        for(var i=0; i<links.length; i++){
            formats.push({name: links[i].textContent.trim(), href: links[i].href});
        }
        out['download_formats'] = formats;
        return JSON.stringify(out);
    })()
    ''')

    cdp.evaluate("document.querySelector('#gs_cit-x')?.click()")
    time.sleep(0.5)

    try:
        citation_data = json.loads(citations)
    except (json.JSONDecodeError, TypeError):
        citation_data = {}

    cdp.close()
    return {"ok": True, "action": "cite", "index": index, "citations": citation_data}


def cited_by(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    href = cdp.evaluate(f'''
    (function(){{
        var results = document.querySelectorAll('.gs_r.gs_or.gs_scl');
        if({index} >= results.length) return '';
        var links = results[{index}].querySelectorAll('.gs_fl a');
        for(var i=0;i<links.length;i++){{
            if(links[i].textContent.match(/Cited by/)) return links[i].href;
        }}
        return '';
    }})()
    ''')
    if not href:
        cdp.close()
        return {"ok": False, "error": f"No 'Cited by' link for result #{index}"}

    interact = _interact()
    interact.mcp_navigate(cdp, href, wait_selector=".gs_r", timeout=10, tool_name=TOOL_NAME)
    time.sleep(1)
    machine.set_url(href)
    machine.transition(GSState.VIEWING_CITATIONS)
    results = _extract_results(cdp)
    cdp.close()
    return {"ok": True, "action": "cited_by", "index": index,
            "results": results, "count": len(results)}


def get_pdf_url(index: int = 0, port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    r = cdp.evaluate(f'''
    (function(){{
        var results = document.querySelectorAll('.gs_r.gs_or.gs_scl');
        if({index} >= results.length) return '{{}}'
        var pdf = results[{index}].querySelector('.gs_or_ggsm a, .gs_ggs a');
        if(!pdf) return '{{}}'
        return JSON.stringify({{url: pdf.href, label: pdf.textContent.trim()}});
    }})()
    ''')
    cdp.close()
    try:
        data = json.loads(r)
        if data.get("url"):
            return {"ok": True, "index": index, **data}
        return {"ok": False, "error": f"No PDF for result #{index}"}
    except (json.JSONDecodeError, TypeError):
        return {"ok": False, "error": "Parse error"}


# ---------------------------------------------------------------------------
# Profile / Library
# ---------------------------------------------------------------------------

def open_profile(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    interact.mcp_click(cdp, "a[href*='/citations?user=']",
                       label="My profile", dwell=1.0, tool_name=TOOL_NAME)
    time.sleep(3)
    url = cdp.evaluate("window.location.href") or ""
    machine.set_url(url)
    machine.transition(GSState.VIEWING_PROFILE)
    profile = cdp.evaluate('''
    (function(){
        var name = document.querySelector('#gsc_prf_in')?.textContent?.trim() || '';
        var affiliation = document.querySelector('.gsc_prf_ila')?.textContent?.trim() || '';
        var interests = [];
        var tags = document.querySelectorAll('#gsc_prf_int a');
        for(var i=0; i<tags.length; i++) interests.push(tags[i].textContent.trim());
        var stats = {};
        var statRows = document.querySelectorAll('#gsc_rsb_st tr');
        for(var i=1; i<statRows.length; i++){
            var cells = statRows[i].querySelectorAll('td');
            if(cells.length >= 2) stats[cells[0].textContent.trim()] = cells[1].textContent.trim();
        }
        return JSON.stringify({name:name, affiliation:affiliation, interests:interests, stats:stats});
    })()
    ''')
    cdp.close()
    try:
        return {"ok": True, "profile": json.loads(profile)}
    except (json.JSONDecodeError, TypeError):
        return {"ok": True, "profile": {}}


def open_library(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _interact()
    interact.mcp_click(cdp, "a[href*='scilib=1']",
                       label="My library", dwell=1.0, tool_name=TOOL_NAME)
    time.sleep(3)
    results = _extract_results(cdp)
    cdp.close()
    return {"ok": True, "action": "library", "results": results, "count": len(results)}


def search_author(name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    url = f"https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors={urllib.parse.quote(name)}"
    interact = _interact()
    interact.mcp_navigate(cdp, url, timeout=10, tool_name=TOOL_NAME)
    time.sleep(2)
    authors = cdp.evaluate('''
    (function(){
        var cards = document.querySelectorAll('.gsc_1usr');
        var out = [];
        for(var i=0; i<cards.length; i++){
            var c = cards[i];
            var nameEl = c.querySelector('.gs_ai_name a');
            var affEl = c.querySelector('.gs_ai_aff');
            var citedEl = c.querySelector('.gs_ai_cby');
            var interestsEls = c.querySelectorAll('.gs_ai_one_int');
            var interests = [];
            for(var j=0; j<interestsEls.length; j++) interests.push(interestsEls[j].textContent.trim());
            out.push({
                name: nameEl ? nameEl.textContent.trim() : '',
                profile_url: nameEl ? nameEl.href : '',
                affiliation: affEl ? affEl.textContent.trim() : '',
                cited: citedEl ? citedEl.textContent.trim() : '',
                interests: interests
            });
        }
        return JSON.stringify(out);
    })()
    ''')
    cdp.close()
    try:
        return {"ok": True, "authors": json.loads(authors)}
    except (json.JSONDecodeError, TypeError):
        return {"ok": True, "authors": []}


def screenshot(output_path: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    img = capture_screenshot(cdp)
    cdp.close()
    if img:
        if not output_path:
            output_path = str(_DATA_DIR / "screenshot.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img)
        return {"ok": True, "path": output_path}
    return {"ok": False, "error": "Screenshot failed"}
