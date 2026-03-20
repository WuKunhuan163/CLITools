# Assistant Full-Stack Code Audit

**Date:** 2026-03-16
**Scope:** `logic/assistant/gui/` (server, engine, live.html, round_store) + `tool/LLM/logic/task/agent/conversation.py`
**Total LOC reviewed:** ~10,083 across 5 core files

---

## 1. Architecture Overview

| Component | File | LOC | Role |
|-----------|------|-----|------|
| Backend Server | `logic/assistant/gui/server.py` | 1,628 | HTTP API, SSE broker, session/config management |
| Conversation Engine | `tool/LLM/logic/task/agent/conversation.py` | 2,313 | LLM orchestration, tool execution, auto-retry |
| Frontend Engine | `logic/assistant/gui/engine.js` | 2,191 | Protocol-driven UI rendering (reusable module) |
| Frontend App | `logic/assistant/gui/live.html` | 3,656 | Full SPA: settings, sidebar, chat, data panels |
| Round Store | `logic/assistant/gui/round_store.py` | 295 | Per-round token/file data + inspection pages |

### Dependency Graph

```
live.html → engine.js → SSE ← server.py → conversation.py → LLM providers
                                            ↳ tools.py (std tools)
                                            ↳ auto.py (model selection)
```

The architecture cleanly separates protocol events from rendering. The engine processes events sequentially via `enqueueEvent()`, making replay and testing straightforward. The server acts as a thin proxy between the HTTP/SSE layer and the `ConversationManager`.

---

## 2. Strengths

### 2.1 Protocol-Driven Rendering
The `engine.js` event system is well-designed. Each SSE event type has a dedicated renderer, making the UI deterministic and replay-safe. The `registerBlock()` pattern is extensible.

### 2.2 SSE Resilience (Server-Side)
The SSE broker (`_SSEBroker` in `html_server.py`) sends keepalive comments every 15 seconds, preventing proxy/firewall timeouts. Client count tracking enables future load monitoring.

### 2.3 Auto Model Selection
The `auto.py` module implements a sophisticated two-tier selection (primary/fallback lists) with provider health tracking and configurable recovery conditions. This is enterprise-quality design.

### 2.4 Tool Streaming
The streaming edit/think preview system (`tool_stream_start/delta/end`) provides Cursor-quality UX for long tool outputs. The parallel tool execution for read-only tools (`read_file`, `search`) is a good optimization.

### 2.5 Event Persistence
Sessions are persisted to disk (`<id>/history.json`) with reconstruction on reload. The round store rebuilds token data from event history, enabling crash recovery.

---

## 3. Issues Found

### 3.1 Critical

#### C1: `_event_history` Unbounded Memory Growth
**File:** `server.py`, all `_push_sse` callsites
**Impact:** Memory leak for long-running sessions

The `_event_history` dict accumulates all events for every session in memory with no eviction. A session with 200 rounds at 100+ events/round can hold tens of thousands of events. The `_edit_blocks` dict similarly rebuilds from the full event history on every access (`_get_edit_blocks` → `_build_edit_blocks` scans all events each time).

**Fix:** Implement a sliding window or tier the event history: keep recent N rounds in memory, offload older rounds to disk. Add lazy loading for `_edit_blocks`.

#### C2: No Input Validation on `/api/session/<sid>/purge`
**File:** `server.py`, `_api_purge_data`
**Impact:** Data corruption if malformed requests are sent

The purge endpoint accepts `type` and `count` but doesn't validate that `type` is one of the expected enum values (`input`, `output`, `context`, `read`, `edit`, `exec`, `rounds`). Arbitrary strings pass through silently.

**Fix:** Validate `dtype` against an explicit allowlist.

#### C3: Race Condition in `_resilient_stream` Producer Thread
**File:** `conversation.py`, `_resilient_stream`
**Impact:** Potential deadlock if producer thread outlives the generator

The producer thread runs independently and pushes to `chunk_queue`. If the consumer (generator caller) stops iterating (e.g., due to cancellation or exception in the calling code), the producer keeps running and may block on `chunk_queue.put()` if the queue fills up (maxsize not set). The `daemon=True` flag prevents orphan threads at process exit but not during a single turn.

**Fix:** Add a `threading.Event` cancel signal. Set maxsize on the queue. The producer should check the cancel flag between chunks.

### 3.2 High

#### H1: Monolithic `_run_turn` Method (560+ lines)
**File:** `conversation.py:1355-2100`
**Impact:** High maintenance burden, difficult to test

