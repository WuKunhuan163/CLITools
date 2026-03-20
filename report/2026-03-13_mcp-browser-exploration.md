# MCP Browser & Colab Integration Exploration Report

Date: 2026-03-02

## Problem Statement

The Cursor IDE built-in browser (`cursor-ide-browser`) has limitations:
1. **OAuth popup flows fail**: `drive.mount()` in Colab triggers "credential propagation was unsuccessful" because the embedded browser cannot handle cross-tab OAuth redirects.
2. **Isolated clipboard**: `Meta+V` paste doesn't work — the MCP browser has a separate clipboard context from the system.
3. **Session instability**: Long idle periods cause "Could not load JavaScript files" errors, requiring session restarts.

These issues mean the built-in browser cannot reliably support Google Drive-authenticated Colab workflows.

## Solutions Explored

### 1. Chrome DevTools MCP (Recommended for External Browser Control)

**Package**: `chrome-devtools-mcp` (Official Google, ChromeDevTools org)
**GitHub**: https://github.com/ChromeDevTools/chrome-devtools-mcp

Controls an **existing Chrome browser session** on the user's machine. Since the user is already logged into Google in their regular Chrome, all OAuth/auth is pre-established.

**Key Features**:
- Connect to active Chrome sessions (no re-auth needed)
- `--autoConnect` flag (Chrome M144+) connects to existing sessions
- Puppeteer-based automation with automatic result waiting
- Full DevTools access: DOM, network, console, performance
- User sees permission dialog for each connection (security)

**Setup**:
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest", "--autoConnect"]
    }
  }
}
```
Requires: Chrome M144+, Node.js v20.19+, enable `chrome://inspect/#remote-debugging`.

**Verdict**: Most promising for controlling authenticated Colab sessions. The user's regular Chrome is already logged into Google, so all auth flows work natively.

---

### 2. Playwright MCP (External Headless/Headed Browser)

**Package**: `@playwright/mcp` (Official Microsoft)
**GitHub**: via npm `npx -y @playwright/mcp@latest`

Launches a **new browser instance** (Chromium, Firefox, or WebKit). Supports headed mode where the user can see the browser window.

**Key Features**:
- Accessibility-first interaction (similar to cursor-ide-browser)
- Can persist browser profiles for session reuse
- Headed mode allows user to see and intervene

**Limitation**: Launches a fresh browser, so Google login must be done again (or use persistent profile). Does NOT connect to the user's existing Chrome.

**Setup**:
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    }
  }
}
```

**Verdict**: Good for automation but requires separate login. Persistent profile can cache credentials, but initial OAuth flow still needed.

---

### 3. Google Colab MCP Servers (Direct Execution)

Two dedicated Colab MCP servers exist that bypass the browser entirely:

#### 3a. `mcp-server-colab-exec`
**Package**: PyPI `mcp-server-colab-exec` (by pdwi2020)
**GitHub**: https://github.com/pdwi2020/mcp-server-colab-exec

Allocates Colab GPU runtimes and executes Python code directly.

**Tools**: `colab_execute`, `colab_execute_file`, `colab_execute_notebook`
**Auth**: OAuth2 (opens browser window on first run, caches tokens)
**Setup**: `uvx mcp-server-colab-exec`

#### 3b. `google-colab-mcp`
**Package**: PyPI `google-colab-mcp` (by inkbytefo)

Full Colab integration: notebook CRUD, code execution, file ops, package management.

**Features**: Persistent Chrome profile, auto OAuth2, session management
**Auth**: Same OAuth2 as Google Colab VS Code extension

**Verdict**: These could replace the entire GDS browser workflow for code execution, running code on Colab GPUs without any browser interaction after initial auth. However, they may not support arbitrary shell commands or the specific Drive-based sync architecture GDS uses.

---

### 4. browser-use MCP (AI-Driven Browser Control)

**Package**: `browser-use` (Python)
**Docs**: https://docs.browser-use.com

AI-powered browser automation using Chrome DevTools Protocol. Can connect to running Chrome instances.

**Key Features**:
- CDP connection to existing Chrome/Chromium
- Natural language task descriptions
- Multi-LLM support
- State persistence across sessions

**Verdict**: Powerful but complex. Adds another AI layer. Better suited for general web automation than Colab-specific tasks.

---

### 5. Colab REST API Server (Jupyter Kernel)

**Package**: `colab_api_server` (by ekoshv)
**GitHub**: https://github.com/ekoshv/colab_server

Sets up a REST API inside a running Colab instance, allowing remote code execution via HTTP.

**How it works**: 
1. User runs `ColabAPIServer.run()` in a Colab cell
2. Server provides a public URL (via ngrok or similar)
3. Local code sends POST requests to execute Python remotely

**Verdict**: Requires initial manual setup in Colab but then enables fully programmatic execution. Could be integrated into GDS remount script as an optional feature.

---

### 6. Google Drive MCP Server (File Operations Only)

**Package**: `@modelcontextprotocol/server-gdrive` (Official Anthropic)
**GitHub**: https://github.com/modelcontextprotocol/servers/tree/main/src/gdrive

Direct Google Drive file operations without browser.

**Tools**: `gdrive_search`, `gdrive_read_file`
**Auth**: OAuth Desktop App

**Verdict**: Only handles file operations (read, search, list). Cannot execute code on Colab. Could complement GDS for file sync but doesn't solve the execution problem.

## Hands-On CDP Testing Results

### Setup Requirements (Chrome 143)

Chrome must be launched with explicit flags for CDP access:

```bash
# Quit Chrome first, then:
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=* \
  --user-data-dir="$HOME/ChromeDebugProfile"
