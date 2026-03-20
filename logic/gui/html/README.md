# HTML GUI Framework

Browser-based GUI blueprints for AITerminalTools. Each blueprint is a self-contained HTML/CSS/JS + Python server that serves a local web app.

## Directory Structure

```
html/
  __init__.py
  AGENT.md         Agent reference
  README.md            This file
  blueprint/
    chatbot/           Multi-session chatbot with sidebar
      index.html       SPA: sidebar + chat + WebSocket client
      server.py        ChatbotServer: HTTP + WebSocket bridge
      AGENT.md     Blueprint documentation
```

## Comparison with Tkinter Blueprints

| Feature | HTML | Tkinter |
|---------|------|---------|
| Dependency | None (optional: websockets) | Tcl/Tk runtime |
| Styling | Full CSS | Limited |
| Runs in | Browser tab | Native window |
| Real-time | WebSocket | Tkinter after() |
| External control | REST API + Python | Python cmd_*() methods |
| Cross-platform | Any browser | macOS/Windows/Linux with Tk |

## Creating New Blueprints

1. Create `blueprint/<name>/` directory
2. Add `index.html` (standalone SPA)
3. Add `server.py` with a server class
4. Add `AGENT.md` documentation
5. Add `__init__.py`
