# GCS MCP: Create Remote Notebook

## Purpose
Create `.root.ipynb` in the Env folder on Google Drive using the built-in browser MCP. This is used when the service account API cannot upload file content (403 storage quota error).

## Prerequisites
- GCS setup tutorial completed (Steps 1-5)
- Running in Cursor IDE with `cursor-ide-browser` MCP available
- User is signed into Google Drive in the integrated browser

## Usage

### Step 1: Check status
```bash
GCS --mcp-create-notebook
```
If the notebook already exists and is valid (size > 0), it reports success and no further action is needed. If creation is needed, proceed to Step 2.

### Step 2: Get workflow instructions
```bash
GCS --mcp-create-notebook --json
```
Returns a JSON object with `status: "needs_creation"` and a `steps` array of MCP tool calls.

### Step 3: Execute browser workflow

The agent should execute the following MCP tool calls in sequence:

1. **Resize browser** for Drive menu visibility:
   - Tool: `browser_resize` with `{"width": 1024, "height": 768}`

2. **Navigate** to the Env folder:
   - Tool: `browser_navigate` with `{"url": "<folder_url from JSON>"}`

3. **Lock browser**:
   - Tool: `browser_lock`

4. **Open New menu**: Click the "New" button
   - Tool: `browser_click` with ref matching `button:New`

5. **Expand More submenu**: Click "More" in the dropdown
   - Tool: `browser_click` with ref matching `menuitem:More has submenu`

6. **Click Google Colaboratory**:
   - Tool: `browser_click` with ref matching `menuitem:Google Colaboratory`

7. **Handle shared folder dialog**: A dialog "Create in a shared folder?" appears.
   - The "Create and share" button should be focused
   - Tool: `browser_press_key` with `{"key": "Enter"}`
   - If the button click is intercepted by overlay, use `offsetY` parameter

8. **Wait** for Colab tab to open (5 seconds):
   - Tool: `browser_wait_for` with `{"time": 5}`

9. **Rename notebook**: Fill the notebook name textbox
   - Tool: `browser_fill` with ref matching `textbox:Notebook name` and value `.root.ipynb`

10. **Confirm rename**:
    - Tool: `browser_press_key` with `{"key": "Enter"}`

11. **Wait** for save (3 seconds):
    - Tool: `browser_wait_for` with `{"time": 3}`

12. **Unlock browser**:
    - Tool: `browser_unlock`

### Step 4: Save the notebook ID

Extract the file ID from the Colab URL (format: `colab.research.google.com/drive/{file_id}`), then:
```bash
GCS --mcp-save-notebook <file_id>
```

### Step 5: Verify
```bash
GCS --mcp-create-notebook
```
Should report "Already configured" with the Colab URL.

## Troubleshooting

- **"Create and share" button click intercepted**: The Drive dropdown menu may overlay the dialog. Press `Escape` first to close the dropdown, then try clicking the button with an offset (`offsetY: 10` or `offsetY: 27`). Alternatively, if the button has focus, just press `Enter`.
- **Browser tab didn't change**: Check `browser_tabs` to see if a new Colab tab was opened. The new tab URL should contain `colab.research.google.com/drive/#create=1&folderId=`.
- **Empty notebook (0 bytes)**: If the notebook was created via API metadata-only (instead of browser), it will be 0 bytes and Colab shows "Unexpected end of JSON input". Delete it and recreate via browser.

## Idempotency
This workflow is idempotent:
- If `.root.ipynb` exists with size > 0, no action is taken
- If it exists with size = 0 (corrupted), it's deleted and recreated
- If it doesn't exist, the full workflow executes
