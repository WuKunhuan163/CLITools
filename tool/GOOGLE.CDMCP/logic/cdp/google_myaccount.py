"""Google My Account page automation via CDP.

Provides structured access to myaccount.google.com sub-pages:
- Personal Info (name, email, phone, birthday, language, addresses)
- Security (2FA, devices, recent activity, passwords)
- Data & Privacy (activity controls, ad settings, app permissions)
- People & Sharing (contacts, blocked users, location sharing)

All operations require an active Google login. Use check_login_required()
before calling any function.
"""

import json
import time
from typing import Any, Dict, List, Optional

from logic.chrome.session import CDPSession, list_tabs, CDP_PORT

_MYACCOUNT_URL = "https://myaccount.google.com"

_PAGES = {
    "home": _MYACCOUNT_URL,
    "personal-info": f"{_MYACCOUNT_URL}/personal-info",
    "security": f"{_MYACCOUNT_URL}/security",
    "data-privacy": f"{_MYACCOUNT_URL}/data-and-privacy",
    "people-sharing": f"{_MYACCOUNT_URL}/people-and-sharing",
    "payments": f"{_MYACCOUNT_URL}/payments-and-subscriptions",
}


def check_login_required(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check if user is signed in to Google. Returns {"ok": bool, "error": str}."""
    from pathlib import Path
    identity_file = Path(__file__).resolve().parent.parent.parent / "data" / "sessions" / "google_identity.json"
    if identity_file.exists():
        try:
            with open(identity_file) as f:
                identity = json.load(f)
            if identity.get("email"):
                return {"ok": True, "email": identity["email"],
                        "display_name": identity.get("display_name")}
        except Exception:
            pass
    return {"ok": False, "error": "Not signed in. Run CDMCP --mcp-login first."}


def _get_myaccount_cdp(session, port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get or create a CDP session to a myaccount.google.com tab."""
    tab_info = session.require_tab(
        label="myaccount",
        url_pattern="myaccount.google.com",
        open_url=_MYACCOUNT_URL,
        auto_lock=True,
    )
    if not tab_info:
        return None
    ws = tab_info.get("ws", "")
    if not ws:
        for t in list_tabs(port):
            if t.get("id") == tab_info.get("id"):
                ws = t.get("webSocketDebuggerUrl", "")
                break
    if not ws:
        return None
    return CDPSession(ws, timeout=10)


def _navigate_to(cdp: CDPSession, page_key: str) -> bool:
    """Navigate the myaccount tab to a specific sub-page."""
    url = _PAGES.get(page_key, "")
    if not url:
        return False
    current = cdp.evaluate("window.location.href") or ""
    if page_key != "home" and page_key in current:
        return True
    cdp.send_and_recv("Page.enable", {})
    cdp.send_and_recv("Page.navigate", {"url": url})
    time.sleep(2)
    return True


def get_profile(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract profile info: name, email(s), phone, birthday, language, addresses."""
    result = {"ok": False}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    _navigate_to(cdp, "personal-info")
    time.sleep(1)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var lines = text.split('\\n').map(function(l){ return l.trim(); }).filter(Boolean);
    var profile = {};
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        var next = i + 1 < lines.length ? lines[i + 1] : '';
        if (line === '名稱' || line === 'Name') profile.name = next;
        if (line === '性別' || line === 'Gender') profile.gender = next;
        if (line === '生日' || line === 'Birthday') profile.birthday = next;
        if (line === '語言' || line === 'Language') profile.language = next;
        if (line === '電郵' || line === 'Email') {
            var emails = [];
            for (var j = i + 1; j < Math.min(i + 5, lines.length); j++) {
                if (lines[j].indexOf('@') >= 0) emails.push(lines[j]);
                else break;
            }
            profile.emails = emails;
        }
        if (line === '電話' || line === 'Phone') {
            if (next && !next.match(/^[A-Z]/)) profile.phone = next;
        }
    }
    return JSON.stringify(profile);
})()
""") or "{}"

    try:
        profile = json.loads(data)
        result.update(profile)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse profile data"

    cdp.close()
    return result


def get_security_overview(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract security overview: 2FA, devices, recent activity, recovery options."""
    result = {"ok": False}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    _navigate_to(cdp, "security")
    time.sleep(1)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var info = {};
    if (text.indexOf('兩步驗證功能已關閉') >= 0 || text.indexOf('2-Step Verification is off') >= 0)
        info.two_factor = 'off';
    else if (text.indexOf('兩步驗證') >= 0 || text.indexOf('2-Step Verification') >= 0)
        info.two_factor = 'on';
    var pwMatch = text.match(/密碼.*?變更[：:]\s*(.+?)\\n|Password.*?changed[：:]\s*(.+?)\\n/);
    if (pwMatch) info.password_last_changed = (pwMatch[1] || pwMatch[2] || '').trim();
    info.has_security_alerts = text.indexOf('安全提示') >= 0 || text.indexOf('security') >= 0;
    var deviceMatch = text.match(/(\\d+)\\s*個工作階段|(\\d+)\\s*session/);
    if (deviceMatch) info.active_sessions = parseInt(deviceMatch[1] || deviceMatch[2]);
    return JSON.stringify(info);
})()
""") or "{}"

    try:
        info = json.loads(data)
        result.update(info)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse security data"

    cdp.close()
    return result


def get_recent_activity(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """Extract recent security activity entries."""
    result = {"ok": False, "activities": []}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    _navigate_to(cdp, "security")
    time.sleep(1)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var lines = text.split('\\n').map(function(l){ return l.trim(); }).filter(Boolean);
    var activities = [];
    var inActivity = false;
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].indexOf('最近的安全性活動') >= 0 || lines[i].indexOf('Recent security activity') >= 0) {
            inActivity = true;
            continue;
        }
        if (inActivity) {
            if (lines[i].indexOf('查看安全性活動') >= 0 || lines[i].indexOf('Review security') >= 0) break;
            if (lines[i].length > 5 && lines[i].length < 100) {
                activities.push(lines[i]);
            }
        }
    }
    return JSON.stringify(activities.slice(0, 10));
})()
""") or "[]"

    try:
        result["activities"] = json.loads(data)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse activity data"

    cdp.close()
    return result


def get_connected_apps(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """List third-party apps connected to the Google account."""
    result = {"ok": False, "apps": []}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    cdp.send_and_recv("Page.enable", {})
    cdp.send_and_recv("Page.navigate", {
        "url": f"{_MYACCOUNT_URL}/connections"
    })
    time.sleep(3)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var lines = text.split('\\n').map(function(l){ return l.trim(); }).filter(Boolean);
    var apps = [];
    var inApps = false;
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].indexOf('有權存取你帳戶的第三方應用') >= 0 ||
            lines[i].indexOf('Third-party apps with account access') >= 0) {
            inApps = true; continue;
        }
        if (inApps && lines[i].length > 2 && lines[i].length < 60 &&
            lines[i] !== '搜尋 Google 帳戶' && lines[i] !== '取得協助') {
            apps.push(lines[i]);
        }
    }
    return JSON.stringify(apps.slice(0, 20));
})()
""") or "[]"

    try:
        result["apps"] = json.loads(data)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse apps data"

    cdp.close()
    return result


