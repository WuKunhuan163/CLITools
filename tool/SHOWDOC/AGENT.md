# SHOWDOC - Agent Reference

## Purpose

Access ShowDoc documentation platform via CDMCP (Chrome DevTools MCP).
Manages an authenticated browser session in the user's Chrome to interact
with showdoc.com.cn -- both via REST API (for data) and DOM (for navigation).

## Architecture

```
main.py              CLI entry point (20+ commands: session, read, write, navigation)
logic/chrome/
  api.py             Core CDMCP API -- session management, REST API calls, DOM navigation
interface/
  main.py            Cross-tool interface (re-exports all api.py functions)
```

**Data flow**: All data operations use ShowDoc's REST API via `_api_call()`,
which executes `fetch()` inside the browser page. This avoids fragile DOM
scraping and leverages the authenticated session's `user_token` from localStorage.

## REST API Reference

Base URL: `https://showdoc-server.cdn.dfyun.com.cn/server/index.php?s=`

Auth: POST FormData with `user_token` from `localStorage['userinfo']`.
Response: `{error_code: 0, data: ...}`

### Read Endpoints

| Endpoint | Params | Returns |
|---|---|---|
| `/api/user/info` | (token only) | `{uid, username, email, name, vip_type, ...}` |
| `/api/item/myList` | (token only) | `[{item_id, item_name, item_type, item_description, is_private, is_star, ...}]` |
| `/api/item/info` | `item_id` | `{item_id, item_name, item_type, menu: {pages, catalogs}, ...}` |
| `/api/item/search` | `item_id, keyword` | `{item_name, pages: [{page_id, page_title, search_content, ...}]}` |
| `/api/catalog/catList` | `item_id` | `[{cat_id, cat_name, parent_cat_id, level, ...}]` |
| `/api/page/info` | `page_id` | `{page_id, page_title, page_content, item_id, cat_id, ...}` |
| `/api/page/history` | `page_id` | `[{history entries}]` |
| `/api/itemGroup/getList` | (token only) | `[{group_id, group_name, ...}]` |
| `/api/message/getUnread` | (token only) | Unread message count |

### Write Endpoints

| Endpoint | Params | Effect |
|---|---|---|
| `/api/item/add` | `item_name, item_type, item_description, password` | Create project |
| `/api/item/update` | `item_id, item_name?, item_description?` | Update project |
| `/api/item/delete` | `item_id, password` | Delete project |
| `/api/item/star` | `item_id` | Star project |
| `/api/item/unstar` | `item_id` | Unstar project |
| `/api/page/save` | `item_id, page_title, page_content, cat_id, [page_id]` | Create or update page |
| `/api/page/delete` | `page_id, item_id` | Delete page |
| `/api/catalog/save` | `item_id, cat_name, parent_cat_id, [cat_id]` | Create/rename catalog |
| `/api/catalog/delete` | `cat_id, item_id` | Delete catalog |

### Additional Endpoints (discovered, not yet wrapped)

| Endpoint | Params | Purpose |
|---|---|---|
| `/api/export/markdown` | `item_id` | Export to markdown |
| `/api/export/word` | `item_id` | Export to Word |
| `/api/exportHtml/export` | `item_id` | Export to HTML |
| `/api/import/auto` | varies | Auto-import |
| `/api/template/getMyList` | (token) | List templates |
| `/api/template/save` | varies | Save template |
| `/api/ai/create` | varies | AI generation |
| `/api/ai/rebuildIndex` | `item_id` | Rebuild AI index |
| `/api/mock/add` | varies | Add API mock |
| `/api/page/sqlToMarkdownTable` | `sql` | Convert SQL to markdown table |
| `/api/team/getList` | (token) | List teams |
| `/api/member/getList` | `item_id` | List project members |

### Item Types

| `item_type` | Name |
|---|---|
| `1` | Regular (API docs, markdown docs) |
| `4` | Table (data dictionary/spreadsheet) |
| `5` | Whiteboard |

### Document Tree Structure (from `/api/item/info`)

```json
{
  "menu": {
    "pages": [
      {"page_id": "...", "page_title": "...", "cat_id": "0"}
    ],
    "catalogs": [
      {
        "cat_id": "...", "cat_name": "...",
        "pages": [...],
        "catalogs": [...]
      }
    ]
  }
}
```

