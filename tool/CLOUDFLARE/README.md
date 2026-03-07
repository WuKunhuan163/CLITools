# CLOUDFLARE

Cloudflare account management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Cloudflare dashboard session in Chrome to perform API operations without requiring a separate API token. All calls go through the same-origin proxy at `dash.cloudflare.com/api/v4/`.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Cloudflare dashboard tab (`dash.cloudflare.com`) with authenticated session

## Commands

| Command | Description |
|---------|-------------|
| `CLOUDFLARE user` | Show authenticated user info |
| `CLOUDFLARE account` | Show account info |
| `CLOUDFLARE zones` | List DNS zones |
| `CLOUDFLARE dns <zone_id>` | List DNS records for a zone |
| `CLOUDFLARE workers` | List Workers scripts |
| `CLOUDFLARE pages` | List Pages projects |
| `CLOUDFLARE kv` | List KV namespaces |

## Interface

Other tools can import Cloudflare functions:

```python
from tool.CLOUDFLARE.logic.interface.main import (
    find_cloudflare_tab,
    get_user,
    list_zones,
    list_dns_records,
)
```
