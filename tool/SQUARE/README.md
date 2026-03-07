# SQUARE

Square business platform tool via Chrome DevTools Protocol.

## Overview

Access Square dashboard info, merchant data, and payment overview
through the authenticated browser session using Chrome CDP.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Square session at `squareup.com`

## Commands

| Command     | Description                          |
|-------------|--------------------------------------|
| `status`    | Check authentication state           |
| `page`      | Show current page info               |
| `dashboard` | Show dashboard summary (auth)        |

## Usage

```bash
SQUARE status
SQUARE page
SQUARE dashboard
```

## Architecture

- `logic/chrome/api.py` — CDP-based Square functions
- `interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
