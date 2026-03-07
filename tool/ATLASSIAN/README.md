# ATLASSIAN

Atlassian account management via Chrome DevTools Protocol (CDP).

## Overview

Uses the authenticated Atlassian Home session in Chrome to access user profile, notifications, and preferences via the gateway API at `home.atlassian.com/gateway/api/`.

## Prerequisites

- Chrome running with `--remote-debugging-port=9222 --remote-allow-origins=*`
- An active Atlassian tab (`home.atlassian.com` or any `*.atlassian.com`) with authenticated session

## Commands

| Command | Description |
|---------|-------------|
| `ATLASSIAN me` | Show user profile |
| `ATLASSIAN notifications` | List recent notifications |
| `ATLASSIAN preferences` | Show user preferences |

## Interface

```python
from tool.ATLASSIAN.logic.interface.main import (
    find_atlassian_tab,
    get_me,
    get_notifications,
)
```
