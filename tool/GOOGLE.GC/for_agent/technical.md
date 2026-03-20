# GOOGLE.GC Technical Details

## Key Behaviors

- All operations use CDMCP session `require_tab()` for tab lifecycle
- If the Colab tab is missing, it auto-opens in the session window
- If the session window is lost, triggers full session reboot
- Every operation shows MCP visual effects (lock, badge, highlight, counter)
- Turing machine tracks state for error recovery

## Toolbar Targeting

Colab creates the cell toolbar (shadow DOM) **only for the focused cell**. The flow is:
1. Defocus all cells via API, focus target cell
2. Real click on left margin (command mode)
3. Hover to render toolbar
4. Access buttons via `cells[idx].querySelector('.cell-toolbar colab-cell-toolbar').shadowRoot`

Available toolbar buttons: `move-up`, `move-down`, `delete`, `edit` (text cells), `more`
Available "More actions" menu: `select`, `copy-link`, `cut`, `copy`, `delete`, `comment`, `editor-settings`, `mirror`, `scratch`, `form`

## Closure Library Menus

Colab uses Google Closure Library for top-bar menus and cell context menus.
- `.click()` and CDP `real_click` don't work through the lock overlay
- Use JS `dispatchEvent(new MouseEvent('mousedown', ...))` instead
- Menu item text may include keyboard shortcuts (use `startsWith` matching)
- Menu item IDs are dynamic (`:75`, `:76`) so match by text content

## State Reporting

`GOOGLE.GC state --json` returns structured state:
- `cells`: list of `{index, type, text, text_length, focused}`
- `runtime`: `{button_text, connected, running_cells, pending_cells}`
- `notebook`: `{title, url}`
- `cdp_available`: bool
- `colab_tab`: `{id, url}`

Use after operations to verify expected state changes programmatically.

## Screenshot for Verification

`Page.captureScreenshot` requires connecting to the `type: "page"` target (not iframe):
```python
from logic.chrome.session import CDPSession, list_tabs, capture_screenshot
tabs = [t for t in list_tabs()
        if "colab.research.google.com" in t.get("url", "") and t.get("type") == "page"]
s = CDPSession(tabs[0]["webSocketDebuggerUrl"])
img = capture_screenshot(s)  # returns bytes or None
s.close()
```

## Cell Edit Details

- `--replace-with` escaping: `\\n` = literal `\n`, actual newline = line separator
- Line indices are 0-based
- Typing speed adapts to content length (more content = faster)
- Line-level highlighting for line operations

## Error Handling

- Missing cell: Turing machine reports "Cell N not found (have M cells)"
- Missing line: Reports "Line N not found (cell has M lines)"
- No Colab tab: Auto-opens if session exists, fails otherwise
- CDP unavailable: Reports connection error at first stage
