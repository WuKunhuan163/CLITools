# HTML Chatbot Blueprint — Agent Guide

## Overview

Web-based chatbot GUI served as a local HTTP + WebSocket server.
Drop-in replacement for the tkinter chatbot blueprint when a modern web UI is preferred.

## Quick Start

```python
from logic.gui.html.blueprint.chatbot.server import ChatbotServer

server = ChatbotServer(
    title="My Tool",
    on_send=lambda sid, text: print(f"[{sid}] {text}"),
    session_provider=my_sessions,
)
server.start()
server.open_browser()
```

## Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | "OPENCLAW" | Window/tab title |
| `port` | int | auto | HTTP server port |
| `ws_port` | int | auto | WebSocket port |
| `on_send` | Callable(sid, text) | None | User message callback |
| `session_provider` | object | None | Session CRUD interface |

## Session Provider Interface

Same as tkinter chatbot blueprint:
- `list_sessions()` -> list of session objects
- `create_session()` -> new session
- `get_session(id)` -> session or None
- `add_message(id, role, content)` -> None
- `update_title(id, title)` -> None
- `delete_session(id)` -> None

Session objects must have: `.id`, `.title` or `.get_display_title()`, `.status`, `.messages`

## External Control (from pipeline/backend)

| Method | Description |
|--------|-------------|
| `send_message_to_gui(sid, role, content)` | Push message to chat |
| `update_session_title(sid, title)` | Update sidebar title |
| `set_pipeline_running(bool)` | Toggle running indicator |
| `set_typing(bool)` | Show/hide typing dots |
| `set_status(text)` | Update status badge |
| `open_browser()` | Open in Chrome (CDMCP) or default browser |
| `stop()` | Shut down server |

## REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/status | Sessions + pipeline state |
| GET | /api/sessions/:id/messages | Messages for session |
| POST | /api/sessions | Create session |
| POST | /api/send | Send message {session_id, text} |
| DELETE | /api/sessions/:id | Delete session |

## WebSocket Protocol

Messages are JSON with `type` field:
- **Client -> Server**: `create_session`, `send_message`, `delete_session`, `stop_pipeline`
- **Server -> Client**: `sessions`, `session_created`, `message`, `title_update`, `pipeline_status`, `typing`, `status`

## Dependencies

- `websockets` (optional — falls back to HTTP polling without it)
- No npm/build step required — pure HTML/CSS/JS

## Differences from Tkinter Blueprint

- Runs in browser tab (Chrome via CDMCP or any browser)
- No Tkinter/Tcl dependency — works in any Python environment
- More styling flexibility via CSS
- External control via REST API in addition to Python methods
