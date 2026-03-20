"""
CHARTCUBE Tool Interface

Provides functions for cross-tool communication.
Other tools can access this via:
    from interface import get_interface
    iface = get_interface("CHARTCUBE")
"""


def get_info():
    """Return basic tool info dict."""
    return {"name": "CHARTCUBE", "version": "1.0.0"}
