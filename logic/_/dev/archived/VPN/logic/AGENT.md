# VPN Logic — Technical Reference

## engine.py — VpnEngine

```python
VpnEngine()
```

Paths:
- `tool_dir`: `tool/VPN/`
- `data_dir`: `tool/VPN/data/`
- `bin_dir`: `tool/VPN/data/bin/` — VPN client binary

Operations:
- Start/stop VPN connection
- Manage configuration files
- Monitor connection status
- Signal handling for clean shutdown

## Gotchas

1. **Binary in data/bin/**: VPN client executable is stored in `data/bin/`, not system PATH.
2. **Signal handling**: Uses `signal` module for clean process termination.
