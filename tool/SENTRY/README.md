# SENTRY

Sentry error monitoring tool via Chrome DevTools Protocol.

## Overview

Access Sentry organizations, projects, and issues through the
authenticated browser session using Chrome CDP. Sentry's same-origin
REST API at `/api/0/` works with session cookies, enabling direct
API calls via CDP `fetch()`.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Sentry session at `sentry.io`

## Commands

| Command               | Description                          |
|-----------------------|--------------------------------------|
| `status`              | Check authentication state           |
| `page`                | Show current page info               |
| `orgs`                | List organizations (requires auth)   |
| `projects <org>`      | List projects (requires auth)        |
| `issues <org>`        | List issues (requires auth)          |

## Usage

```bash
SENTRY status
SENTRY orgs
SENTRY projects my-org
SENTRY issues my-org --project my-project
```

## Architecture

- `logic/chrome/api.py` — CDP-based Sentry functions (same-origin API)
- `logic/interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
