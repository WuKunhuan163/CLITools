from tool.VPN.logic.engine import VpnEngine

def get_vpn_interface():
    """Returns a stable interface for VPN functionalities."""
    engine = VpnEngine()
    return {
        "start_proxy": engine.start_proxy,
        "stop_proxy": engine.stop_proxy,
        "is_running": engine.is_running,
        "get_proxy_urls": engine.get_proxy_urls
    }
