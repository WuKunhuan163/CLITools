# HTML GUI — Agent Reference

## Overview

HTML-based GUI blueprints served as local HTTP/WebSocket servers.
Alternative to tkinter blueprints — works in any Python environment, opens in Chrome.

## Available Blueprints

- `blueprint/chatbot/` — Multi-session chatbot with sidebar, message bubbles, WebSocket

## Usage Pattern

```python
from logic.gui.html.blueprint.chatbot.server import ChatbotServer

server = ChatbotServer(title="My Tool", on_send=handler, session_provider=sessions)
server.start()          # Starts HTTP + WS servers in background
server.open_browser()   # Opens in Chrome via CDMCP
```

## Dependencies

- `websockets` (optional — falls back to HTTP polling)
- No npm/node/build step required
