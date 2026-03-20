# Chatbot Blueprint - Agent Guide

## Core Concepts

`ChatbotWindow` is a multi-session chat GUI with sidebar navigation. It extends `BaseGUIWindow` and provides a reusable chat interface that any tool can use for conversational workflows.

## Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | str | Window title (shown in sidebar header) |
| `timeout` | int | Auto-close seconds (0 = no timeout) |
| `internal_dir` | str | Localization directory |
| `tool_name` | str | Tool identifier for instance registry |
| `on_send` | Callable(session_id, text) | Callback when user sends a message |
| `session_provider` | object | Session management object (see below) |
| `colors` | Dict | Optional color overrides |
| `fonts` | Dict | Optional font overrides |
| `window_size` | str | Tkinter geometry (default "1100x700") |
| `focus_interval` | int | Seconds between focus/bell (default 0) |

## Session Provider Interface

The `session_provider` must implement:
- `list_sessions()` -> List of session objects with `.id`, `.get_display_title()`, `.status`, `.messages`
- `create_session()` -> Session object
- `get_session(id)` -> Session or None
- `add_message(id, role, content)` -> None
- `update_title(id, title)` -> None
- `complete_session(id)` -> None
- `delete_session(id)` -> None

## External Control Commands

| Method | Description |
|--------|-------------|
| `cmd_create_session()` | Create and switch to new session, returns ID |
| `cmd_send_message(text)` | Send message in current session |
| `cmd_get_status()` | Return session_id, pipeline_running, status_text |
| `cmd_list_sessions()` | Return list of {id, title, status} dicts |
| `cmd_switch_session(id)` | Switch to session by ID |
| `cmd_get_messages()` | Return messages for current session |
| `cmd_stop_pipeline()` | Request pipeline stop |

## Thread-Safe Update Methods

These are called from background threads (e.g., pipeline):
- `append_message(role, content)` — Add message bubble
- `set_status(text)` — Update status bar
- `set_pipeline_running(bool)` — Track pipeline state
- `update_session_title(session_id, title)` — Update sidebar title

## Result Format (Interface I)

On close: `{"status": "...", "data": {"session_id": "...", "pipeline_running": bool, "sessions": [...]}}`

## Gotchas

- `on_send` is called on the main thread. Start pipelines in background threads.
- `session_provider` is required for session persistence. Without it, sessions are in-memory only.
- SF Pro fonts (macOS); fallback to system fonts on other platforms.
