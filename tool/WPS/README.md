# WPS

WPS Office / KDocs tool via Chrome DevTools Protocol.

## Overview

Access WPS user info and recent documents through the authenticated
KDocs/WPS web session using Chrome CDP. Supports WeChat/QQ/email
login on `kdocs.cn`.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- Authenticated WPS/KDocs session at `kdocs.cn` or `wps.com`

## Commands

| Command  | Description                          |
|----------|--------------------------------------|
| `status` | Check authentication state           |
| `page`   | Show current page info               |
| `me`     | Show user info (requires auth)       |
| `docs`   | List recent documents (requires auth)|

## Usage

```bash
WPS status
WPS me
WPS docs
```

## Architecture

- `logic/chrome/api.py` — CDP-based WPS/KDocs functions
- `logic/interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
