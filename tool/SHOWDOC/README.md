# SHOWDOC

ShowDoc documentation platform via CDMCP (Chrome DevTools MCP).

## Overview

Access [ShowDoc](https://www.showdoc.com.cn) API documentation, data
dictionaries, and team docs through an authenticated Chrome browser session.
Uses ShowDoc's REST API for data operations and CDP for browser control.

Supports full CRUD operations: create/read/update/delete for projects,
catalogs (folders), and pages. Also includes full-text search,
star/unstar, and browser navigation with screenshots.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- `GOOGLE.CDMCP` tool installed (provides session management and overlays)
- An active ShowDoc account at showdoc.com.cn

## Quick Start

```bash
SHOWDOC boot          # Opens ShowDoc tab in Chrome
# Log in to showdoc.com.cn in Chrome if prompted
SHOWDOC status        # Verify authentication
SHOWDOC projects      # List your documentation projects
```

## Commands

### Session

| Command | Description |
|---|---|
| `boot` | Boot CDMCP session, open ShowDoc tab in Chrome |
| `status` | Check Chrome CDP, session, and authentication state |

### Read

| Command | Description |
|---|---|
| `user` | Show authenticated user profile |
| `projects` | List all documentation projects |
| `project <item_id>` | Show project metadata and full document tree |
| `catalog <item_id>` | Show catalog (folder) structure |
| `page <page_id>` | Show page content (markdown source) |
| `search <item_id> <keyword>` | Full-text search within a project |

### Write

| Command | Description |
|---|---|
| `save-page <item_id> <title>` | Create/update page (--content or --file) |
| `delete-page <page_id> <item_id>` | Delete a page |
| `create-project <name>` | Create new project (--type, --password) |
| `create-catalog <item_id> <name>` | Create catalog folder (--parent) |
| `delete-catalog <cat_id> <item_id>` | Delete a catalog folder |
| `star <item_id>` | Star a project |
| `unstar <item_id>` | Unstar a project |

### Navigation

| Command | Description |
|---|---|
| `goto <item_id> [page_id]` | Navigate browser to project or specific page |
| `home` | Navigate to the ShowDoc dashboard |
| `screenshot [--output]` | Take a screenshot of the current page |

## Architecture

- **Data layer**: All data operations go through ShowDoc's REST API via
  in-page `fetch()` calls. The user's `user_token` from `localStorage`
  provides authentication.
- **Session layer**: CDMCP session management ensures a persistent Chrome
  tab with visual overlays (favicon + badge).
- **Navigation layer**: CDP evaluates `window.location.href` for browser
  navigation; DOM selectors are only used for auth state detection.
- **Interface layer**: `interface/main.py` exports all API functions for
  cross-tool integration.

## Dependencies

- `PYTHON` -- Python runtime
- `GOOGLE.CDMCP` -- Chrome DevTools MCP session infrastructure
