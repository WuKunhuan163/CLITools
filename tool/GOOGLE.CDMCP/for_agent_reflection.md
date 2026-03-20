# GOOGLE.CDMCP — Agent Self-Reflection

## Purpose

This file is a **stable reflection guide** for agents working on GOOGLE.CDMCP. It prompts self-evaluation and identifies improvement opportunities. It is NOT a recording file — session discoveries go to `BRAIN log` / `SKILLS learn`, not here.

## How to Update This File

This file should be **refined, not grown**:
- **Fix a gap** → remove it from "Known Gaps" and briefly note what replaced it
- **Discover a gap** → add it, but keep to 3-5 gaps
- **Session-specific notes** → `BRAIN log`, `SKILLS learn`, `runtime/experience/lessons.jsonl`
- **Never add a changelog or session log** — that belongs in git history and brain context

## Self-Check (after each task on this tool)

- **Discovery**: Did I read this tool's `for_agent.md` and search for related skills before coding?
- **Interface**: If I added reusable functionality, did I expose it in `interface/main.py`?
- **Testing**: Did I run existing tests and add new ones for my changes?
- **Documentation**: Did I update `README.md` and `for_agent.md` to reflect my changes?

## Known Gaps

1. **Default screenshot targets demo tab** — `--mcp-screenshot` without `--tab-id` captures the demo/session tab instead of the most recently navigated tab. Should track and default to the last user-navigated tab.
2. **websocket package conflict** — The `websocket` v0.2.1 server package conflicts with `websocket-client`. Fixed by uninstalling the old package but need to ensure `setup.py` doesn't reintroduce it.
3. **No accessibility tree snapshot** — Cursor's browser has `browser_snapshot` returning a structured accessibility tree with refs for direct element targeting. CDMCP uses CSS selectors only. Consider adding an accessibility-tree-based interaction mode.
4. **No form-filling shorthand** — Cursor has `browser_fill_form` for batch form filling. CDMCP requires individual calls.
5. **Demo error reporting is opaque** — When `--mcp-demo --single` fails, the message "Demo had failures: check steps" gives no actionable detail. Should log specific step failures.

## Comparison: CDMCP vs Cursor IDE Built-in Browser (2026-03-17)

| Feature | CDMCP | Cursor Browser | Gap |
|---------|-------|----------------|-----|
| Navigation | `--mcp-navigate URL` | `browser_navigate` | Equivalent |
| Click | `--mcp-click` (CSS selector) | `browser_click` (accessibility ref) | CDMCP: selector-based only; Cursor: ref-based (more robust) |
| Type | `mcp_type()` with char delay | `browser_type` | Equivalent, CDMCP has visual feedback |
| Fill | `mcp_fill()` | `browser_fill` | Equivalent |
| Snapshot | `--mcp-scan` (element scan) | `browser_snapshot` (accessibility tree) | CDMCP scan is slower and less structured |
| Screenshot | `--mcp-screenshot` | `browser_take_screenshot` | Equivalent, but default tab targeting differs |
| Lock/Unlock | Visual overlay lock | `browser_lock`/`browser_unlock` | CDMCP: visual; Cursor: tab-level |
| Scroll | `--mcp-scroll` | `browser_scroll` | Equivalent |
| Session Mgmt | Full session system | Per-tab viewId | CDMCP: richer session model |
| Visual Effects | Badge, focus, highlight, cursor | None | CDMCP advantage |
| Dialog Handling | `mcp_handle_dialog` | `browser_handle_dialog` | Equivalent |
| Network Monitor | `mcp_network_requests` | `browser_network_requests` | Equivalent |
| Console Logs | `mcp_console_messages` | `browser_console_messages` | Equivalent |
| Auth Integration | Google auth flow | None | CDMCP advantage |
| Page Search | `mcp_search` | `browser_search` | Equivalent |
| Robustness | Manual Chrome lifecycle | IDE-managed browser | Cursor: more stable |

## Design Notes

(Stable, non-obvious architectural decisions or constraints. NOT per-session observations — only enduring design patterns.)