## DOM Structure (showdoc.com.cn)

### Dashboard (`/item/index`)

- `.item-home` -- main container
- `.header` -- top bar with logo and controls
  - `.header-right .icon-item .fa-user` -- user icon (present when authenticated)
  - `.header-right .icon-item .fa-message` -- messages
- `.left-side` -- "All items" / "Starred" / Groups
- `.right-side` -- project grid
  - `.item-card` -- each project card
  - `.item-card-title` -- project name
  - `.item-type-badge` -- type label
  - `.ant-col[data-key]` -- item_id
  - `.create-item-btn-div` -- "Create Item" button

### Project page (`/{item_id}`)

- `.show-regular-item` -- main container
- `.item-header` -- project name header
- `.doc-container` -- two-column layout
  - `.catalog-tree` -- left sidebar with Ant Design Tree
    - `.ant-tree-treenode` -- each tree node
    - `.node-title.node-page` -- page node
    - `.node-title.node-folder` -- folder node
    - `.node-selected` -- currently selected node
  - `.page-content-main` -- right content panel
    - `.markdown-body.editormd-html-preview` -- rendered markdown

### Auth State

- **Authenticated**: `localStorage['userinfo']` contains `user_token`, URL not `/user/login`
- **Not authenticated**: URL is `/user/login` or `/user/register`

## CLI Commands

### Session Management

```bash
SHOWDOC boot                     # Boot CDMCP session, open ShowDoc tab
SHOWDOC status                   # Check CDP, session, and auth state
```

### Read Operations

```bash
SHOWDOC user                     # Show user profile
SHOWDOC projects                 # List all projects with IDs
SHOWDOC project <item_id>        # Full project info + document tree
SHOWDOC catalog <item_id>        # Catalog folders only
SHOWDOC page <page_id>           # Show page content (markdown)
SHOWDOC search <item_id> <kw>    # Full-text search within project
```

### Write Operations

```bash
SHOWDOC save-page <item_id> <title> --content "# Hello"    # Create new page
SHOWDOC save-page <item_id> <title> --file doc.md           # Create from file
SHOWDOC save-page <item_id> <title> --page-id <id> --content "..."  # Update
SHOWDOC delete-page <page_id> <item_id>                     # Delete page
SHOWDOC create-project <name> [--type 1|4|5] [--password]   # New project
SHOWDOC create-catalog <item_id> <name> [--parent <cat_id>] # New folder
SHOWDOC delete-catalog <cat_id> <item_id>                   # Delete folder
SHOWDOC star <item_id>                                       # Star project
SHOWDOC unstar <item_id>                                     # Unstar
```

### Navigation

```bash
SHOWDOC goto <item_id> [page_id] # Navigate browser to project/page
SHOWDOC home                     # Navigate to dashboard
SHOWDOC screenshot [--output]    # Capture current page
```

## Python Interface (cross-tool)

```python
from tool.SHOWDOC.interface.main import get_projects, get_page_content, save_page

projects = get_projects()
page = get_page_content("11559060626653822")
save_page("2598850122360470", "New Page", "# Content here")
```

## Common Workflows

### Read a document

```bash
SHOWDOC projects                            # find item_id
SHOWDOC project 2598850122360470            # see document tree, find page_id
SHOWDOC page 11559060626653822              # read page content
```

### Create documentation

```bash
SHOWDOC create-project "My API Docs" --password secret123
SHOWDOC create-catalog <item_id> "Authentication"
SHOWDOC save-page <item_id> "Login API" --cat-id <cat_id> --file login.md
```

### Search and navigate

```bash
SHOWDOC search 2598850122360470 "login"     # find pages mentioning "login"
SHOWDOC goto 2598850122360470 11559060626653825  # open in Chrome
SHOWDOC screenshot --output /tmp/doc.png    # capture it
```

## ToS Compliance

**Status: COMPLIANT** -- This tool uses ShowDoc's REST API via in-page `fetch()` from the authenticated session (`_api_call()` helper). CDMCP is only used for session management. ShowDoc is open source (Apache 2.0) with a well-documented API. All data operations go through `showdoc-server.cdn.dfyun.com.cn/server/index.php?s=/api/`.
