# BILIBILI Logic

Bilibili video platform automation via CDMCP. Session-based tool with state machine tracking for `bilibili.com`.

## Structure

| Module | Purpose |
|--------|---------|
| `chrome/api.py` | CDP-based operations — session boot, video playback, danmaku, live streaming, creative center, privacy settings |
| `chrome/state_machine.py` | FSM tracking session lifecycle and recovery |

## Key API Functions (70 total)

Core: `boot_session()`, `get_session_status()`, `get_mcp_state()`, `get_auth_state()`, `get_page_info()`, `take_screenshot()`

Video playback, danmaku, live streaming, creative center, privacy settings.