```

- `--user-data-dir` is REQUIRED (Chrome refuses debugging with default profile)
- `--remote-allow-origins=*` is REQUIRED (WebSocket CORS rejection otherwise)
- The ChromeDebugProfile persists between sessions (extensions, logins saved)
- Chrome M143 does NOT support `--autoConnect` (requires M144+)

### Issue 1: Run Button Click - SOLVED

The Colab run button is `<colab-run-button>`, a **Web Component with Shadow DOM**.
Regular `querySelector('button')` cannot find it.

**Working solutions (3 methods):**

```javascript
// Method A: Click the custom element directly (simplest)
document.querySelector('colab-run-button').click();

// Method B: Access Shadow DOM inner button
document.querySelector('colab-run-button')
  .shadowRoot.querySelector('#run-button').click();

// Method C: Use Colab tooltip for shortcut reference
// Tooltip shows: "Run cell (Cmd/Ctrl+Enter)"
```

Shadow DOM structure:
```
<colab-run-button>
  #shadow-root
    <div class="cell-execution focused running">
      <button id="run-button" aria-label="Run cell">
        <span class="cell-execution-indicator">
          <svg>...</svg>  (play icon)
        </span>
      </button>
      <div class="status">
        <div class="execution-count">[ ]</div>
      </div>
    </div>
```

Execution state tracking via classes: `pending` -> `running` -> `stale` (completed).

### Issue 2: Keyboard Shortcuts - SOLVED

All three work when the cell is properly focused:

| Shortcut | CDP modifiers | Behavior |
|---|---|---|
| Shift+Enter | `modifiers: 8` | Run cell, move focus to next |
| Ctrl+Enter | `modifiers: 2` | Run cell, keep focus |
| Cmd+Enter | `modifiers: 4` | Run cell, keep focus |

```python
# Focus cell first
session.evaluate("document.querySelector('.cell.code textarea.inputarea').focus()")

# Then dispatch key event
session.send_and_recv("Input.dispatchKeyEvent", {
    "type": "keyDown", "key": "Enter", "code": "Enter",
    "windowsVirtualKeyCode": 13, "modifiers": 2  # Ctrl+Enter
})
```

Original failure cause: The GDS remount script takes 120+ seconds; tests only waited 5 seconds.

### Issue 3: JS Injection / Colab Internal APIs - SOLVED

Colab exposes rich internal APIs via the `colab` global object:

**Cell manipulation (best approach):**
```javascript
var cell = colab.global.notebook.cells[0];
cell.getText();                    // Read cell code
cell.setText("print('hello')");    // Set cell code
cell.isRunning();                  // Check execution state
cell.getExecutionCount();          // Get [N] count
```

**Notebook-level APIs:**
```javascript
var nb = colab.global.notebook;
nb.cells.length;                   // Number of cells
nb.insertCell(index, 'code');      // Add new cell
nb.runAll();                       // Run all cells
nb.focusCell(cellIndex);           // Focus specific cell
nb.saveNotebook();                 // Save
nb.connectToKernel();              // Connect to runtime
```

**Proven full workflow (setText + click + poll):**
```javascript
// 1. Set code
colab.global.notebook.cells[0].setText("print('test')");
// 2. Execute
document.querySelector('colab-run-button').click();
// 3. Read output
document.querySelector('.cell.code .output_text').textContent;
```

**Output reading:** `.output_text` selector on the cell DOM, or poll the
run button state div class for `running` -> `stale` transition.

### CDP Text Insertion (for paste-like behavior)

```python
# Focus cell editor textarea
session.evaluate("document.querySelector('.cell.code textarea.inputarea').focus()")

# Select all (Cmd+A)
session.send_and_recv("Input.dispatchKeyEvent", {
    "type": "keyDown", "key": "a", "code": "KeyA",
    "windowsVirtualKeyCode": 65, "modifiers": 4  # Meta
})

