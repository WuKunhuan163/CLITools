"""Timezone detection and resolution utilities."""
import re


def get_current_timezone():
    """Detect current timezone based on IP if possible, otherwise return configured or UTC."""
    try:
        import requests
        res = requests.get("http://ip-api.com/json/", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "success":
                return data.get("timezone", "UTC")
    except:
        pass
    
    from logic.config import get_global_config
    return get_global_config("timezone", "UTC")

def resolve_timezone(tz_input=None):
    """
    Resolves a timezone input into a (tz_object, display_name).
    tz_input can be:
    - None or "AUTO": detect via IP
    - "UTC+X" or "GMT-X"
    - City names (Beijing, Tokyo, etc.)
    - IANA names (Asia/Shanghai)
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime, timezone as py_timezone, timedelta
    
    manual_mapping = {
        "Beijing": "Asia/Shanghai",
        "Chongqing": "Asia/Shanghai",
        "Harbin": "Asia/Shanghai",
        "Taipei": "Asia/Taipei",
        "Hong_Kong": "Asia/Hong_Kong",
        "Macau": "Asia/Macau",
    }
    
    tz_name = tz_input or "AUTO"
    if tz_name.upper() == "AUTO":
        tz_name = get_current_timezone()
    
    if tz_name in manual_mapping:
        tz_name = manual_mapping[tz_name]
    
    utc_match = re.match(r'^(?:UTC|GMT)([+-]\d+)$', tz_name, re.IGNORECASE)
    
    target_tz = None
    display_name = tz_name
    
    if utc_match:
        offset = int(utc_match.group(1))
        target_tz = py_timezone(timedelta(hours=offset))
        display_name = f"UTC{'+' if offset >= 0 else ''}{offset}"
    else:
        try:
            target_tz = ZoneInfo(tz_name)
        except Exception:
            try:
                import pytz
                found = None
                for zone in pytz.all_timezones:
                    if zone.split('/')[-1].lower() == tz_name.lower():
                        found = zone
                        break
                if found:
                    target_tz = ZoneInfo(found)
                    display_name = found
                else:
                    raise Exception("Not found")
            except Exception:
                target_tz = py_timezone.utc
                display_name = "UTC"
            
    now = datetime.now(target_tz)
    offset_total_seconds = int(now.utcoffset().total_seconds())
    offset_hours = offset_total_seconds // 3600
    offset_str = f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours}"
    
    full_display = f"{display_name} ({offset_str})"
    return target_tz, full_display
