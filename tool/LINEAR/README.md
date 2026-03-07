# LINEAR

Linear product development tool via Chrome DevTools Protocol.

## Overview

Access Linear user info, authentication state, and organization data
through the authenticated browser session using Chrome CDP. Data is read
from `localStorage` (`ApplicationStore`) since Linear's GraphQL API
requires token auth not carried via cross-origin cookies.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Linear session at `linear.app`

## Commands

| Command  | Description                                  |
|----------|----------------------------------------------|
| `status` | Check authentication and organization state  |
| `me`     | Show user info (account ID, email, orgs)     |
| `page`   | Show current page state                      |

## Usage

```bash
LINEAR status
LINEAR me
LINEAR page
```

## Architecture

- `logic/chrome/api.py` — CDP-based Linear functions (localStorage)
- `interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
