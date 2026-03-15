# GOOGLE Logic

Parent tool providing Chrome CDP infrastructure, OAuth automation, and Google service access. Acts as the foundation for GOOGLE.GD, GOOGLE.GC, and GOOGLE.GCS.

## Structure

| Module | Purpose |
|--------|---------|
| `engine.py` | GoogleEngine class — data directory management and search stub |

## Sub-Packages

| Directory | Purpose |
|-----------|---------|
| `chrome/` | CDP-based browser automation: session management, Colab cell injection, Drive API via gapi.client, OAuth consent flow, login/logout |
| `mcp/` | MCP login workflow — guided Google sign-in via built-in browser with recovery codes |
| `translation/` | Localized strings (zh.json, ar.json) |

## Chrome Module Hierarchy

```
chrome/colab.py    — Colab cell injection + execution
chrome/drive.py    — Drive CRUD via CDP + gapi.client
chrome/oauth.py    — OAuth consent flow automation
chrome/login.py    — Google account login/logout via CDP
```

CDP session management is provided by `logic.chrome.session` (root-level shared module).
