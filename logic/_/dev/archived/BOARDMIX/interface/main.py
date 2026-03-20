"""
BOARDMIX Tool Interface

Provides functions for cross-tool communication.
Other tools can access this via:
    from interface import get_interface
    iface = get_interface("BOARDMIX")
"""


def get_info():
    """Return basic tool info dict."""
    return {"name": "BOARDMIX", "version": "1.0.0"}