def get_devices(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """List devices signed in to the Google account."""
    result = {"ok": False, "devices": []}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    cdp.send_and_recv("Page.enable", {})
    cdp.send_and_recv("Page.navigate", {
        "url": f"{_MYACCOUNT_URL}/device-activity"
    })
    time.sleep(3)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var lines = text.split('\\n').map(function(l){ return l.trim(); }).filter(Boolean);
    var devices = [];
    for (var i = 0; i < lines.length; i++) {
        if ((lines[i].indexOf('Mac') >= 0 || lines[i].indexOf('Windows') >= 0 ||
             lines[i].indexOf('iPhone') >= 0 || lines[i].indexOf('Android') >= 0 ||
             lines[i].indexOf('Linux') >= 0 || lines[i].indexOf('Chrome') >= 0) &&
            lines[i].length < 60) {
            devices.push(lines[i]);
        }
    }
    return JSON.stringify(devices.slice(0, 10));
})()
""") or "[]"

    try:
        result["devices"] = json.loads(data)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse devices data"

    cdp.close()
    return result


def get_storage_usage(session, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Google account storage usage (Drive, Gmail, Photos)."""
    result = {"ok": False}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    cdp.send_and_recv("Page.enable", {})
    cdp.send_and_recv("Page.navigate", {
        "url": "https://one.google.com/storage"
    })
    time.sleep(3)

    data = cdp.evaluate("""
(function(){
    var text = document.body.innerText;
    var storage = {};
    var m = text.match(/(\\d+(?:\\.\\d+)?\\s*(?:GB|MB|TB|KB)).*?(?:of|\\/).*?(\\d+(?:\\.\\d+)?\\s*(?:GB|MB|TB|KB))/i);
    if (m) { storage.used = m[1]; storage.total = m[2]; }
    return JSON.stringify(storage);
})()
""") or "{}"

    try:
        info = json.loads(data)
        result.update(info)
        result["ok"] = True
    except Exception:
        result["error"] = "Failed to parse storage data"

    cdp.close()
    return result


def navigate_page(session, page: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate the myaccount tab to a named page. Returns page content summary."""
    if page not in _PAGES:
        return {"ok": False, "error": f"Unknown page '{page}'. Available: {list(_PAGES.keys())}"}

    result = {"ok": False}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    _navigate_to(cdp, page)
    time.sleep(1)

    title = cdp.evaluate("document.title") or ""
    url = cdp.evaluate("window.location.href") or ""
    text = cdp.evaluate("document.body.innerText.substring(0, 500)") or ""

    result.update({
        "ok": True,
        "page": page,
        "title": title,
        "url": url,
        "summary": text[:300],
    })
    cdp.close()
    return result


def change_language(session, language_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to the language settings page. Requires manual selection."""
    result = {"ok": False}
    cdp = _get_myaccount_cdp(session, port)
    if not cdp:
        result["error"] = "Could not open myaccount tab"
        return result

    cdp.send_and_recv("Page.enable", {})
    cdp.send_and_recv("Page.navigate", {
        "url": f"{_MYACCOUNT_URL}/language"
    })
    time.sleep(2)
    result["ok"] = True
    result["message"] = f"Navigated to language settings. Current language shown in page."
    cdp.close()
    return result