# Insert text (replaces selection)
session.send_and_recv("Input.insertText", {"text": "print('hello')"})
```

Both `Input.insertText` (CDP) and `cell.setText()` (JS API) work for setting code.
`setText()` is cleaner and more reliable.

## Recommendation

**Immediate (Ready to use now):**
1. Launch Chrome with `--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=~/ChromeDebugProfile`
2. Use raw CDP WebSocket connection from Python (proven working)
3. Workflow: `cell.setText(code)` -> `colab-run-button.click()` -> poll `.output_text`
4. No MCP server needed; direct CDP is simpler and fully tested

**Short-term (Better DX):**
- Install `chrome-devtools-mcp` as Cursor MCP server for IDE integration
- Upgrade Chrome to M144+ to use `--autoConnect` (no restart needed)

**Medium-term (Full automation):**
- Evaluate `mcp-server-colab-exec` or `google-colab-mcp` for headless execution
- Build CDP-based Colab controller into GDS tool as an interface module

**Long-term (Architecture):**
- Build a Colab REST API server into the GDS remount script
- Fully programmatic execution without any browser dependency

## End-to-End Workflow Validation

All tests below ran successfully on 2026-03-02 via CDP -> Chrome 143 -> Colab.

### Shell Command Execution with Exit Code

```python
# Inject this into Colab cell:
import subprocess
result = subprocess.run(['echo', 'Hello'], capture_output=True, text=True)
print(f"STDOUT: {result.stdout.strip()}")
print(f"EXIT_CODE: {result.returncode}")
```
Result: `STDOUT: Hello from Colab!`, `EXIT_CODE: 0`

### Error Detection (non-zero exit)

```python
result = subprocess.run(['ls', '/nonexistent_path'], capture_output=True, text=True)
```
Result: `STDERR: ls: cannot access '/nonexistent_path': No such file or directory`, `EXIT_CODE: 2`

### Structured JSON Output (machine-readable)

Using `__CDP_RESULT__` / `__CDP_END__` delimiters to parse structured results:
```
__CDP_RESULT__{"stdout": "Hello\nWorld\n", "stderr": "", "exit_code": 0, "success": true}__CDP_END__
```
Parsed successfully by the local Python script.

### Python Exception Detection

When `raise ValueError(...)` is executed, the cell execution state div gets the
CSS class `error`, detectable via:
```javascript
runBtn.shadowRoot.querySelector('.cell-execution').className.includes('error')
```

### Long-running Command Tracking

3-second timed execution with intermediate output: all steps captured, `Done in 3.0s`.

### Environment Info

- Colab runtime: Python 3.12.12, cwd: `/content`, GPU: none (free tier)
- Output duplication: `.output_text` selector returns text twice (nested elements); use `.output_text pre` for cleaner extraction.

---

## Phase 3: CDP Completion Detection & Notebook Creation (2026-03-02)

### Hash-Based Completion Marker

The original polling approach relied solely on Colab cell CSS state (`running`/`pending`/`error`), which could miss fast completions or read stale output. A hash-based marker was added:

1. `generate_remote_command_script()` now includes `GDS_DONE_<cmd_hash>` in the "Finished" output
2. `cmd_hash` = MD5(timestamp + command)[:8] — unique per invocation
3. `inject_and_execute()` accepts `done_marker` parameter and checks cell output for it
4. **Marker detection takes priority** over CSS state, providing a reliable completion signal
5. Result includes `detected_by: "marker"` or `"css_state"` to indicate detection method

### Notebook Creation via CDP + gapi.client

Successfully created Colab notebooks with content via CDP:

- **Approach**: Use `gapi.client.request()` from the Colab page context
- **Why gapi.client**: It's pre-loaded in Colab, handles CORS automatically (unlike raw `fetch()` which is blocked), and uses the user's existing Google auth
- **Auth**: No OAuth token extraction needed — `gapi.client` already has the user's auth configured
- **API**: `POST /upload/drive/v3/files?uploadType=multipart` with Colab mime type
- **Result**: Full notebook with cell content, placed in specified Drive folder

Failed approaches:
- `fetch()` to `www.googleapis.com` — 401 (SAPISIDHASH not accepted)
- `fetch()` to `clients6.google.com` — CORS blocked
- OAuth token from `gapi.auth2` — not initialized
- XHR interceptor — Colab doesn't use standard XHR/fetch for saves

### GDS --cdp Commands

New CLI commands for CDP management:

- `GDS --cdp status` — Check CDP readiness (Chrome, notebook, Colab tab)
- `GDS --cdp boot` — Launch debug Chrome, find/create notebook, open Colab tab

### Module Updates

- `logic/cdp/colab.py`: Added `create_notebook()` and `delete_drive_file()` functions
- `logic/cdp/colab.py`: Added `_build_poll_js()` with marker detection
- `executor.py`: `done_marker` threaded through subprocess chain
- `executor.py`: Feedback timeout reduced from 300s to 30s
- TuringStage status strings now translated via `_t()`
- Removed local GDS --remount hint (remote error already suggests it)
