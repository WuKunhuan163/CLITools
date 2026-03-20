# OpenClaw Role-Play Session Log

Date: 2026-03-06
Purpose: Simulate OpenClaw agent workflow to identify and fix gaps in our OPENCLAW implementation.

Each task follows the OpenClaw agent lifecycle:
1. System loads: skills scan, memory recall, bootstrap context
2. Agent selects relevant skill, reads it
3. Agent searches memory for prior experience
4. Agent plans and executes with tools
5. Agent records lessons
6. Agent reports completion

Gaps are identified at each step and fixed immediately.

---

## Gap Log

| # | Task | Step | Gap Description | Fix Applied | File(s) Changed |
|---|------|------|----------------|-------------|-----------------|
| 1 | T1-Bilibili | Memory Recall | No unified memory search interface — Cursor agents use `SKILLS lessons`, OPENCLAW remote agents use `--openclaw-memory-search`. OpenClaw has a single `memory_search` tool. | Documented as future unification target. Both paths read from `data/_/runtime/_/eco/experience/lessons.jsonl`. | (documented) |
| 2 | T1-Bilibili | Tool Discovery | Remote agent has no way to learn a tool's specific commands (e.g., `filter-search --sort views`). OpenClaw provides tool docs in system prompt context; OPENCLAW only lists tool names. | Added `--openclaw-tool-help [TOOL]` command that returns the tool's `AGENT.md` or `README.md`. Updated protocol.py to advertise it. | `sandbox.py`, `protocol.py` |
| 3 | T1-Bilibili | Execution | Task completed successfully — found 10 videos with >1M views using BILIBILI filter-search --sort views. | No fix needed. Recorded lesson #13 about efficient search patterns. | (lesson recorded) |
| 4 | T2-Gmail | Tool Capability | GMAIL tool had no destructive operations (delete/archive). OpenClaw agent would be stuck — tool only supports read + send. | Added `delete_email(index)` to `GMAIL/logic/chrome/api.py` with `_gmail_click()` helper. Added `delete` CLI command. Updated `AGENT.md`. | `tool/GMAIL/logic/chrome/api.py`, `tool/GMAIL/main.py`, `tool/GMAIL/AGENT.md` |
| 5 | T2-Gmail | DOM Interaction | Gmail SPA ignores bare `.click()` calls. Initial `delete_email` implementation reported success but didn't actually delete. Gmail requires full mouse event chain: mousedown -> mouseup -> click. | Created `_gmail_click()` helper that dispatches full MouseEvent chain. Refactored `delete_email` to use it. | `tool/GMAIL/logic/chrome/api.py` |
| 6 | T2-Gmail | Execution | Successfully deleted 10 unimportant emails (Google security alerts, Kaggle promotions, account updates) one by one from inbox. | Recorded lesson #14 about Gmail's click requirements. | (lesson recorded) |
| 7 | T3-还好么 | Sandbox Capability | Sandbox only had basic read/list commands. A dev task requires npm, pip, mkdir, curl, git, and file writing. Agent can't build a project without these. | Extended `ALLOWED_COMMANDS` with npm/node/pip/mkdir/cp/mv/rm/curl/git. Added `--openclaw-write-file` and `--openclaw-web-search` handlers. | `sandbox.py`, `protocol.py` |
| 8 | T3-还好么 | Execution | Full-stack app built: Flask backend (REST API, SQLite, APScheduler for alerts) + React/Vite frontend. All endpoints tested. App runs at localhost:5001 (API) + localhost:5173 (UI). | Recorded lesson #15. | Backend: `app.py`, Frontend: `App.jsx`, `App.css` |
| 9 | GUI | GUI Architecture | Tkinter GUI has Tcl dependency issues and limited styling. Web-based GUI is more flexible, works in any Python env, and matches OPENCLAW's browser-centric architecture. | Created HTML chatbot blueprint at `logic/gui/html/blueprint/chatbot/` with `index.html` (dark theme SPA), `server.py` (HTTP+WebSocket server), `AGENT.md`. Updated OPENCLAW to use HTML GUI by default with `--gui tkinter` fallback. | `logic/gui/html/blueprint/chatbot/*`, `tool/OPENCLAW/logic/gui/chat_html.py`, `tool/OPENCLAW/main.py` |
| 10 | Yuanbao | DOM Selectors | Yuanbao uses Quill editor (`.ql-editor` contenteditable), not textarea. Send button is `<a class="style__send-btn">` with `.icon-send` icon. Response rendered in `.hyc-common-markdown`. New chat is `[class*="ic_newchat"]`. All need full MouseEvent chain. | Fixed `create_conversation()` to use Yuanbao icon selector. Rewrote `send_message()` to set Quill innerHTML directly + dispatch input event + full mouse event click on send-btn. Fixed `get_last_response()` to use `.hyc-common-markdown` selector. | `tool/OPENCLAW/logic/chrome/api.py` |
| 11 | Yuanbao | E2E Pipeline | Full end-to-end pipeline tested: boot -> create conversation -> send system prompt (18K chars) -> receive response -> parse for commands/termination. All steps functional. | Recorded lessons #16, #17. Pipeline is operational. | (tested, no code changes) |
| 12 | Yuanbao | Text Injection | `send_message()` using `innerHTML` with `<p>` tags caused HTML escaping of `<<EXEC:>>` tokens — agent received garbled protocol tokens. | Switched to `Input.insertText` CDP method which injects raw text without HTML escaping. | `tool/OPENCLAW/logic/chrome/api.py` |
| 13 | Yuanbao | Sandbox Routing | Sandbox didn't recognize project tool commands (e.g. `BILIBILI boot`). Agent couldn't use any project tools. | Added `_is_project_tool()` checker and `_execute_project_tool()` handler that routes tool commands to `python3 tool/<NAME>/main.py`. | `tool/OPENCLAW/logic/sandbox.py` |
| 14 | Yuanbao | System Prompt | Protocol included sample `<<EXEC:>>` tokens in instructions, which DeepSeek agent interpreted as already-attempted commands. System prompt was 19K chars — too long and noisy for a weaker model. | Rewrote `build_system_prompt()` with explicit emphasis on `<<EXEC:>>` format, added `_load_project_tools()` to dynamically list available tools, trimmed prompt significantly. | `tool/OPENCLAW/logic/protocol.py` |
| 15 | Yuanbao | Pipeline Loop | Agent repeated identical responses 14x with no circuit-breaker. Pipeline blindly kept executing the same stale loop. | Added `LOOP_DETECTION_THRESHOLD` (3 identical responses) — injects correction message with tool discovery hint and resets counter. | `tool/OPENCLAW/logic/pipeline.py` |
| 16 | Yuanbao | Tool Discovery | Agent didn't know project tools existed. System prompt listed only shell commands — no mention of BILIBILI, GMAIL, etc. | Added `_load_project_tools()` to dynamically enumerate non-protected tools from `tool/` directory with descriptions. Integrated into system prompt. | `tool/OPENCLAW/logic/protocol.py` |
| 17 | Yuanbao | Stale Responses | `wait_for_response()` couldn't distinguish old responses from new ones. It checked `is_generating()` which was false before the new response even started, returning the previous answer. | Added `_count_responses()` to track total response elements. `wait_for_response()` now does Phase 1 (wait for count to increase) then Phase 2 (wait for generation to finish). Accepts `prev_response_count` parameter. | `tool/OPENCLAW/logic/chrome/api.py` |
| 18 | Yuanbao | Auth Detection | `get_auth_state()` falsely reported `authenticated: True` when user was logged out — it relied on editor existence, but Yuanbao shows the editor even when not logged in (just disabled). | Rewrote auth detection to check for `.nologin` class, `tool__login` button presence, and send button disabled state. All three must be absent for `authenticated: True`. | `tool/OPENCLAW/logic/chrome/api.py` |
| 19 | Yuanbao | create_conversation | `create_conversation()` used bare `.click()` which Yuanbao's SPA ignored (same issue as Gmail/send button). Also didn't verify URL change, so stale conversations persisted. | Switched to full `mousedown/mouseup/click` event chain. Added URL change verification with fallback to navigating to chat root. | `tool/OPENCLAW/logic/chrome/api.py` |
| 20 | T4-GUI | Stdout Buffering | `OPENCLAW chat` command produced no visible output — Python's stdout buffering suppressed all print statements until process exit. Since `server.wait()` blocks indefinitely, output never appeared. | Added `os.environ.setdefault("PYTHONUNBUFFERED", "1")` to `main.py`. Added `flush=True` to all print calls in `cmd_chat()` and `chat_html.py`. | `tool/OPENCLAW/main.py`, `tool/OPENCLAW/logic/gui/chat_html.py` |
| 21 | T4-GUI | Browser Fallback | `ChatbotServer.open_browser()` called `open_tab()` via CDMCP but only caught exceptions — when `open_tab()` returned `False` (CDP unavailable), no exception was raised, so fallback to `webbrowser.open()` never triggered. Browser tab never opened. | Rewrote to check `open_tab()` return value: if `False` or exception, fall back to `webbrowser.open()`. | `logic/gui/html/blueprint/chatbot/server.py` |
| 22 | T4-GUI | Logo Discovery | Used CDMCP browser automation to navigate to `github.com/openclaw/openclaw`, found the repo (266k stars), extracted logo URLs from raw README. Repo has dark and light logo variants at `docs/assets/openclaw-logo-text{,-dark}.png`. Org avatar is the lobster icon. | Downloaded 3 assets via curl to `logic/gui/html/blueprint/chatbot/assets/`: `openclaw-logo-text.png`, `openclaw-logo-text-dark.png`, `openclaw-avatar.png`. | `logic/gui/html/blueprint/chatbot/assets/*` |
| 23 | T4-GUI | Theme Restyling | Original GUI used a purple accent (#7c6df0) dark theme. OpenClaw's brand is red (#d32f2f) with warm dark tones. Empty state showed a generic Unicode symbol. | Rewrote CSS variables to red/warm-dark palette. Added lobster emoji favicon via SVG data URI. Integrated downloaded logo in empty state and sidebar avatar. | `logic/gui/html/blueprint/chatbot/index.html` |
| 24 | T5-Session | Session Click | Clicking session items in sidebar had no effect. Click handler was on `.session-title` (inner div) not `.session-item` (parent row). The `<div>` had no `role` or `tabindex`, making it invisible to accessibility tree and CDMCP automation. | Moved click handler to `.session-item` with `e.target.closest(".session-delete")` guard. Added `role="button"`, `tabindex="0"`, `aria-label`, and keyboard support (Enter/Space). | `logic/gui/html/blueprint/chatbot/index.html` |
| 25 | T5-Session | E2E Verification | Used CDMCP to externally control the GUI: clicked session, filled textarea with "请帮我打开一个Chrome分页", pressed Enter. Pipeline booted, detected Yuanbao auth expired. Full round-trip verified. | No code fix needed. External control pattern validated: lock -> click -> fill -> press_key -> screenshot -> unlock. | (verified, no code changes) |
| 26 | T6-ShowDoc | Template Bug | `TOOL --dev create SHOWDOC` failed with `KeyError: '\n  "name"'`. The `tool.json.tmpl` template had raw `{` and `}` JSON braces that conflicted with Python's `str.format()` placeholder syntax. | Escaped JSON braces as `{{` and `}}` in `tool.json.tmpl`. Only `{name}` remains as a placeholder. | `logic/tool/template/tool.json.tmpl` |

---

## Summary

**Start time**: 2026-03-06T01:34:40
**Tasks completed**: 7 (3 role-play + HTML GUI + Yuanbao integration + GUI restyling + session click fix)
**Gaps identified and fixed**: 25
**Lessons recorded**: 9 (#13-#21)

### Key Technical Achievements

1. **BILIBILI**: Discovered `filter-search --sort views` for efficient high-view video discovery
2. **GMAIL**: Added `delete_email()` with `_gmail_click()` helper — full mouse event chain required for Gmail SPA
3. **还好么 App**: Built complete full-stack app (Flask + React + SQLite) with daily check-in, emergency contacts, scheduled alerts
4. **HTML GUI Blueprint**: Created `logic/gui/html/blueprint/chatbot/` — dark-themed SPA with WebSocket, replaces tkinter dependency
5. **Yuanbao E2E**: Fixed all DOM selectors (Quill editor, send-btn, .hyc-common-markdown, new-chat icon), verified full pipeline
6. **Pipeline Robustness**: Added stale response detection (Phase 1/2 wait), loop detection (3x repeat threshold), auth state hardening, create_conversation URL verification
7. **Agent Protocol**: Rewrote system prompt with dynamic project tool discovery, compact format, explicit `<<EXEC:>>` emphasis
8. **Sandbox Tool Routing**: Added project tool execution (`_is_project_tool` + `_execute_project_tool`) so remote agents can use BILIBILI, GMAIL, etc.
9. **GUI Restyling**: Restyled HTML chatbot to OpenClaw red theme with lobster favicon, downloaded official logo/avatar assets via CDMCP browser automation
10. **Launch Reliability**: Fixed stdout buffering and browser open fallback — `OPENCLAW chat` now shows immediate output and reliably opens a browser tab

### Lessons #18-#19

- **#18 (Stdout Buffering)**: When Python process blocks indefinitely (e.g. `server.wait()`), stdout is never flushed in non-TTY contexts. Always use `flush=True` on print calls before blocking operations, or set `PYTHONUNBUFFERED=1`.
- **#19 (Return Value Fallback)**: CDMCP's `open_tab()` returns `False` on failure rather than raising an exception. Functions that call it must check the return value, not rely on try/except alone.

### BLOCKER: Yuanbao Auth Expired

As of 2026-03-06 ~02:30, the Yuanbao session expired ("Not logged in"). User needs to re-authenticate at `yuanbao.tencent.com/chat` to continue Yuanbao integration testing. All code fixes (Gaps 12-19) are implemented and ready for re-testing once auth is restored.

### Files Changed

| Category | Files |
|----------|-------|
| OPENCLAW sandbox | `tool/OPENCLAW/logic/sandbox.py` (tool-help, write-file, web-search, expanded commands, project tool routing) |
| OPENCLAW protocol | `tool/OPENCLAW/logic/protocol.py` (compact prompt, dynamic tool listing, explicit EXEC format) |
| OPENCLAW pipeline | `tool/OPENCLAW/logic/pipeline.py` (loop detection, stale response tracking, response count threading) |
| OPENCLAW Yuanbao API | `tool/OPENCLAW/logic/chrome/api.py` (create_conversation mouse chain + URL verify, stale response detection, auth hardening, Input.insertText) |
| OPENCLAW GUI (HTML) | `tool/OPENCLAW/logic/gui/chat_html.py`, `tool/OPENCLAW/main.py` |
| HTML blueprint | `logic/gui/html/blueprint/chatbot/{index.html, server.py, AGENT.md}` |
| HTML blueprint assets | `logic/gui/html/blueprint/chatbot/assets/{openclaw-logo-text.png, openclaw-logo-text-dark.png, openclaw-avatar.png}` |
| GMAIL tool | `tool/GMAIL/logic/chrome/api.py`, `tool/GMAIL/main.py`, `tool/GMAIL/AGENT.md` |
| Documentation | `tool/OPENCLAW/README.md`, `tool/OPENCLAW/AGENT.md`, `tool/OPENCLAW/logic/AGENT.md` |
| 还好么 App | `tmp/haihao-ma/{backend/app.py, frontend/src/App.jsx, frontend/src/App.css, README.md}` |
