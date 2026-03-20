# GOOGLE

Google Ecosystem Proxy Tool — provides Chrome CDP infrastructure, OAuth automation, and access to Google services.

## Architecture

GOOGLE is the **infrastructure layer** of the Google tool hierarchy:

```
GOOGLE              Chrome CDP session, input dispatch, OAuth, screenshots
├── GOOGLE.GD       Google Drive CRUD (create, delete, list via gapi.client)
├── GOOGLE.GC       Google Colab automation (cell inject, execute, tab mgmt)
└── GOOGLE.GCS      Simulated shell on Colab (highest abstraction)
```

### Chrome CDP Modules (`logic/chrome/`)

| Module | Purpose |
|--------|---------|
| `session.py` | Core CDP session, tab management, input dispatch, screenshots |
| `colab.py` | Colab tab discovery, cell injection and execution |
| `drive.py` | Google Drive operations via gapi.client in Colab |
| `oauth.py` | Google OAuth consent flow automation |
| `login.py` | Google account login/logout automation via CDP |

### Interface (`interface/main.py`)

Aggregates all CDP functions for external consumption:

```python
from tool.GOOGLE.interface.main import (
    is_chrome_available, CDPSession, CDP_PORT,
    find_colab_tab, inject_and_execute,
    list_drive_files, create_notebook,
    handle_oauth_if_needed, close_oauth_tabs,
)
```

## Commands

```bash
GOOGLE search <query>       # Google Search
GOOGLE drive list            # List Drive files
GOOGLE trends                # View trending topics
GOOGLE auth-status           # Check Google account login state
GOOGLE login --email <email> --password <pwd> [--recovery-code <code>]
GOOGLE logout                # Sign out of Google account
GOOGLE --mcp-login [email]   # MCP authentication workflow (for Cursor IDE browser)
```

## Developer Commands

```bash
GOOGLE --dev info            # Show tool paths and dependencies
GOOGLE --dev sanity-check    # Check tool structure
GOOGLE --test                # Run unit tests
GOOGLE --test --list         # List available tests
```

## Dependencies

- **PYTHON**: Managed Python runtime
- **USERINPUT**: User feedback interface
- **websocket-client**: CDP WebSocket communication
