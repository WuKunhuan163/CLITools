# OPENCLAW Logic — Technical Reference

## Architecture

```
tool/OPENCLAW/
  main.py                  CLI entry point (chat, status, sessions)
  setup.py                 Tool installation
  tool.json                Tool metadata
  logic/
    chrome/api.py          CDMCP API for yuanbao.tencent.com
    gui/chat.py            Glue: tkinter chatbot blueprint -> OPENCLAW pipeline
    gui/chat_html.py       Glue: HTML chatbot blueprint -> OPENCLAW pipeline (default)
    session.py             Session persistence (JSON files in data/sessions/)
    pipeline.py            Task execution loop (user -> agent -> sandbox -> agent)
    protocol.py            Message packaging and response parsing
    sandbox.py             Restricted command execution
  skills/                  OpenClaw-characteristic skills (canonical source)
  data/
    sessions/              Persisted session JSON files
    BOOTSTRAP.md           Centralized project context for remote agents

Blueprints (shared):
  logic/gui/html/blueprint/chatbot/    HTML-based chatbot (default)
    index.html             Dark-theme SPA with sidebar + chat + WebSocket
    server.py              ChatbotServer: HTTP + WebSocket bridge
    for_agent.md           Blueprint docs
  logic/gui/tkinter/blueprint/chatbot/ Tkinter-based chatbot (fallback)
    gui.py                 ChatbotWindow (reusable, extends BaseGUIWindow)
    for_agent.md           Blueprint docs
```

## chrome/api.py — Yuanbao DOM Interaction

Tab discovery: `find_yuanbao_tab()` searches for `yuanbao.tencent.com` via `logic.chrome.session.find_tab()`.

**Critical DOM knowledge** (lesson #17):
- Input: Quill editor `.ql-editor` (contenteditable), NOT textarea
- Send button: `<a class="style__send-btn">` containing `.icon-send`
- Response content: `.hyc-common-markdown`
- New chat icon: `[class*="ic_newchat"]`
- All interactive elements require full MouseEvent chain (mousedown+mouseup+click)

Public API:
- `boot_yuanbao(port)` — Ensure Chrome + Yuanbao tab via CDMCP, return auth state
- `find_yuanbao_tab(port)` — Find the Yuanbao tab
- `get_auth_state(port)` — Check login status
- `get_conversations(port)` — List sidebar conversations
- `create_conversation(port)` — Click new chat icon
- `send_message(text, port)` — Write to Quill editor + click send-btn
- `is_generating(port)` — Check if agent is still responding
- `get_last_response(port)` — Get last .hyc-common-markdown content
- `wait_for_response(timeout, poll_interval, port)` — Poll until response complete

## pipeline.py

The core loop:
1. Pre-flight: boot Yuanbao (ensure_chrome + require_tab) + verify auth
2. Create new remote conversation
3. Send system prompt + project summary + user task
4. Wait for response, parse it
5. Execute any `<<EXEC: cmd >>` tokens via sandbox
6. Feed results back to agent
7. Repeat until `<<OPENCLAW_TASK_COMPLETE>>` or max iterations (50)

Heartbeat: every 5 minutes, verifies remote agent connection.

## sandbox.py

Protected paths (agent cannot access): OPENCLAW, GOOGLE.CDMCP, logic/chrome, .git, .cursor, data/run.

Allowed commands: ls, cat, head, tail, wc, grep, find, echo, pwd, tree, file, stat, python3, pip, pip3, npm, npx, node, mkdir, cp, mv, rm, touch, curl, wget, git.

Special OPENCLAW commands:
- `--openclaw-memory-search "query"` — Search lessons.jsonl (MANDATORY before tasks)
- `--openclaw-experience "lesson"` — Record a lesson to institutional memory
- `--openclaw-status` — Report project and tool status
- `--openclaw-tool-help [TOOL]` — Get a tool's for_agent.md documentation
- `--openclaw-write-file <path> <content>` — Write content to a file
- `--openclaw-web-search <query>` — Search the web via TAVILY

## protocol.py

System prompt structure (OpenClaw-inspired):
1. Identity -> Bootstrap context (BOOTSTRAP.md) -> Available commands -> Skills (mandatory scan) -> Memory recall (mandatory) -> Learnings -> Project overview -> Execution rules -> Safety

## Gotchas

1. **DOM selectors for Yuanbao may change**: Check `get_auth_state()` first.
2. **Full mouse event chain required**: Gmail and Yuanbao both swallow bare `.click()`.
3. **Response parsing relies on text tokens**: Agent must output `<<EXEC:`, `<<EXPERIENCE:`, `<<OPENCLAW_TASK_COMPLETE>>`.
4. **GUI choice**: HTML (default) runs in browser tab. Tkinter via `--gui tkinter`.
5. **One pipeline per session at a time**: GUI prevents concurrent sends.
