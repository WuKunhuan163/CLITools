"""Kling AI operations via Chrome DevTools Protocol.

Uses the authenticated ``app.klingai.com`` session.  User data is read
from ``localStorage`` and DOM elements since the Kling API gateway
(``api-app-global.klingai.com``) blocks cross-origin fetch from the app
domain.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

KLING_URL_PATTERN = "app.klingai.com"


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
                    var user = JSON.parse(localStorage.getItem("user") || "{}");
                    var userId = document.cookie.split(";").map(c => c.trim())
                        .find(c => c.startsWith("userId="));
                    var uid = userId ? userId.split("=")[1] : user.userId;
                    return JSON.stringify({
                        ok: true,
                        data: {
                            userId: uid || user.userId,
                            userName: user.userName,
                            email: user.userEmail,
                            avatar: (user.userAvatars || [])[0] || null,
                            introduction: user.introduction || ""
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
    """Get Kling AI credit points from DOM."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Kling AI tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var pointBox = document.querySelector("[class*=point-box], [class*=pointBox]");
                    var points = pointBox ? pointBox.textContent.trim() : null;

                    var subEl = document.querySelector("[class*=subscribe], [class*=membership], [class*=plan]");
                    var plan = subEl ? subEl.textContent.trim().substring(0, 50) : null;

                    return JSON.stringify({ok: true, data: {points: points, plan: plan}});
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
    """Read generation history from the Assets page DOM.

    Navigates to the assets page if not already there, then reads
    visible generation items.
    """
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Kling AI tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var items = document.querySelectorAll(
                    "[class*=asset-card], [class*=work-card], [class*=creation-item], [class*=task-item]"
                );
                var results = Array.from(items).slice(0, 20).map(el => ({
                    text: el.textContent.trim().substring(0, 100),
                    hasVideo: !!el.querySelector("video"),
                    hasImage: !!el.querySelector("img")
                }));
                return JSON.stringify({ok: true, count: results.length, items: results});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
