"""Vendor-specific provider configurations.

Each vendor is a directory module under providers/ containing:
  __init__.py  — shared constants (API_URL, CONFIG_VENDOR, CONFIG_KEY_ENV, etc.)
  logo.svg     — vendor logo icon
  base.py      — (optional) vendor-specific base provider class (e.g. Anthropic)

Usage:
    from tool.LLM.logic.providers import baidu
    class MyBaiduModel(OpenAICompatProvider):
        API_URL = baidu.API_URL
        CONFIG_VENDOR = baidu.CONFIG_VENDOR
        ...
"""
from tool.LLM.logic.providers import (
    anthropic, baidu, deepseek, google,
    nvidia, openai, siliconflow, tencent, zhipu,
)

VENDORS = {
    "anthropic": anthropic,
    "baidu": baidu,
    "deepseek": deepseek,
    "google": google,
    "nvidia": nvidia,
    "openai": openai,
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
