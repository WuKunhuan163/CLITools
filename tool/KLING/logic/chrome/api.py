"""Kling AI operations via CDMCP (Chrome DevTools MCP).

Uses the authenticated ``klingai.com`` session via CDP (port 9222).
Auth state and basic page info are read from localStorage/URL.
DOM scraping functions (get_points, get_generation_history) are disabled
due to ToS concerns. Use the official Kling AI API instead.

# TODO: Migrate to Kling AI official API (https://docs.qingque.cn/d/home/eZQCUXCd2RS3MFEzfR6Vc8ADRnx)
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
)

KLING_URL_PATTERN = "klingai.com"

# TODO: Migrate to Kling AI official API for credits and generation history.
_TOS_ERR = "Disabled: DOM scraping may violate Kling ToS. Use Kling AI official API instead."


def find_kling_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Kling AI app tab in Chrome."""
    return find_tab(KLING_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_kling_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_user_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Kling AI user info from localStorage."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Kling AI tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var user = JSON.parse(localStorage.getItem("klingai_user") || "{}");
                    if (!user.id) user = JSON.parse(localStorage.getItem("user") || "{}");
                    var userId = document.cookie.split(";").map(c => c.trim())
                        .find(c => c.startsWith("userId="));
                    var uid = userId ? userId.split("=")[1] : null;
                    return JSON.stringify({
                        ok: true,
                        data: {
                            userId: uid || user.id || user.userId,
                            userName: user.nickname || user.userName || null,
                            email: user.email || user.userEmail || null,
                            avatar: user.avatar || (user.userAvatars || [])[0] || null
                        }
                    });
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_points(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get credit points. DISABLED: violates Kling ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current Kling page state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Kling AI tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var nav = document.querySelector("nav, [class*=sidebar]");
                var activeItem = nav ? nav.querySelector("[class*=active], [aria-selected=true]") : null;
                var activePage = activeItem ? activeItem.textContent.trim() : "";
                return JSON.stringify({ok: true, url: url, title: title, activePage: activePage});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_generation_history(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get generation history. DISABLED: violates Kling ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}
