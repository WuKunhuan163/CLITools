"""
LUCIDCHART Tool Interface

Provides functions for cross-tool communication.
Other tools can access this via:
    from interface import get_interface
    iface = get_interface("LUCIDCHART")
"""


def get_info():
    """Return basic tool info dict."""
    return {"name": "LUCIDCHART", "version": "1.0.0"}
