"""CLOUDFLARE Tool Interface — Cloudflare API via Chrome CDP.

Exposes Cloudflare management functions for other tools to import::

    from tool.CLOUDFLARE.interface.main import (
        find_cloudflare_tab,
        get_user,
        list_zones,
    )
"""
from tool.CLOUDFLARE.logic.chrome.api import (  # noqa: F401
    find_cloudflare_tab,
    get_user,
    get_account,
    list_zones,
    get_zone,
    list_dns_records,
    list_workers,
    list_pages_projects,
    list_kv_namespaces,
)
