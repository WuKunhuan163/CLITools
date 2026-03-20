# BILIBILI — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
All content operations must use the Bilibili Open Platform API.

## Active Commands (CDMCP auth only)

| Command | Description | Status |
|---------|-------------|--------|
| `BILIBILI boot` | Boot session | Active |
| `BILIBILI status` | Session status | Active |
| `BILIBILI state` | Full MCP state | Active |
| `BILIBILI screenshot` | Take screenshot | Active |

## Disabled Commands (ToS violation)

All navigation, search, playback, engagement, danmaku, live, and content
creation commands are disabled. They return ToS errors.

## ToS Compliance

**Status: HIGH RISK** (DOM automation disabled)

Bilibili's Terms of Service explicitly prohibit:
- Automated queries and bot access
- Use of robots, spiders, scrapers
- Methods other than official interfaces

Enforcement includes 412 error codes, rate limiting (429), CAPTCHA challenges,
and account warnings/suspension.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS prohibits automation | **Yes** (explicit) |
| Official API exists | **Yes** (open.bilibili.com) |
| Decision | **Use Open Platform API; CDMCP for auth/session only** |

## Migration: Bilibili Open Platform API

### Overview

Bilibili offers comprehensive developer APIs at https://open.bilibili.com/:

- **User Management**: Authorization, profile info
- **Video Content**: Upload, edit, delete, metadata queries
- **Article Management**: Article creation and management
- **Livestream**: Streaming integration, WebSocket, room management
- **Data Services**: Analytics, performance metrics
- **Account Management**: OAuth tokens and authentication

### Setup

1. Register at https://open.bilibili.com/
2. Complete identity verification (身份认证)
3. Create an application
4. Accept authorization invitations
5. Use OAuth2 for user-scoped operations

### API Documentation

- https://open.bilibili.com/agreement/developer-service
- https://bilibili.apifox.cn/ (API reference)
- https://github.com/bilibili-openplatform/demo (SDK demos)

## Preserved Exploration Data

`data/exploration/bilibili_elements.json` documents the explored DOM structure.
Preserved as reference, not for automation.
