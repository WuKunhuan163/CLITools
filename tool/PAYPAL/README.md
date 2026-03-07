# PAYPAL

PayPal payment integration tool via Chrome DevTools Protocol.

## Overview

Access PayPal account info, balance, and recent activity through the
authenticated browser session using Chrome CDP.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222`
- An authenticated PayPal session at `paypal.com`

## Commands

| Command    | Description                          |
|------------|--------------------------------------|
| `status`   | Check authentication state           |
| `page`     | Show current page info               |
| `account`  | Show account info (requires auth)    |
| `activity` | Show recent transactions (auth)      |

## Usage

```bash
PAYPAL status
PAYPAL page
PAYPAL account
PAYPAL activity
```

## Architecture

- `logic/chrome/api.py` — CDP-based PayPal functions
- `logic/interface/main.py` — Cross-tool interface exports
- `logic/translation/zh.json` — Chinese translations