The `_run_turn` method contains the entire LLM orchestration loop: model selection, streaming, tool execution, auto-retry, nudging, zombie detection, and round management. At 560+ lines with 8+ levels of nesting, it violates single-responsibility and makes unit testing impractical.

**Recommendation:** Extract into focused methods: `_execute_streaming_round()`, `_handle_auto_fallback()`, `_process_tool_calls()`, `_emit_round_end()`. Each can be independently tested.

#### H2: Silent Exception Swallowing
**File:** `conversation.py` (30+ bare `except` blocks)
**Impact:** Hidden bugs, debugging difficulty

Many exception handlers use `except Exception: pass` or `except Exception: <minimal handling>` without logging. Examples:
- `_fire_hook` (line ~2072): hooks silently fail
- Provider health reporting (lines ~1695-1698): failures are invisible
- Usage recording (lines ~1681-1682): cost tracking silently breaks

**Fix:** Add `logger.exception()` or `logger.warning()` in all catch blocks. At minimum, emit debug events for hook/recording failures.

#### H3: `live.html` Single-File SPA (3,656 lines)
**File:** `live.html`
**Impact:** Poor maintainability, no code splitting

The entire frontend — HTML structure, CSS (700+ lines), JavaScript (2,500+ lines including 102 functions), and template strings — lives in a single file. This makes feature isolation, testing, and code review extremely difficult.

**Recommendation:** Extract into modules:
- `style.css` — all CSS
- `settings.js` — settings panel logic (500+ lines)
- `data-panel.js` — data sidebar logic
- `queue.js` — task queue management
- `live.js` — core chat/send/SSE logic

#### H4: Frontend Global State Pollution
**File:** `live.html`
**Impact:** Namespace collisions, implicit coupling

The frontend uses 20+ global variables (`sending`, `taskRunning`, `activeSessionId`, `currentModel`, `debugMode`, `currentTurnLimit`, `_allSessions`, `_queuedTasks`, etc.) without namespacing. Functions mutate globals freely, making data flow hard to trace.

**Fix:** Group into a state object: `const appState = { sending, taskRunning, activeSessionId, ... }`. Or use a lightweight store pattern.

### 3.3 Medium

#### M1: `_force_no_tools` Dead Code
**File:** `conversation.py:1504`
**Impact:** Code confusion

After the round-limit fix (task 7), `_force_no_tools` is initialized but never set to `True`. The check at line 1545 (`if _force_no_tools: api_tools = None`) is dead code.

**Fix:** Remove `_force_no_tools` and the conditional at line 1545.

#### M2: Duplicate `sendMessage()` Paths
**File:** `live.html:1678-1721`
**Impact:** Code duplication, inconsistent behavior

`sendMessage()` has two code paths: one for queueing during a running task (lines 1678-1687) and one for fresh sends (lines 1697-1721). The queue path doesn't show the pending model banner or start the connection watchdog.

**Fix:** Unify: the queue path should also show the banner with a "Queued" indicator.

#### M3: Missing `AbortController` for Stale Fetches
**File:** `live.html` (multiple `fetch()` calls)
**Impact:** Race conditions on rapid session switching

When the user switches sessions rapidly, previous fetches (settings, data, sessions) may resolve after the UI context has changed. No `AbortController` is used to cancel stale requests.

**Fix:** Create an AbortController per session switch; abort previous controllers when switching.

#### M4: `setInterval(syncSessions, 10000)` Without Backoff
**File:** `live.html:3305`
**Impact:** Unnecessary network traffic when idle

Sessions sync every 10 seconds regardless of activity. This is wasteful for idle sessions and can create flickering in the sidebar.

**Fix:** Use exponential backoff: sync frequently during activity (5s), slow down when idle (30-60s). Reset backoff on user interaction.

#### M5: `__import__("time")` Inline Import
**File:** `server.py:381`
**Impact:** Code smell

The `/api/health` endpoint uses `__import__("time").time()` instead of a proper import. While functional, this is an anti-pattern.

**Fix:** Import `time` at the top of the method or module.

#### M6: `_build_edit_blocks` Rebuilds on Every Access
**File:** `server.py:1166`
**Impact:** O(n) cost per edit block query

Every call to `_get_edit_blocks()` rescans the full event history. For sessions with thousands of events, this is O(n) per access.

**Fix:** Maintain an incremental append-only list. Only scan new events since the last build.

### 3.4 Low / Style

#### L1: Inconsistent Error Event Types
The codebase uses both `{"type": "error", ...}` and `{"type": "system_notice", "level": "error", ...}` for error events. The recent migration to `system_notice` is incomplete.

