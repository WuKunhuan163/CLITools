"""Vendor-specific provider configurations.

Each vendor module defines shared constants (API_URL, CONFIG_VENDOR, CONFIG_KEY_ENV)
and optional vendor-specific logic (key validation, display name). Model providers
import from here to avoid duplicating vendor details.

Usage:
    from tool.LLM.logic.providers import baidu
    class MyBaiduModel(OpenAICompatProvider):
        API_URL = baidu.API_URL
        CONFIG_VENDOR = baidu.CONFIG_VENDOR
        ...
"""
from tool.LLM.logic.providers import (
    baidu, google, nvidia, siliconflow, tencent, zhipu
)

VENDORS = {
    "baidu": baidu,
    "google": google,
    "nvidia": nvidia,
    "siliconflow": siliconflow,
    "tencent": tencent,
    "zhipu": zhipu,
}


def get_vendor(name: str):
    """Get a vendor module by name."""
    return VENDORS.get(name)


def vendor_display_name(name: str) -> str:
    """Get the display name for a vendor, with correct capitalization."""
    v = VENDORS.get(name)
    if v and hasattr(v, "DISPLAY_NAME"):
        return v.DISPLAY_NAME
    return name.capitalize()
