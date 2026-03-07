# KLING

Kling AI video generation tool via Chrome DevTools Protocol.

## Overview

Access Kling AI user info, credit points, and generation history through
the authenticated browser session using Chrome CDP. Data is read from
`localStorage` and DOM elements since the Kling API gateway blocks
cross-origin fetch.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated Kling AI session at `app.klingai.com`

## Commands

| Command   | Description                         |
|-----------|-------------------------------------|
| `me`      | Show user info (ID, name, email)    |
| `points`  | Show credit points balance          |
| `page`    | Show current page state             |
| `history` | Show recent generation history      |

## Usage

```bash
KLING me
KLING points
KLING page
KLING history
```

## Architecture

- `logic/chrome/api.py` — CDP-based Kling AI functions (localStorage + DOM)
- `interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
