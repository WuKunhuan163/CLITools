"""
WHIMSICAL Tool Interface

Provides functions for cross-tool communication.
Other tools can access this via:
    from interface import get_interface
    iface = get_interface("WHIMSICAL")
"""


def get_info():
    """Return basic tool info dict."""
    return {"name": "WHIMSICAL", "version": "1.0.0"}