**References:** `conversation.py:1307` still emits `{"type": "error"}`.

#### L2: Magic Numbers
Multiple magic numbers throughout: `90` (heartbeat timeout), `3` (max consecutive empty), `6` (max nudge round), `12` (max quality check round), `50` (zombie check interval), `16384` (max tokens). These should be class-level constants.

#### L3: `esc()` Not Used Consistently in Template Literals
Most `innerHTML` assignments properly use `esc()` for user data, but some template literals embed raw variables. Example: `live.html:2959` uses `data.error` directly in innerHTML without escaping.

#### L4: No TypeScript / JSDoc Type Coverage
The 2,191-line `engine.js` has no type annotations. Adding JSDoc `@param` / `@returns` annotations would improve IDE support and catch type errors.

---

## 4. Feature Completion Audit

| Feature | Status | Issues |
|---------|--------|--------|
| Multi-session management | Complete | Sidebar indicator race (fixed this session) |
| Auto model selection | Complete | Provider health state not surfaced in UI |
| Round limit enforcement | Fixed | Was off-by-one (fixed this session) |
| Streaming tool preview | Complete | No progress indicator for long tool calls |
| Edit accept/revert | Complete | `_build_edit_blocks` performance (M6) |
| Data sidebar (purge) | Complete | Missing input validation (C2) |
| Settings panel | Complete | Settings changes don't notify other tabs |
| Task queuing | Complete | Queue path doesn't show pending banner (M2) |
| Network resilience | Improved | Added resilient stream + watchdog (this session) |
| SSE reconnection | Complete | Existing keepalive + health check |
| Prompt engineering | Improved | Agent still occasionally over-reads files |
| Syntax error tolerance | Fixed | Edit writes file + warns (this session) |
| JSON parsing robustness | Improved | Embedded JSON extraction added |
| Immediate model banner | Added | Shows on send, 30s timeout (this session) |
| Cost tracking | Complete | USD conversion, per-round cost display |
| Dark/light theme | Complete | CSS variables, `logo-adaptive` for logos |
| Localization (en/zh) | Partial | ~60% of UI strings translated |

---

## 5. Performance Considerations

| Area | Current | Recommendation |
|------|---------|---------------|
| Event history | In-memory, unbounded | Tier: recent in memory, old on disk |
| Edit block scan | O(n) per access | Incremental append-only |
| SSE broadcast | All events to all clients | Session-scoped SSE channels |
| Frontend re-render | Full sidebar rebuild | Virtual list / diff-based updates |
| `syncSessions` polling | Fixed 10s interval | Adaptive backoff |
| Round store memory | All rounds in memory | LRU eviction for old rounds |

---

## 6. Security Notes

| Area | Status |
|------|--------|
| HTML escaping | `esc()` function used in engine.js; mostly consistent |
| API authentication | None (localhost only) — acceptable for local tool |
| File access | `edit_file`, `read_file` unrestricted — intentional for agent |
| CORS | `Access-Control-Allow-Origin: *` — acceptable for localhost |
| Input validation | Weak on purge/inject endpoints (C2) |

---

## 7. Recommendations Priority

### Immediate (This Sprint)
1. **Remove `_force_no_tools` dead code** (M1) — 2 min fix
2. **Fix `/api/health` inline import** (M5) — 1 min fix
3. **Add purge endpoint validation** (C2) — 5 min fix
4. **Escape `data.error` in innerHTML** (L3) — 2 min fix

### Short-Term (Next Sprint)
5. **Extract `_run_turn` into sub-methods** (H1) — reduces complexity
6. **Add logging to exception handlers** (H2) — improves debuggability
7. **Fix `_resilient_stream` producer lifecycle** (C3) — add cancel signal
8. **Incremental `_build_edit_blocks`** (M6) — performance fix

### Medium-Term
9. **Split `live.html` into modules** (H3) — major maintainability win
10. **Namespace global state** (H4) — reduces coupling
11. **Event history tiering** (C1) — memory management
12. **Adaptive `syncSessions` polling** (M4) — reduce waste

---

## 8. Test Coverage Gap

No automated tests exist for:
- Frontend rendering (engine.js event → DOM output)
- SSE reconnection behavior
- Auto-retry model fallback sequences
- Round limit boundary conditions
- Data purge correctness
- Edit block accept/revert lifecycle

**Recommendation:** Add integration tests using a mock LLM provider. The engine's event-driven design makes it naturally testable — feed events, assert DOM state.

---

*Generated by code audit on 2026-03-16. Files analyzed at commit HEAD.*
